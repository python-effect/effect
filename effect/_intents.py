# -*- test-case-name: effect.test_intents -*-

"""
Standard intents and some of their performers.

The :obj:`base_dispatcher` object in this module is a dispatcher which provides
standard performers for intents which really only have one reasonable way to be
performed, sunch as :class:`Func`, :class:`Error`, and
:class:`Constant`.

Other intents, such as :class:`ParallelEffects` and :class:`Delay`, need to
have a performer specified elsewhere, since the performers are reliant on
choices made by the application author. :module:`effect.twisted` provides a
Twisted-specific dispatcher for these.
"""


from __future__ import print_function, absolute_import
from characteristic import attributes, Attribute
from functools import partial
from itertools import count

from ._base import Effect, perform
from ._sync import sync_performer
from ._dispatcher import TypeDispatcher


@attributes(['effects'], apply_with_init=False, apply_immutable=True)
class ParallelEffects(object):
    """
    An effect intent that asks for a number of effects to be run in parallel,
    and for their results to be gathered up into a sequence.

    :func:`perform_parallel_async` can perform this Intent assuming all child
    effects have asynchronous performers.
    """
    def __init__(self, effects):
        """
        :param effects: Effects which should be performed in parallel.
        """
        self.effects = effects


def parallel(effects):
    """
    Given multiple Effects, return one Effect that represents the aggregate of
    all of their effects.  The result of the aggregate Effect will be a list of
    their results, in the same order as the input to this function.

    :param effects: Effects which should be performed in parallel.
    """
    return Effect(ParallelEffects(list(effects)))


@attributes(['exception', 'index'])
class FirstError(Exception):
    """
    One of the effects in a :obj:`ParallelEffects` resulted in an error. This
    represents the first such error that occurred.
    """
    def __str__(self):
        return '(index=%s) %s: %s' % (
            self.index, type(self.exception).__name__, self.exception)


def perform_parallel_async(dispatcher, intent, box):
    """
    A performer for :obj:`ParallelEffects` which works if all child Effects are
    intrinsically asynchronous. Use this for things like Twisted, asyncio, etc.

    WARNING: If this is used when child Effects have blocking performers, it
    will run them in serial, not parallel.
    """
    effects = list(intent.effects)
    if not effects:
        box.succeed([])
        return
    num_results = count()
    results = [None] * len(effects)

    def succeed(index, result):
        results[index] = result
        if next(num_results) + 1 == len(effects):
            box.succeed(results)

    def fail(index, result):
        box.fail((FirstError,
                  FirstError(exception=result[1], index=index),
                  result[2]))

    for index, effect in enumerate(effects):
        perform(
            dispatcher,
            effect.on(
                success=partial(succeed, index),
                error=partial(fail, index)))


@attributes(['delay'], apply_with_init=False, apply_immutable=True)
class Delay(object):
    """
    An intent which represents a delay in time.

    When performed, the specified delay will pass and then the effect will
    result in None.
    """
    def __init__(self, delay):
        """
        :param float delay: The number of seconds to delay.
        """
        self.delay = delay


@attributes(['result'], apply_with_init=False, apply_immutable=True)
class Constant(object):
    """An intent that returns a pre-specified result when performed."""
    def __init__(self, result):
        """
        :param result: The object which the Effect should result in.
        """
        self.result = result


@sync_performer
def perform_constant(dispatcher, intent):
    """Performer for :class:`Constant`."""
    return intent.result


@attributes(['exception'], apply_with_init=False, apply_immutable=True)
class Error(object):
    """An intent that raises a pre-specified exception when performed."""
    def __init__(self, exception):
        self.exception = exception


@sync_performer
def perform_error(dispatcher, intent):
    """Performer for :class:`Error`."""
    raise intent.exception


@attributes(['func'], apply_with_init=False, apply_immutable=True)
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
    """
    def __init__(self, func):
        """
        :param func: The function to call when this intent is performed.
        """
        self.func = func


@sync_performer
def perform_func(dispatcher, intent):
    """Performer for :class:`Func`."""
    return intent.func()


base_dispatcher = TypeDispatcher({
    Constant: perform_constant,
    Error: perform_error,
    Func: perform_func,
})
