"""
Various functions for inspecting and restructuring effects.
"""

from effect import Effect


class StubIntent(object):
    """An effect that returns a pre-specified result."""
    def __init__(self, result):
        self.result = result

    def __repr__(self):
        return "StubIntent(%r)" % (self.result,)

    def perform_effect(self, handlers):
        return self.result


def resolve_effect(effect, result):
    """
    Supply a result for an effect, allowing its callbacks to run.

    The return value of the last callback is returned, unless any callback
    returns another Effect, in which case an Effect representing that
    operation plus the remaining callbacks will be returned.

    This allows you to test your code in a somewhat "channel"-oriented
    way:

        eff = do_thing()
        next_eff = resolve_effect(eff, first_result)
        next_eff = resolve_effect(next_eff, second_result)
        result = resolve_effect(next_eff, third_result)

    Equivalently, if you don't care about intermediate results:

        result = resolve_effect(
            resolve_effect(
                resolve_effect(
                    do_thing(),
                    first_result),
                second_result),
            third_result)

    NOTE: Currently, parallel effects are not supported.
    NOTE: Currently, error handlers are not supported.
    """
    for i, (callback, errback) in enumerate(effect.callbacks):
        result = callback(result)
        if type(result) is Effect:
            # Wrap all the remaining callbacks around the new effect we just
            # found, so that resolving it will run everything, and not just
            # the nested ones.
            return Effect.with_callbacks(
                result.intent,
                result.callbacks + effect.callbacks[i + 1:])
    return result


def resolve_stub(effect):
    """
    Like resolve_effect, but automatically uses the result available in a
    StubIntent.
    """
    return resolve_effect(effect, effect.intent.result)
