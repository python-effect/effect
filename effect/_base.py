# -*- test-case-name: effect.test_base -*-
from __future__ import print_function, absolute_import

import sys

from functools import partial

from characteristic import attributes

from .continuation import trampoline


@attributes([
    'intent', 'callbacks',
], apply_with_init=False, apply_immutable=True)
class Effect(object):
    """
    Wrap an object that describes how to perform some effect (called an
    "intent"), and allow attaching callbacks to be run when the effect
    is complete.

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
        Return a new Effect that will invoke either the success or error
        callbacks provided based on whether this Effect completes sucessfully
        or in error.
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
    it raised an exception. In that case result will be sys.exc_info().
    """
    try:
        return (False, f(*args, **kwargs))
    except:
        return (True, sys.exc_info())


class NoPerformerFoundError(Exception):
    """Raised when a performer for an intent couldn't be found."""


def perform(dispatcher, effect):
    """
    Perform an effect and invoke callbacks associated with it.

    The dispatcher will be passed the intent, and is expected to return a
    ``performer``, which is a function taking a dispatcher, the intent, and a
    box, and returning nothing. See :module:`effect.dispatcher` for some
    implementations of dispatchers, and :obj:`effect.base_dispatcher` for a
    dispatcher supporting core intents like :obj:`ConstantIntent` and so forth.

    The performer will then be invoked with two arguments: the dispatcher and
    the box.

    The dispatcher is passed so the performer can make recursive calls to
    perform, if it needs to perform other effects (see :func:`parallel` and
    :func:`perform_parallel` for an example of this).

    The box is an object that lets the performer provide the result (optionally
    asynchronously). See :func:`_Box.succeed` and :func:`_Box.fail`. Often
    you can ignore the box by using a decorator like :func:`sync_performer` or
    :func:`effect.twisted.deferred_performer`.

    If a callback of an Effect ``a`` returns an Effect ``b``, ``b`` will be
    performed immediately, and its result will be passed on to the next
    callback.

    Note that this function does _not_ return the final result of the effect.
    You may instead want to use :func:`sync_perform` or
    :func:`effect.twisted.perform`.

    :returns: None
    """
    def _run_callbacks(bouncer, chain, result):
        is_error, value = result

        if type(value) is Effect:
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
            raise NoPerformerFoundError(effect.intent)

        performer(
            dispatcher,
            effect.intent,
            _Box(partial(bouncer.bounce,
                         _run_callbacks, effect.callbacks)))

    trampoline(_perform, effect)
