# -*- test-case-name: effect.test_intents -*-

from __future__ import print_function, absolute_import
from characteristic import attributes

from ._base import Effect
from ._sync import sync_performer


@attributes(['effects'], apply_with_init=False, apply_immutable=True)
class ParallelEffects(object):
    """
    An effect intent that asks for a number of effects to be run in parallel,
    and for their results to be gathered up into a sequence.

    There is an implementation of this intent for Twisted, as long as the
    effect.twisted.perform function is used to perform the effect.

    Alternative implementations could run the child effects in threads, or use
    some other concurrency mechanism. Of course, the implementation strategy
    for this effect will need to cooperate with the effects being parallelized
    -- there's not much use running a Deferred-returning effect in a thread.
    """
    def __init__(self, effects):
        self.effects = effects


def parallel(effects):
    """
    Given multiple Effects, return one Effect that represents the aggregate of
    all of their effects.
    The result of the aggregate Effect will be a list of their results, in
    the same order as the input to this function.
    """
    return Effect(ParallelEffects(list(effects)))


@attributes(['delay'], apply_with_init=False, apply_immutable=True)
class Delay(object):
    """
    An effect which represents a delay in time.

    When performed, the specified delay will pass and then the effect will
    result in None.
    """
    def __init__(self, delay):
        self.delay = delay


@attributes(['result'], apply_with_init=False, apply_immutable=True)
class ConstantIntent(object):
    """An intent that returns a pre-specified result when performed."""
    def __init__(self, result):
        self.result = result


@sync_performer
def perform_constant(dispatcher, intent):
    return intent.result


@attributes(['exception'], apply_with_init=False, apply_immutable=True)
class ErrorIntent(object):
    """An intent that raises a pre-specified exception when performed."""
    def __init__(self, exception):
        self.exception = exception


@sync_performer
def perform_error(dispatcher, intent):
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
        self.func = func


@sync_performer
def perform_func(dispatcher, intent):
    return intent.func()
