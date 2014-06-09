"""
Various functions for inspecting and restructuring effects.
"""

from __future__ import print_function

import sys

from . import Effect, guard

import six


class StubIntent(object):
    """An effect that returns a pre-specified result."""
    def __init__(self, result):
        self.result = result

    def __repr__(self):
        return "StubIntent(%r)" % (self.result,)

    def perform_effect(self, dispatcher):
        return self.result


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
    Like resolve_effect, but automatically uses the result available in a
    StubIntent.
    """
    return resolve_effect(effect, effect.intent.result)
