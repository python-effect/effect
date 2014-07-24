"""
Various functions for inspecting and restructuring effects.
"""

from __future__ import print_function

import sys

from . import Effect, guard

import six


class StubIntent(object):
    """An intent that returns a pre-specified result when performed."""
    def __init__(self, result):
        self.result = result

    def __repr__(self):
        return "StubIntent(%r)" % (self.result,)

    def perform_effect(self, dispatcher):
        return self.result


class ErrorIntent(object):
    """An intent that raises a pre-specified exception when performed."""
    def __init__(self, exception):
        self.exception = exception

    def perform_effect(self, dispatcher):
        raise self.exception


class FuncIntent(object):
    """
    An intent that returns the result of the specified function.

    This class should _only_ be used for unit tests, since the
    :func:`resolve_stubs` function automatically performs it.
    """

    def __init__(self, func):
        self.func = func

    def perform_effect(self, dispatcher):
        return self.func()


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
    Automatically resolve a FuncIntent, ErrorIntent, or StubIntent.
    """
    if type(effect.intent) in (StubIntent, ErrorIntent, FuncIntent):
        is_error, result = guard(effect.intent.perform_effect, None)
        return resolve_effect(effect, result, is_error=is_error)
    else:
        raise TypeError("resolve_stub can only resolve stubs, not %r"
                        % (effect,))


def resolve_stubs(effect):
    """
    Successively resolves effects until a non-Effect value, or an Effect with
    a non-stub intent is returned, and return that value.
    """
    # TODO: perhaps support parallel effects, as long as all the child effects
    # are stubs.
    if type(effect) is not Effect:
        raise TypeError("effect must be Effect: %r" % (effect,))

    while type(effect) is Effect:
        try:
            effect = resolve_stub(effect)
        except TypeError:
            break
    return effect
