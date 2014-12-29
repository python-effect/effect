# -*- test-case-name: effect.test_intents -*-

"""
Standard intents and some of their performers.

The :obj:`base_dispatcher` object in this module is a dispatcher which provides
standard performers for intents which really only have one reasonable way to be
performed, sunch as :class:`FuncIntent`, :class:`ErrorIntent`, and
:class:`ConstantIntent`.

Other intents, such as :class:`ParallelEffects` and :class:`Delay`, need to
have a performer specified elsewhere, since the performers are reliant on
choices made by the application author. :module:`effect.twisted` provides a
Twisted-specific dispatcher for these.
"""


from __future__ import print_function, absolute_import
from characteristic import attributes

from ._base import Effect
from ._sync import sync_performer
from ._dispatcher import TypeDispatcher


@attributes(['effects'], apply_with_init=False, apply_immutable=True)
class ParallelEffects(object):
    """
    An effect intent that asks for a number of effects to be run in parallel,
    and for their results to be gathered up into a sequence.

    Performers for this intent could perform the child effects in threads, or
    use some other concurrency mechanism like Twisted's ``gatherResults``. Of
    course, the implementation strategy for this effect will need to cooperate
    with the performers of the Effects being parallelized -- e.g., a
    ``@deferred_performer`` performer for a child intent should not be used
    with a thread-dispatching performer for :class:`ParallelEffects`.
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
class ConstantIntent(object):
    """An intent that returns a pre-specified result when performed."""
    def __init__(self, result):
        """
        :param result: The object which the Effect should result in.
        """
        self.result = result


@sync_performer
def perform_constant(dispatcher, intent):
    """Performer for :class:`ConstantIntent`."""
    return intent.result


@attributes(['exception'], apply_with_init=False, apply_immutable=True)
class ErrorIntent(object):
    """An intent that raises a pre-specified exception when performed."""
    def __init__(self, exception):
        self.exception = exception


@sync_performer
def perform_error(dispatcher, intent):
    """Performer for :class:`ErrorIntent`."""
    raise intent.exception


@attributes(['func'], apply_with_init=False, apply_immutable=True)
class FuncIntent(object):
    """
    An intent that returns the result of the specified function.

    Note that FuncIntent is something of a cop-out. It doesn't follow the
    convention of an intent being transparent data that is easy to introspect,
    since it just wraps an opaque callable. This has two drawbacks:

    - it's harder to test, since the only thing you can do is call the
      function, instead of inspect its data.
    - it doesn't offer any ability for changing the way the effect is
      performed.

    If you use FuncIntent in your application code, know that you are giving
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
    """Performer for :class:`FuncIntent`."""
    return intent.func()


base_dispatcher = TypeDispatcher({
    ConstantIntent: perform_constant,
    ErrorIntent: perform_error,
    FuncIntent: perform_func,
})
