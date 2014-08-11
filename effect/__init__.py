"""
A system for helping you separate your IO and state-manipulation code
(hereafter referred to as "effects") from everything else, thus allowing
the majority of your code to be trivially testable and composable (that is,
have the general benefits of purely functional code).

TODO: an effect implementation of ParallelEffects that uses threads?
TODO: an effect implementation of ParallelEffects that is actually serial,
      as a fallback?
TODO: integration with other asynchronous libraries like asyncio, trollius,
      eventlet
"""

from __future__ import print_function

import sys

import six

from .continuation import trampoline


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
            performed. Optionally has a perform_effect(dispatcher) method.
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

    def __repr__(self):
        return "Effect(%r, callbacks=%s)" % (self.intent, self.callbacks)


def dispatch_method(intent, dispatcher):
    """
    Call intent.perform_effect with the given dispatcher and box.

    Raise NoEffectHandlerError if there's no perform_effect method.
    """
    if hasattr(intent, 'perform_effect'):
        return intent.perform_effect(dispatcher)
    raise NoEffectHandlerError(intent)


def default_dispatcher(intent, box):
    """
    This is the default dispatcher used by :func:`perform`.

    If the intent has a 'perform_effect' method, invoke it with this
    function as an argument. Its result will be passed to the first callback
    on the effect.

    If the perform_effect method can't be found, raise NoEffectHandlerError.

    If you're using Twisted Deferreds, you should look at
    :func:`effect.twisted.twisted_dispatcher`.
    """
    try:
        box.succeed(dispatch_method(intent, default_dispatcher))
    except:
        box.fail(sys.exc_info())


class _Box(object):
    """
    An object into which an effect dispatcher can place a result.
    """
    def __init__(self, bouncer, more):
        self._bouncer = bouncer
        self._more = more

    def succeed(self, result):
        """
        Indicate that the effect has succeeded, and the result is available.
        """
        self._bouncer.bounce(self._more, (False, result))

    def fail(self, result):
        """
        Indicate that the effect has failed to be met. result must be an
        exc_info tuple.
        """
        self._bouncer.bounce(self._more, (True, result))


def perform(effect, dispatcher=default_dispatcher):
    """
    Perform an effect by invoking the dispatcher, and invoke callbacks
    associated with it.

    The dispatcher will be passed a "box" argument and the intent. The box
    is an object that lets the dispatcher specify the result (optionally
    asynchronously). See :func:`_Box.succeed` and :func:`_Box.fail`.

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
        dispatcher(
            effect.intent,
            _Box(bouncer,
                 lambda bouncer, result:
                     _run_callbacks(bouncer, effect.callbacks, result)))

    trampoline(_perform, effect)


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


class NoEffectHandlerError(Exception):
    """
    No perform_effect method was found on the given intent.
    """


class ParallelEffects(object):
    """
    An effect intent that asks for a number of effects to be run in parallel,
    and for their results to be gathered up into a sequence.

    The default implementation of this effect relies on Twisted's Deferreds.
    An alternative implementation can run the child effects in threads, for
    example. Of course, the implementation strategy for this effect will need
    to cooperate with the effects being parallelized -- there's not much use
    running a Deferred-returning effect in a thread.
    """
    def __init__(self, effects):
        self.effects = effects

    def __repr__(self):
        return "ParallelEffects(%r)" % (self.effects,)


def parallel(effects):
    """
    Given multiple Effects, return one Effect that represents the aggregate of
    all of their effects.
    The result of the aggregate Effect will be a list of their results, in
    the same order as the input to this function.
    """
    return Effect(ParallelEffects(list(effects)))


class NotSynchronousError(Exception):
    """Performing an effect did not immediately return a value."""


def sync_perform(effect, dispatcher=default_dispatcher):
    """
    Perform an effect, and return its ultimate result. If the final result is
    an error, the exception will be raised. This is useful for testing, and
    also if you're using blocking effect implementations.

    This requires that the effect (and all effects returned from any of its
    callbacks) to be synchronous. If this is not the case, NotSynchronousError
    will be raised.
    """
    successes = []
    errors = []

    def success(x):
        successes.append(x)

    def error(x):
        errors.append(x)

    effect = effect.on(success=success, error=error)
    perform(effect, dispatcher=dispatcher)
    if successes:
        return successes[0]
    elif errors:
        six.reraise(*errors[0])
    else:
        raise NotSynchronousError("Performing %r was not synchronous!"
                                  % (effect,))


class ConstantIntent(object):
    """An intent that returns a pre-specified result when performed."""
    def __init__(self, result):
        self.result = result

    def __repr__(self):
        return "ConstantIntent(%r)" % (self.result,)

    def perform_effect(self, dispatcher):
        return self.result


class ErrorIntent(object):
    """An intent that raises a pre-specified exception when performed."""
    def __init__(self, exception):
        self.exception = exception

    def perform_effect(self, dispatcher):
        raise self.exception


class FuncIntent(object):
    """An intent that returns the result of the specified function."""
    def __init__(self, func):
        self.func = func

    def perform_effect(self, dispatcher):
        return self.func()
