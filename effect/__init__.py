"""
A system for helping you separate your IO and state-manipulation code
(hereafter referred to as "effects") from everything else, thus allowing
the majority of your code to be trivially testable and composable (that is,
have the general benefits of purely functional code).

Keywords: monad, IO, stateless.

The core behavior is as follows:
- Effectful operations should be represented as plain Python objects which
  we will call the *intent* of an effect. These objects should be wrapped
  in an instance of :class:`Effect`.
- Intent objects can implement a 'perform_effect' method to actually perform
  the effect. This method should _not_ be called directly.
- In most cases where you'd perform effects in your code, you should instead
  return an Effect wrapping the effect intent.
- To represent work to be done *after* an effect, use Effect.on_success,
  .on_error, etc.
- Near the top level of your code, invoke Effect.perform on the Effect you
  have produced. This will invoke the effect-performing handler specific to
  the wrapped object, and invoke callbacks as necessary.
- If the callbacks return another instance of Effect, that Effect will be
  performed before continuing back down the callback chain.

On top of the implemented behaviors, there are some conventions that these
behaviors synergize with:

- Don't perform actual IO or manipulate state in functions that return an
  Effect. This kinda goes without saying. However, there are a few cases
  where you may decide to compromise:
  - most commonly, logging.
  - generation of random numbers.
- Effect-wrapped objects should be *inert* and *transparent*. That is, they
  should be unchanging data structures that fully describe the behavior to be
  performed with public members. This serves two purposes:
  - First, and most importantly, it makes unit-testing your code trivial.
    The tests will simply invoke the function, inspect the Effect-wrapped
    object for correctness, and manually resolve the effect to execute any
    callbacks in order to test the post-Effect behavior. No more need to mock
    out effects in your unit tests!
  - This allows the effect-code to be *small* and *replaceable*. Using these
    conventions, it's trivial to switch out the implementation of e.g. your
    HTTP client, using a blocking or non-blocking network library, or
    configure a threading policy. This is only possible if effect intents
    expose everything necessary via a public API to alternative
    implementation.
- To spell it out clearly: do not call Effect.perform() on Effects produced by
  your code under test: there's no point. Just grab the 'intent'
  attribute and look at its public attributes to determine if your code
  is producing the correct kind of effect intents. Separate unit tests for
  your effect *handlers* are the only tests that need concern themselves with
  true effects.
- When testing, use the utilities in the effect.testing module: they will help
  a lot.

UNFORTUNATE:

- In general, callbacks should not need to care about the implementation
  of the effect handlers. However, currently error conditions are passed to
  error handlers in an implementation-bound way: when Deferreds are involved,
  Failures are passed, whereas when synchronous exceptions are raised, a
  sys.exc_info() tuple is passed. This should be fixed somehow, maybe by
  relying on a split-out version of Twisted's Failures. Unfortunately
  splitting out Failure has a lot of blockers.

TODO:
- factor the Twisted bits out somehow. One way to do this is to make the
  implementation of perform(), and perform_effect, fundamentally
  asynchronous -- perhaps perform_effect should be passed a callback to
  invoke when complete. But, at the same time we should ensure we don't blow
  the stack on "infinite loops" of effects.
- standardize what gets passed to error handlers.

"""

from __future__ import print_function

import sys

import six

from functools import wraps

from .continuation import Continuation, trampoline

__all__ = ['Effect', 'perform', 'parallel', 'ParallelEffects']

# XXX What happens when an inner effect has no effect implementation (and thus raises NoEffectHandlerError)
# Are its error handlers invoked?


class Effect(object):
    """
    Wrap an object that describes how to perform some effect (called an
    "effect intent"), and offer a way to actually perform that effect.

    (You're an object-oriented programmer.
     You probably want to subclass this.
     Don't.)
    """
    def __init__(self, intent):
        """
        :param intent: An object that describes an effect to be
            performed. Optionally has a perform_effect(dispatcher) method.
        """
        self.intent = intent
        self.callbacks = []

    @classmethod
    def with_callbacks(klass, intent, callbacks):
        eff = klass(intent)
        eff.callbacks = callbacks
        return eff

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
        as its only argument.
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
        return Effect.with_callbacks(self.intent,
                                     self.callbacks + [(success, error)])

    def __repr__(self):
        return "Effect.with_callbacks(%r, %s)" % (self.intent, self.callbacks)

    def serialize(self):
        """
        A simple debugging tool that serializes a tree of effects into basic
        Python data structures that are useful for pretty-printing.

        If the effect intent has a "serialize" method, it will be invoked to
        represent itself in the resulting structure.
        """
        if hasattr(self.intent, 'serialize'):
            intent = self.intent.serialize()
        else:
            intent = self.intent
        return {"type": type(self), "intent": intent,
                "callbacks": self.callbacks}


def default_effect_perform(intent, box):
    """
    If the intent has a 'perform_effect' method, invoke it with this
    function as an argument. Otherwise raise NoEffectHandlerError.
    """
    if hasattr(intent, 'perform_effect'):
        return intent.perform_effect(default_effect_perform, box)
    raise NoEffectHandlerError(intent)


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
    def __init__(self, continuation, more):
        self._continuation = continuation
        self._more = more

    def succeed(self, result):
        """
        Indicate that the effect has succeeded, and the result is available.
        """
        self._continuation.more(self._more, (False, result))

    def fail(self, result):
        """
        Indicate that the effect has failed to be met. result must be an
        exc_info tuple.
        """
        self._continuation.more(self._more, (True, result))


def perform(effect, dispatcher=default_effect_perform):
    """
    Perform the intent of an effect by passing it to the dispatcher, and
    invoke callbacks associated with it.

    Note that this function does _not_ return the final result of the effect.
    You may instead want to use effect.twisted.perform.

    :returns: None
    """

    def _run_callbacks(continuation, chain, result):
        is_error, value = result
        if type(value) is Effect:
            continuation.more(
                _perform,
                Effect.with_callbacks(value.intent, value.callbacks + chain))
            return
        if not chain:
            continuation.done()
            return
        cb = chain[0][is_error]
        if cb is not None:
            result = _guard(cb, value)
        chain = chain[1:]
        continuation.more(_run_callbacks, chain, result)

    def _perform(cont, effect):
        dispatcher(
            effect.intent,
            _Box(cont,
                lambda cont, result:
                    _run_callbacks(cont, effect.callbacks, result)))

    trampoline(_perform, effect)


def _guard(f, *args, **kwargs):
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


