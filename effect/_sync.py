# -*- test-case-name: effect.test_sync -*-
from ._base import perform
import six


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
