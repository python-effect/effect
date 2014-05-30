"""
Various functions for inspecting and restructuring effects.
"""

from effect import Callbacks, Effect


class StubRequest(object):
    """An effect that returns a pre-specified result."""
    def __init__(self, result):
        self.result = result

    def __repr__(self):
        return "StubRequest(%r)" % (self.result,)

    def perform_effect(self, handlers):
        return self.result


def get_request(effect):
    """
    Given an effect, get the first actual effect request it represents.

    Note that this function can only traverse effects that it knows about;
    if there's some custom effect that wraps another effect, it won't be able
    to find the inner effect.

    NOTE: Currently, parallel effects are not supported.
    """
    return serialize(effect)[0]


def serialize(effect):
    """
    Return a list of effect requests, in order that callbacks will be run.

    In other words, if you have an effect like this:

        do_thing().on_success(foo).on_error(bar)

    This will return:

        [do_thing().request, Callbacks success=foo, Callbacks error=bar]

    NOTE: Currently, parallel effects are not supported.
    """
    result = []
    while True:
        result.append(effect.request)
        if type(effect.request) is Callbacks:
            effect = effect.request.effect
        else:
            break
    result.reverse()
    return result


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
    """
    sequence = serialize(effect)
    for i, callback in enumerate(sequence[1:]):
        result = callback.callback(result)
        if type(result) is Effect:
            # We want to return a new effect with all the remaining callbacks
            # attached to it, so it can naturally be passed to resolve_effect.
            # unfortunately this means we need to rebuild the partial callback
            # chain.
            eff = result
            for callback in sequence[i + 2:]:
                eff = eff.on(success=callback.callback,
                             error=callback.errback)
            return eff
    return result


def resolve_stub(effect):
    """
    Like resolve_effect, but automatically uses the result available in a
    StubRequest.
    """
    return resolve_effect(effect, get_request(effect).result)
