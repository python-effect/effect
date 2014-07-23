"""Retrying effects."""

import six

from functools import partial


def retry(effect, should_retry):
    """
    Retry an effect as long as it raises an exception and as long as the
    ``should_retry`` error handler returns an Effect of True.

    If ``should_retry`` returns an Effect of False, then the returned effect
    will fail with the most recent error from func.

    :param effect.Effect effect: Any effect.
    :param should_retry: A function which should take an exc_info tuple as an
        argument and return an effect of bool.
    """

    def maybe_retry(error, retry_allowed):
        if retry_allowed:
            return try_()
        else:
            six.reraise(*error)

    def try_():
        return effect.on(
            error=lambda e: should_retry(e).on(
                success=partial(maybe_retry, e)))

    return try_()
