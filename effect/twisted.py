"""
Twisted integration for the Effect library.

This is largely concerned with bridging the gap between Effects and Deferreds.

Note that the core effect library does *not* depend on Twisted, but this module
does.

The main useful thing you should be concerned with is the :func:`perform`
function, which is like effect.perform except that it returns a Deferred with
the final result, and also sets up Twisted/Deferred specific effect handling
by using its default effect dispatcher, twisted_dispatcher.
"""

from __future__ import absolute_import

from functools import partial

import sys

from twisted.internet.defer import Deferred, maybeDeferred, gatherResults
from twisted.python.failure import Failure
from twisted.internet.task import deferLater

from . import dispatch_method, perform as base_perform, Delay
from effect import ParallelEffects


def deferred_to_box(d, box):
    """
    Make a Deferred pass its success or fail events on to the given box.
    """
    d.addCallbacks(box.succeed, lambda f: box.fail((f.type, f.value, f.tb)))


def twisted_dispatcher(reactor, intent, box):
    """
    Very similar to :func:`effect.default_dispatcher`, with two differences:

    - Deferred results from effect handlers are used to provide the effect
      results
    - parallel intents are handled with :func:`perform_parallel`.
    """
    # TODO: Allow Twisted-specific effect performers to have the reactor passed
    #       to them. ALTERNATIVELY, rely on application writers to curry in
    #       the reactor they desire to their effect performers...
    dispatcher = partial(twisted_dispatcher, reactor)
    if type(intent) is ParallelEffects:
        func = partial(perform_parallel, intent, reactor)
    elif type(intent) is Delay:
        func = partial(perform_delay, intent, reactor)
    else:
        func = partial(dispatch_method, intent, dispatcher)

    try:
        result = func()
    except:
        box.fail(sys.exc_info())
    else:
        if isinstance(result, Deferred):
            deferred_to_box(result, box)
        else:
            box.succeed(result)


def perform_parallel(parallel, reactor):
    """
    Perform a ParallelEffects intent by using the Deferred gatherResults
    function.
    """
    return gatherResults(
        [maybeDeferred(perform, reactor, e, dispatcher=twisted_dispatcher)
         for e in parallel.effects])


def perform_delay(delay, reactor):
    return deferLater(reactor, delay.delay, lambda: None)


def perform(reactor, effect, dispatcher=twisted_dispatcher):
    """
    Perform an effect, handling Deferred results and returning a Deferred
    that will fire with the effect's ultimate result.

    Defaults to using the twisted_dispatcher as the dispatcher.
    """
    d = Deferred()
    eff = effect.on(
        success=d.callback,
        error=lambda e: d.errback(Failure(e[1], e[0], e[2])))
    base_perform(eff, dispatcher=partial(dispatcher, reactor))
    return d
