# -*- test-case-name: effect.test_base -*-
from __future__ import print_function, absolute_import

import sys

from functools import partial

from characteristic import attributes

from ._continuation import trampoline


@attributes([
    'intent', 'callbacks',
], apply_with_init=False, apply_immutable=True)
class Effect(object):
    """
    Take an object that describes a desired effect (called an "Intent"), and
    allow binding callbacks to be called with the result of the effect.

    Effects can be performed with :func:`perform`.

    (You're an object-oriented programmer.
     You probably want to subclass this.
     Don't.)
    """
    def __init__(self, intent, callbacks=None):
        """
        :param intent: An object that describes an effect to be
            performed.
        """
        self.intent = intent
        if callbacks is None:
            callbacks = []
        self.callbacks = callbacks

    def on(self, success=None, error=None):
        """
        Return a new Effect with the given success and/or error callbacks
        bound.

        The result of the Effect will be passed to the first callback. Any
        callbacks added afterwards will receive the result of the previous
        callback. Normal return values are passed on to the next ``success``
        callback, and exceptions are passed to the next ``error`` callback
        as a ``sys.exc_info()`` tuple.

        If a callback returns an :obj:`Effect`, the result of that
        :obj:`Effect` will be passed to the next callback.
        """
        return Effect(self.intent,
                      callbacks=self.callbacks + [(success, error)])


class _Box(object):
    """
    An object into which an effect dispatcher can place a result.
    """
    def __init__(self, cont):
        self._cont = cont

    def succeed(self, result):
        """
        Indicate that the effect has succeeded, and the result is available.
        """
        self._cont((False, result))

    def fail(self, result):
        """
        Indicate that the effect has failed. result must be an exc_info tuple.
        """
        self._cont((True, result))


def guard(f, *args, **kwargs):
    """
    Run a function.

    Return (is_error, result), where is_error is a boolean indicating whether
    it raised an exception. In that case result will be ``sys.exc_info()``.
    """
    try:
        return (False, f(*args, **kwargs))
    except:
        return (True, sys.exc_info())


class NoPerformerFoundError(Exception):
    """Raised when a performer for an intent couldn't be found."""


def perform(dispatcher, effect, recurse_effects=True):
    """
    Perform an effect and invoke callbacks bound to it.

    The dispatcher will be passed the intent, and is expected to return a
    performer (a callable). See :obj:`TypeDispatcher` and
    :obj:`ComposedDispatcher` for some implementations of dispatchers, and
    :obj:`effect.base_dispatcher` for a dispatcher supporting basic intents
    like :obj:`ConstantIntent` et al.

    The performer will then be invoked with the dispatcher, the intent, and
    the box, and should perform the desired effect.

    The dispatcher is passed so the performer can make recursive calls to
    perform, if it needs to perform other effects (see :func:`parallel` and
    :func:`perform_parallel` for an example of this).

    The box is an object that lets the performer provide the result (optionally
    asynchronously). See :func:`_Box.succeed` and :func:`_Box.fail`. Usually
    you can ignore the box by using a decorator like :func:`sync_performer` or
    :func:`effect.twisted.deferred_performer`.

    Callbacks can return Effects, and those effects will immediately performed.
    The result of the returned Effect will be passed to the next callback.

    Note that this function does _not_ return the final result of the effect.
    You may instead want to use :func:`effect.sync_perform` or
    :func:`effect.twisted.perform`.

    :returns: None
    """
    def _run_callbacks(bouncer, chain, result):
        is_error, value = result

        if recurse_effects and type(value) is Effect:
            bouncer.bounce(
                _perform,
                Effect(value.intent, callbacks=value.callbacks + chain))
            return

        if not chain:
            return

        cb = chain[0][is_error]
        if cb is not None:
            result = guard(cb, value)
        chain = chain[1:]
        bouncer.bounce(_run_callbacks, chain, result)

    def _perform(bouncer, effect):
        performer = dispatcher(effect.intent)
        if performer is None:
            try:
                raise NoPerformerFoundError(effect.intent)
            except:
                e = sys.exc_info()
            _run_callbacks(bouncer, effect.callbacks, (True, e))

        else:
            performer(
                dispatcher,
                effect.intent,
                _Box(partial(bouncer.bounce,
                             _run_callbacks, effect.callbacks)))

    trampoline(_perform, effect)
