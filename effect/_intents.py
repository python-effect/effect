# -*- test-case-name: effect.test_intents -*-

"""
Standard intents and some of their performers.

The :obj:`base_dispatcher` object in this module is a dispatcher which provides
standard performers for intents which really only have one reasonable way to be
performed, sunch as :class:`Func`, :class:`Error`, and :class:`Constant`.
"""


from __future__ import print_function, absolute_import

import time

import attr

from ._base import Effect
from ._sync import sync_performer
from ._dispatcher import TypeDispatcher


@attr.s
class ParallelEffects(object):
    """
    An effect intent that asks for a number of effects to be run in parallel,
    and for their results to be gathered up into a sequence.

    :func:`effect.async.perform_parallel_async` can perform this Intent
    assuming all child effects have asynchronous performers.
    :func:`effect.threads.perform_parallel_with_pool` can perform blocking
    performers in a thread pool.

    Note that any performer for this intent will need to be compatible with
    performers for all of its child effects' intents. Notably, if child effects
    have blocking performers, the threaded performer should be used, and if
    they're asynchronous, the asynchronous performer should be used.

    Performers of this intent must fail with a :obj:`FirstError` exception when
    any child effect fails, representing the first error.

    :param effects: Effects to be performed in parallel.
    """

    effects = attr.ib()


def parallel(effects):
    """
    Given multiple Effects, return one Effect that represents the aggregate of
    all of their effects.  The result of the aggregate Effect will be a list of
    their results, in the same order as the input to this function. If any
    child effect fails, the first such failure will be propagated as a
    :obj:`FirstError` exception. If additional error information is desired,
    use :func:`parallel_all_errors`.

    This is just a convenience wrapper for returning of Effect of
    :obj:`ParallelEffects`.

    :param effects: Effects which should be performed in parallel.
    :return: An Effect that results in a list of results, or which fails with
        a :obj:`FirstError`.
    """
    return Effect(ParallelEffects(list(effects)))


def parallel_all_errors(effects):
    """
    Given multiple Effects, return one Effect that represents the aggregate of
    all of their effects.  The result of the aggregate Effect will be a list of
    their results, in the same order as the input to this function.

    This is like :func:`parallel`, but it differs in that exceptions from all
    child effects will be accumulated and provided in the return value, instead
    of just the first one.

    :param effects: Effects which should be performed in parallel.
    :return: An Effect that results in a list of ``(is_error, result)`` tuples,
        where ``is_error`` is True if the child effect raised an exception, in
        which case ``result`` will be an exc_info tuple. If ``is_error`` is
        False, then ``result`` will just be the result as provided by the child
        effect.
    """
    effects = [effect.on(success=lambda r: (False, r),
                         error=lambda e: (True, e))
               for effect in effects]
    return Effect(ParallelEffects(list(effects)))


@attr.s
class FirstError(Exception):
    """
    One of the effects in a :obj:`ParallelEffects` resulted in an error. This
    represents the first such error that occurred.
    """
    exc_info = attr.ib()
    index = attr.ib()

    def __str__(self):
        return '(index=%s) %s: %s' % (
            self.index, self.exc_info[0].__name__, self.exc_info[1])


@attr.s
class Delay(object):
    """
    An intent which represents a delay in time.

    When performed, the specified delay will pass and then the effect will
    result in None.

    :param float delay: The number of seconds to delay.
    """
    delay = attr.ib()


@sync_performer
def perform_delay_with_sleep(dispatcher, intent):
    """Perform a :obj:`Delay` by calling ``time.sleep``."""
    time.sleep(intent.delay)


@attr.s
class Constant(object):
    """
    An intent that returns a pre-specified result when performed.

    :param result: The object which the Effect will result in.
    """
    result = attr.ib()


@sync_performer
def perform_constant(dispatcher, intent):
    """Performer for :class:`Constant`."""
    return intent.result


@attr.s
class Error(object):
    """
    An intent that raises a pre-specified exception when performed.

    :param BaseException exception: Exception instance to raise.
    """
    exception = attr.ib()


@sync_performer
def perform_error(dispatcher, intent):
    """Performer for :class:`Error`."""
    raise intent.exception


@attr.s(init=False)
class Func(object):
    """
    An intent that returns the result of the specified function.

    Note that Func is something of a cop-out. It doesn't follow the
    convention of an intent being transparent data that is easy to introspect,
    since it just wraps an opaque callable. This has two drawbacks:

    - it's harder to test, since the only thing you can do is call the
      function, instead of inspect its data.
    - it doesn't offer any ability for changing the way the effect is
      performed.

    If you use Func in your application code, know that you are giving
    up some ease of testing and flexibility. It's preferable to represent your
    intents as inert objects with public attributes of simple data. However,
    this is useful for integrating wih "legacy" side-effecting code in a quick
    way.

    :param func: The function to call when this intent is performed.
    :param args: Positional arguments to pass to the function.
    :param kwargs: Keyword arguments to pass to the function.
    """
    func = attr.ib()
    args = attr.ib()
    kwargs = attr.ib()

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs


@sync_performer
def perform_func(dispatcher, intent):
    """Performer for :class:`Func`."""
    return intent.func(*intent.args, **intent.kwargs)


base_dispatcher = TypeDispatcher({
    Constant: perform_constant,
    Error: perform_error,
    Func: perform_func,
})
