# -*- test-case-name: effect.test_sync -*-

import six
import sys

from ._base import perform


class NotSynchronousError(Exception):
    """Performing an effect did not immediately return a value."""


def sync_perform(dispatcher, effect):
    """
    Perform an effect, and return its ultimate result. If the final result is
    an error, the exception will be raised. This is useful for testing, and
    also if you're using blocking effect implementations.

    This requires that the effect (and all effects returned from any of its
    callbacks) to be synchronous. If this is not the case, NotSynchronousError
    will be raised.
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

    The returned function accepts an intent and a box, and the wrapped
    function will be called with only the intent. The result of the
    function will be provided as the result to the box.
    """
    def inner(dispatcher, intent, box):
        try:
            box.succeed(f(dispatcher, intent))
        except:
            box.fail(sys.exc_info())
    return inner
