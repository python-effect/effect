# -*- test-case-name: effect.test_sync -*-

"""
Tools for dealing with Effects synchronously.
"""

import six
import sys

from ._base import perform
from ._utils import wraps


class NotSynchronousError(Exception):
    """Performing an effect did not immediately return a value."""


def sync_perform(dispatcher, effect):
    """
    Perform an effect, and return its ultimate result. If the final result is
    an error, the exception will be raised. This is useful for testing, and
    also if you're using blocking effect implementations.

    This requires that the effect (and all effects returned from any of its
    callbacks) be synchronous. If the result is not available immediately,
    :class:`NotSynchronousError` will be raised.
    """
    successes = []
    errors = []
    effect = effect.on(success=successes.append, error=errors.append)
    perform(dispatcher, effect)
    if successes:
        return successes[0]
    elif errors:
        six.reraise(*errors[0])
    else:
        raise NotSynchronousError("Performing %r was not synchronous!"
                                  % (effect,))


def sync_performer(f):
    """
    A decorator for performers that return a value synchronously.

    The function being decorated is expected to take a dispatcher and an intent
    (and not a box), and should return or raise normally. The wrapper function
    that this decorator returns will accept a dispatcher, an intent, and a box
    (conforming to the performer interface). The wrapper deals with putting the
    return value or exception into the box.

    Example::

        @sync_performer
        def perform_foo(dispatcher, foo):
            return do_side_effect(foo)
    """
    @wraps(f)
    def sync_wrapper(*args):
        box = args[-1]
        pass_args = args[:-1]
        try:
            box.succeed(f(*pass_args))
        except:
            box.fail(sys.exc_info())
    return sync_wrapper


def effect_performer(f):
    """
    A decorator for performers that return effect

    The function being decorated is expected to take a dispatcher and an intent
    (and not a box), and should return (dispatcher, effect) tuple. The returned
    effect will be performed using returned dispatcher.

    Example::

        @effect_performer
        def perform_foo(dispatcher, foo):
            new_disp = ComposedDispatcher(
                [special_dispatcher(foo.fields), dispatcher])
            return new_disp, foo.effect
    """
    @wraps(f)
    def eff_wrapper(*args):
        box = args[-1]
        pass_args = args[:-1]
        new_disp, eff = f(*pass_args)
        perform(new_disp, eff, eff.on(box.succeed, box.fail))
    return eff_wrapper
