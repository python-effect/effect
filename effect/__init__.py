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

from functools import wraps

from .continuation import trampoline

__all__ = ['Effect', 'perform', 'parallel', 'ParallelEffects']

# XXX What happens when an inner effect has no effect implementation (and thus
# raises NoEffectHandlerError). Are its error handlers invoked?


class Effect(object):
    """
    Wrap an object that describes how to perform some effect (called an
    "effect intent"), and allow attaching callbacks to be run when the effect
    is complete.

    (You're an object-oriented programmer.
     You probably want to subclass this.
     Don't.)
    """
    def __init__(self, intent, callbacks=None):
        """
        :param intent: An object that describes an effect to be
            performed. Optionally has a perform_effect(dispatcher, box) method.
        """
        self.intent = intent
        if callbacks is None:
            callbacks = []
        self.callbacks = callbacks

    def on_success(self, callback):
        """
        Return a new Effect that will invoke the associated callback when this
        Effect completes succesfully.
        """
        return self.on(success=callback, error=None)

    def on_error(self, callback):
        """
        Return a new Effect that will invoke the associated callback when this
        Effect fails.

        The callback will be invoked with the sys.exc_info() exception tuple
        as its only argument. Note that sometimes the third element in the
        tuple, usually the traceback, may sometimes be None.
        """
        return self.on(success=None, error=callback)

    def after(self, callback):
        """
        Return a new Effect that will invoke the associated callback when this
        Effect completes, whether successfully or in error.
        """
        return self.on(success=callback, error=callback)

    def on(self, success, error):
        """
        Return a new Effect that will invoke either the success or error
        callbacks provided based on whether this Effect completes sucessfully
        or in error.
        """
        return Effect(self.intent,
                      callbacks=self.callbacks + [(success, error)])

    def __repr__(self):
        return "Effect(%r, callbacks=%s)" % (self.intent, self.callbacks)


def dispatch_method(intent, dispatcher, box):
    if hasattr(intent, 'perform_effect'):
        return intent.perform_effect(default_dispatcher, box)
    raise NoEffectHandlerError(intent)


def default_dispatcher(intent, box):
    """
    This is the default dispatcher used by :func:`perform`.

    If the intent has a 'perform_effect' method, invoke it with this
    function as an argument, as well as an instance of :class:`_Box`.

    The perform_effect method MUST call :func:`_Box.succeed` or
    :func:`_Box.fail` with the successful result or exc_info tuple in the case
    of a failure. To reduce this burden, please make use of decorators such as
    :func:`synchronous_performer` or :func:`effect.twisted.deferred_performer`.

    If the perform_effect method can't be found, raise NoEffectHandlerError.

    If you're using Twisted Deferreds, you should look at
    :func:`effect.twisted.twisted_dispatcher`.
    """
    return dispatch_method(intent, default_dispatcher, box)


def synchronous_performer(func):
    """
    A decorator that wraps a perform_effect function so it doesn't need to
    care about the result box -- it just needs to return a value (or raise an
    exception).
    """
    @wraps(func)
    def perform_effect(self, dispatcher, box):
        try:
            box.succeed(func(self, dispatcher))
        except:
            box.fail(sys.exc_info())
    return perform_effect


class _Box(object):
    """
    An object into which an intent performer can place a result.
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
    Perform the intent of an effect by passing it to the dispatcher, and
    invoke callbacks associated with it.

    Note that this function does _not_ return the final result of the effect.
    You may instead want to use effect.twisted.perform.

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


def _iter_conses(seq):
    """
    Generate (head, tail) tuples so you can iterate in a way that feels like
    a typical recursive function over a linked list.
    """
    for i in range(len(seq)):
        yield seq[i], seq[i + 1:]


class NoEffectHandlerError(Exception):
    """
    No Effect handler could be found for the given Effect-wrapped object.
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
    """Raised when performing an effect wasn't synchronous."""


def sync_perform(effect, dispatcher=default_dispatcher):
    """
    Perform an effect, and return the value that its last callback or error
    handler returns. If the final callback raises an exception, the exception
    will be raised. This is useful for testing, and also if you're using
    blocking functions (e.g. with @synchronous_performer) in all your effect
    implementations.

    This requires that the effect (and all effects returned from any of its
    callbacks) to be synchronous -- in other words, the effect performers
    must pass the result to the box before returning.

    If this is not the case, NotSynchronousError will be raised.
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
