"""
A system for helping you separate your IO and state-manipulation code
(hereafter referred to as "effects") from everything else, thus allowing
the majority of your code to be trivially testable and composable (that is,
have the general benefits of purely functional code).

Keywords: monad, IO, stateless.

The core behavior is as follows:
- Effectful operations should be represented as plain Python objects which
  will hereafter be referred to as "effect requests". These objects should be
  wrapped in an instance of :class:`Effect`.
- This library has almost no expectation of effect requests: it's up to users
  to with them what they will[1].
- In most cases where you'd perform effects in your code, you should instead
  return an Effect wrapping the effect request.
- Separately, some function should exist that takes an effect request
  and performs the requested effect.
- To represent work to be done *after* an effect, use Effect.on_success,
  .on_error, etc.
- Near the top level of your code, invoke Effect.perform on the Effect you
  have produced. This will invoke the effect-performing handler specific to
  the wrapped object, and invoke callbacks as necessary.
- If the callbacks return another instance of Effect, that Effect will be
  performed before continuing back down the callback chain.

[1] Actually, as a convenience, perform_effect can be implemented as a method
    on the wrapped object, but the implementation can also be specified in a
    separate handlers table.

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
    No longer will you need to use mocks or stubs to fake out parts of your
    system for the majority of your tests. The tests will simply invoke the
    function, inspect the Effect-wrapped object for correctness, and manually
    resolve the effect to execute any callbacks in order to test the
    post-Effect behavior. No more need to mock out effects in your unit tests!
  - This allows the effect-code to be *small* and *replaceable*. Using these
    conventions, it's trivial to switch out the implementation of e.g. your
    HTTP client, and even to use either a blocking or non-blocking
    interface, or to configure a threading policy. This is only possible if
    effect requests expose everything necessary via a public API to
    alternative implementations.
- To spell it out clearly: do not call Effect.perform() on Effects produced by
  your code under test: there's no point. Just grab the 'effect_request'
  attribute and look at its public attributes to determine if your code
  is producing the correct kind of effect requests. Separate unit tests for
  your effect *handlers* are the only tests that potentially need mocking,
  stubbing, or otherwise concern itself with true effects.

Twisted's Deferreds are supported directly; any effect handler that returns
a Deferred will seamlessly integrate with on_success, on_error etc callbacks.

Support for AsyncIO tasks, and other callback-oriented frameworks, is to be
done, but should be trivial.
"""

from __future__ import print_function

import sys
from functools import partial


class NoEffectHandlerError(Exception):
    """
    No Effect handler could be found for the given Effect-wrapped object.
    """


class Effect(object):
    """
    Wrap an object that describes how to perform some effect (called an
    "effect request"), and offer a way to actually perform that effect.

    (You're an object-oriented programmer.
     You probably want to subclass this.
     Don't.)
    """
    def __init__(self, effect_request):
        """
        :param effect_request: An object that describes an effect to be
            performed. Optionally has a perform_effect(handlers) method.
        """
        self.effect_request = effect_request

    def perform(self, handlers):
        """
        Perform an effect by dispatching to the appropriate handler.

        If the type of the effect request is in ``handlers``, that handler
        will be invoked. Otherwise a ``perform_effect`` method will be invoked
        on the effect request.

        If an effect handler returns another :class:`Effect` instance, that
        effect will be performed immediately before returning.

        :param handlers: A dictionary mapping types of effect requests
            to handler functions.
        :raise NoEffectHandlerError: When no handler was found for the effect
            request.
        """
        func = None
        if type(self.effect_request) in handlers:
            func = partial(handlers[type(self.effect_request)],
                           self.effect_request)
        if func is None:
            func = getattr(self.effect_request, 'perform_effect', None)
        if func is None:
            raise NoEffectHandlerError(self.effect_request)
        result = func(handlers)
        if type(result) is Effect:
            return result.perform(handlers)
        return result

    def on_success(self, callback):
        """
        Return a new Effect that will invoke the associated callback when this
        Effect completes succesfully.
        """
        return Effect(Callbacks(self, callback, None))

    def on_error(self, callback):
        """
        Return a new Effect that will invoke the associated callback when this
        Effect fails.

        The callback will be invoked with the sys.exc_info() exception tuple as its
        only argument.
        """
        return Effect(Callbacks(self, None, callback))

    def after(self, callback):
        """
        Return a new Effect that will invoke the associated callback when this
        Effect completes, whether successfully or in error.
        """
        return Effect(Callbacks(self, callback, callback))

    def on(self, success, error):
        """
        Return a new Effect that will invoke either the success or error
        callbacks provided based on whether this Effect completes sucessfully
        or in error.
        """
        return Effect(Callbacks(self, success, error))


def gather(effects):
    """
    Given multiple Effects, return one Effect that represents the aggregate of
    all of their effects.
    The result of the aggregate Effect will be a list of their results, in
    the same order as the input to this function.
    """
    return


class Callbacks(object):
    """
    A representation of the fact that a call should be made after some Effect is
    performed.

    This supports both handling of successful results (normal return values)
    and failing results (exceptions raised from the inner effect), by invoking
    either a "callback" or "errback".

    Hint: This is kinda like bind (>>=).
    """
    def __init__(self, effect, callback, errback):
        self.effect = effect
        self.callback = callback
        self.errback = errback

    def perform_effect(self, handlers):
        try:
            result = self.effect.perform(handlers)
        except:
            if self.errback is not None:
                return self.errback(sys.exc_info())
            else:
                raise
        else:
            if hasattr(result, 'addCallbacks'):
                callback = (self.callback
                            if self.callback is not None
                            else lambda x: x)
                errback = (self.errback
                           if self.errback is not None
                           else lambda x: x)
                return result.addCallbacks(callback, errback)
            elif self.callback is not None:
                return self.callback(result)
            else:
                return result
