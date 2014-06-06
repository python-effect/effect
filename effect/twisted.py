"""
Twisted integration for the Effect library.

This is largely concerned with bridging the gap between Effects and Deferreds.

There are three useful functions:

- deferred_performer, which is a decorator for writing effect handlers that
  return Deferreds.
- perform, which is like effect.perform except that it returns a Deferred
  with the final result, and also sets up some Deferred-specific handlers.
- perform_parallel, which is the Deferred-specific handler for the
  ParallelEffects intent.
"""

from __future__ import absolute_import

from functools import wraps

from twisted.internet.defer import Deferred, maybeDeferred, gatherResults
from twisted.python.failure import Failure

from . import dispatch_method, perform as base_perform
from effect import ParallelEffects


def deferred_performer(func):
    """
    An instance method decorator which allows you to define your
    effect-performing functions to return Deferreds. If you use this, you
    don't have to care about putting your results into the result box --
    Effect callbacks will automatically be invoked when the Deferred's result
    is available.

    Usage:

        class MyIntent(object):
            @deferred_performer
            def perform_effect(self, dispatcher):
                return get_a_deferred()
    """
    @wraps(func)
    def perform_effect(self, dispatcher, box):
        d = maybeDeferred(func, self, dispatcher)
        deferred_to_box(d, box)
    return perform_effect


def deferred_to_box(d, box):
    """
    Make a Deferred pass its success or fail events on to the given box.
    """
    d.addCallbacks(box.succeed, lambda f: box.fail((f.value, f.type, f.tb)))


def twisted_dispatcher(intent, box):
    """
    Do the same as :func:`effect.default_dispatcher`, but handle 'parallel'
    intents by passing them to :func:`perform_parallel`.
    """
    if type(intent) is ParallelEffects:
        perform_parallel(intent, twisted_dispatcher, box)
    else:
        dispatch_method(intent, twisted_dispatcher, box)


def perform_parallel(parallel, dispatcher, box):
    """
    Perform a ParallelEffects intent by using the Deferred gatherResults
    function.
    """
    d = gatherResults(
        [maybeDeferred(perform, e, dispatcher) for e in parallel.effects])
    deferred_to_box(d, box)


def perform(effect, dispatcher=twisted_dispatcher):
    """
    Perform an effect, and return a Deferred that will fire with that effect's
    ultimate result.
    """
    d = Deferred()
    eff = effect.on(
        success=d.callback,
        error=lambda e: Failure(e[1], e[0], e[2]))
    base_perform(eff, dispatcher=dispatcher)
    return d
