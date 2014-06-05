"""
Twisted integration for the Effect library.

This is largely concerned with bridging the gap between Effects and Deferreds.
"""

from __future__ import absolute_import

from functools import wraps

from twisted.internet.defer import Deferred, maybeDeferred
from twisted.python.failure import Failure

from . import default_effect_perform, perform as base_perform, Effect


def perform(effect, dispatcher=default_effect_perform):
    """
    Perform an effect, and return a Deferred that will fire with that effect's
    ultimate result.
    """
    d = Deferred()
    eff = effect.on(success=d.callback,
                    error=lambda e: Failure(e[1], e[0], e[2]))
    base_perform(eff)
    return d


def deferred_performer(func):
    """
    Allows you to define your effect-performing functions to return Deferreds.
    If you use this, you don't have to care about putting your results into
    the result box -- Effect callbacks will automatically be invoked when the
    Deferred's result is available.

    Usage:

        class MyIntent(object):
            @deferred_performer
            def perform_effect(self):
                return get_a_deferred()

    """
    @wraps(func)
    def perform_effect(self, dispatcher, box):
        d = maybeDeferred(func, self, dispatcher)
        d.addCallbacks(
            box.succeed,
            lambda f: box.fail((f.value, f.type, f.tb)))
    return perform_effect


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

    def serialize(self):
        return {"type": type(self),
                "effects": [e.serialize() for e in self.effects]}

    @deferred_performer
    def perform_effect(self, dispatcher):
        from twisted.internet.defer import gatherResults, maybeDeferred
        return gatherResults(
            [maybeDeferred(perform, e, dispatcher) for e in self.effects])


def parallel(effects):
    """
    Given multiple Effects, return one Effect that represents the aggregate of
    all of their effects.
    The result of the aggregate Effect will be a list of their results, in
    the same order as the input to this function.
    """
    return Effect(ParallelEffects(list(effects)))
