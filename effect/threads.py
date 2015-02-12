import sys
from functools import partial

import six

from ._intents import FirstError
from ._sync import sync_perform, sync_performer


def perform_child(dispatcher, index_and_effect):
    """
    Perform child effect with given dispatcher and raise `FirstError` on
    any error
    """
    index, effect = index_and_effect
    try:
        return sync_perform(dispatcher, effect)
    except:
        exc_info = sys.exc_info()
        six.reraise(FirstError,
                    FirstError(exc_info=exc_info, index=index),
                    exc_info[2])


@sync_performer
def perform_parallel_with_pool(pool, dispatcher, parallel_effects):
    """
    A performer for :obj:`effect.ParallelEffects` which uses a
    ``multiprocessing.pool.ThreadPool`` to perform the child effects in
    parallel.

    Note that this *can't* be used with a ``multiprocessing.Pool``, since
    you can't pass closures to its ``map`` method.

    This function takes the pool as its first argument, so you'll need to
    partially apply it when registering it in your dispatcher, like so::

        my_pool = ThreadPool()
        parallel_performer = functools.partial(
            perform_parallel_effects_with_pool, my_pool)
        dispatcher = TypeDispatcher({ParallelEffects: parallel_performer, ...})

    NOTE: ``ThreadPool`` was broken in Python 3.4.0, but fixed by 3.4.1. This
    performer should work for any version of Python supported by Effect other
    than 3.4.0.
    """

    # pool.map raises whatever exception is raised first, which is the exact
    # behavior we want in this performer -- we just need to translate it to a
    # FirstError exception.
    return pool.map(partial(perform_child, dispatcher),
                    enumerate(parallel_effects.effects))


@sync_performer
def perform_serially(disp, intent):
    """
    Performs parallel effects serially. Useful when testing or simple cases
    """
    return map(partial(perform_child, disp), enumerate(intent.effects))
