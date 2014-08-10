"""
Various functions for inspecting and restructuring effects.
"""

from __future__ import print_function

import sys

from . import Effect, guard

import six


class StubIntent(object):
    """
    An intent which wraps another intent, to flag that the intent should
    be automatically resolved by :func:`resolve_stub`.

    This intent is intentionally not performable by any default mechanism.
    """

    def __init__(self, intent):
        self.intent = intent


def resolve_effect(effect, result, is_error=False):
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

    NOTE: parallel effects have no special support. They can be resolved with
    a sequence, and if they're returned from another effect's callback they
    will be returned just like any other effect.
    """
    for i, (callback, errback) in enumerate(effect.callbacks):
        cb = errback if is_error else callback
        if cb is None:
            continue
        is_error, result = guard(cb, result)
        if type(result) is Effect:
            return Effect(
                result.intent,
                callbacks=result.callbacks + effect.callbacks[i + 1:])
    if is_error:
        six.reraise(*result)
    return result


def fail_effect(effect, exception):
    """
    Resolve an effect with an exception, so its error handler will be run.
    """
    try:
        raise exception
    except:
        return resolve_effect(effect, sys.exc_info(), is_error=True)


def resolve_stub(effect):
    """
    Automatically perform an effect, if its intent is a StubIntent.
    """
    # TODO: perhaps support parallel effects, as long as all the child effects
    # are stubs.
    if type(effect.intent) is StubIntent:
        is_error, result = guard(effect.intent.intent.perform_effect, None)
        return resolve_effect(effect, result, is_error=is_error)
    else:
        raise TypeError("resolve_stub can only resolve stubs, not %r"
                        % (effect,))


def resolve_stubs(effect):
    """
    Successively performs effects with resolve_stub until a non-Effect value,
    or an Effect with a non-stub intent is returned, and return that value.
    """
    if type(effect) is not Effect:
        raise TypeError("effect must be Effect: %r" % (effect,))

    while type(effect) is Effect:
        try:
            effect = resolve_stub(effect)
        except TypeError:
            break
    return effect
