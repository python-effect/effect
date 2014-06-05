"""
Twisted integration for the Effect library.

This is largely concerned with bridging the gap between Effects and Deferreds.
"""

from __future__ import absolute_import

from twisted.internet.defer import Deferred, maybeDeferred
from twisted.python.failure import Failure

from . import default_effect_perform, perform as base_perform


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
    If you use this, you don't have to care about invoking the effect
    continuation -- Effect callbacks will automatically be invoked when the
    Deferred's result is available.

    Usage:

        class MyIntent(object):
            @deferred_performer
            def perform_effect(self, intent):
                return get_a_deferred()

    """
    @wraps(func)
    def perform_effect(intent, continuation):
        d = maybeDeferred(func, intent)
        d.addCallbacks(
            continuation.succeed,
            lambda f: continuation.fail((f.value, f.type, f.tb)))
    return perform_effect
