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


def sync_perform(dispatcher, effect, recurse_effects=True):
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
    perform(dispatcher, effect, recurse_effects=recurse_effects)
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

    The wrapped function is expected to take a dispatcher and an intent (and
    not a box), and should return or raise normally. The decorator deals with
    putting the result or exception into the box.
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
