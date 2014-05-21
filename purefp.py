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
    interface, or to configure a threading policy.

In fact, Twisted is supported out of the box: any Effect handlers that
return Deferreds will work seamlessly [describe this more -radix]. Other
asynchronous frameworks can be trivially added.
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
            return result.perform_effect(result)
        return result

    def on_success(self, callback):
        """
        Return a new Effect that will invoke the associated callback when this
        Effect completes succesfully.
        """
        return Effect(Callback(self, callback))

    def on_error(self, callback):
        """
        Return a new Effect that will invoke the associated callback when this
        Effect fails.
        """
        return Effect(Errback(self, callback))

    def after(self, callback):
        """
        Return a new Effect that will invoke the associated callback when this
        Effect completes, whether successfully or in error.
        """
        return Effect(After(self, callback))

    def on(self, success, error):
        """
        Return a new Effect that will invoke either the success or error callbacks
        provided based on whether this Effect completes sucessfully or in error.
        """



def gather(effects):
    """
    Given multiple Effects, return one Effect that represents the aggregate of
    all of their effects.
    The result of the aggregate Effect will be a list of their results, in
    the same order as the input to this function.
    """
    return


class Callback(object):
    """
    A representation of the fact that a call should be made after some Effect is performed.

    Hint: This is kinda like bind (>>=).
    """
    def __init__(self, effect, callback):
        self.effect = effect
        self.callback = callback

    def perform_effect(self, handlers):
        result = self.effect.perform(handlers)
#         if hasattr(result, 'addCallback'):
#             result.addCallback(self.callback)
#         else:
        return self.callback(result)


class Errback(object):
    """
    A representation of the fact that a call should be made after some Effect fails.
    """
    def __init__(self, effect, callback):
        self.effect = effect
        self.callback = callback

    def perform_effect(self, handlers):
        try:
            result = perform(self.effect, handlers)
#             if hasattr(result, 'addErrback'):
#                 result.addErrback(self.callback)
#             else:
            self.callback(result)
        except:
            self.callback(sys.exc_info())


class After(object):
    """
    A representation of the fact that a call should be made after some Effect is
    performed, whether it succeeds or fails.
    """
    def __init__(self, effect, callback):
        self.effect = effect
        self.callback = callback

    def perform_effect(self, handlers):
        try:
            result = perform(self.effect, handlers)
#             if hasattr(result, 'addBoth'):
#                 result.addErrback(self.callback)
#             else:
            self.callback(result)
        except:
            self.callback(sys.exc_info())
