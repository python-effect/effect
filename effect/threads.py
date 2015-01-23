import sys

from functools import partial

import six

from ._intents import FirstError
from ._sync import sync_perform, sync_performer


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
    """
    try:
        return pool.map(partial(sync_perform, dispatcher),
                        parallel_effects.effects)
    except:
        exc_info = sys.exc_info()
        six.reraise(FirstError, FirstError(exception=exc_info[1], index=0),
                    exc_info[2])
