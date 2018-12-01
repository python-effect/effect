"""Generic asynchronous performers."""

from functools import partial
from itertools import count

from ._base import perform
from ._intents import FirstError


def perform_parallel_async(dispatcher, intent, box):
    """
    A performer for :obj:`ParallelEffects` which works if all child Effects are
    already asynchronous. Use this for things like Twisted, asyncio, etc.

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
                  FirstError(exc_info=result, index=index),
                  result[2]))

    for index, effect in enumerate(effects):
        perform(
            dispatcher,
            effect.on(
                success=partial(succeed, index),
                error=partial(fail, index)))
