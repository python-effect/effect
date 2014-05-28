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
  to do with them what they will[1].
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
    The tests will simply invoke the function, inspect the Effect-wrapped
    object for correctness, and manually resolve the effect to execute any
    callbacks in order to test the post-Effect behavior. No more need to mock
    out effects in your unit tests!
  - This allows the effect-code to be *small* and *replaceable*. Using these
    conventions, it's trivial to switch out the implementation of e.g. your
    HTTP client, using a blocking or non-blocking network library, or
    configure a threading policy. This is only possible if effect requests
    expose everything necessary via a public API to alternative
    implementation.
- To spell it out clearly: do not call Effect.perform() on Effects produced by
  your code under test: there's no point. Just grab the 'request'
  attribute and look at its public attributes to determine if your code
  is producing the correct kind of effect requests. Separate unit tests for
  your effect *handlers* are the only tests that need concern themselves with
  true effects.

Twisted's Deferreds are supported directly; any effect handler that returns
a Deferred will seamlessly integrate with on_success, on_error etc callbacks.

Support for AsyncIO tasks, and other callback-oriented frameworks, is to be
done, but should be trivial.

UNFORTUNATE:

- In general, callbacks should not need to care about the implementation
  of the effect handlers. However, currently error conditions are passed to
  error handlers in an implementation-bound way: when Deferreds are involved,
  Failures are passed, whereas when synchronous exceptions are raised, a
  sys.exc_info() tuple is passed. This should be fixed somehow, maybe by
  relying on a split-out version of Twisted's Failures.
- It's unclear whether the handler-table approach to effect dispatching is
  flexible enough for all/common cases. For example, a system which mixes
  asynchronous and synchronous IO (because multiple libraries that do things
  in different ways are both in use) won't have a way to differentiate an
  asynchronous HTTPRequest from a synchronous HTTPRequest in the same call to
  Effect.perform. Likewise, a threaded implementation of parallel should only
  be used when in the context of Deferred-returning effects.
- Actually testing code that uses this framework may still be tedious
  sometimes, since effects can be wrapped within dozens of levels of
  indirections of callbacks, parallels, and so on. Careful use of mocking may
  help.
- Maybe allowing requests to provide their own implementations of
  perform_effect is a bad idea; if users don't get used to constructing their
  own set of handlers, then when they need to customize an effect handler it
  may require an unfortunately large refactoring.
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
    def __init__(self, request):
        """
        :param request: An object that describes an effect to be
            performed. Optionally has a perform_effect(handlers) method.
        """
        self.request = request

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
        if type(self.request) in handlers:
            func = partial(handlers[type(self.request)],
                           self.request)
        if func is None:
            func = getattr(self.request, 'perform_effect', None)
        if func is None:
            raise NoEffectHandlerError(self.request)
        result = func(handlers)
        # Not happy about this Twisted knowledge being in perform...
        if hasattr(result, 'addCallback'):
            return result.addCallback(self._maybe_chain, handlers)
        else:
            return self._maybe_chain(result, handlers)

    def _maybe_chain(self, result, handlers):
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

    def __repr__(self):
        return "Effect(%r)" % (self.request,)

    def serialize(self):
        """
        A simple debugging tool that serializes a tree of effects into basic
        Python data structures that are useful for pretty-printing.

        If the effect request has a "serialize" method, it will be invoked to
        represent itself in the resulting structure.
        """
        if hasattr(self.request, 'serialize'):
            request = self.request.serialize()
        else:
            request = self.request
        return {"type": type(self), "request": request}


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

    def __repr__(self):
        return "Callbacks(%r, %r, %r)" % (self.effect, self.callback, self.errback)

    def serialize(self):
        return {"type": type(self),
                "effect": self.effect.serialize(),
                "callback": self.callback,
                "errback": self.errback}

    def perform_effect(self, handlers):
        try:
            result = self.effect.perform(handlers)
        except:
            if self.errback is not None:
                return self.errback(sys.exc_info())
            else:
                raise
        else:
            # Consider separating this implementation out to a dispatch table
            # based on the return value's type, to support AsyncIO,
            # concurrent.futures, etc.
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


class ParallelEffects(object):
    """
    An effect request that asks for a number of effects to be run in parallel,
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

    def serialize(self):
        return {"type": type(self),
                "effects": [e.serialize() for e in self.effects]}

    def perform_effect(self, handlers):
        from twisted.internet.defer import gatherResults, maybeDeferred
        return gatherResults(
            [maybeDeferred(e.perform, handlers) for e in self.effects])


def parallel(effects):
    """
    Given multiple Effects, return one Effect that represents the aggregate of
    all of their effects.
    The result of the aggregate Effect will be a list of their results, in
    the same order as the input to this function.
    """
    return Effect(ParallelEffects(effects))
