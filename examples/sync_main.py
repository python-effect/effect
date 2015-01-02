from functools import partial
from multiprocessing.pool import ThreadPool

from effect import (
    ComposedDispatcher,
    ParallelEffects,
    TypeDispatcher,
    perform_parallel_with_pool,
    sync_perform)

from .github_example import main_effect
from .http_intent import HTTPRequest
from .readline_intent import ReadLine, perform_readline_stdin
from .sync_http import perform_request_requests


def get_dispatcher():
    my_pool = ThreadPool()
    pool_performer = partial(perform_parallel_with_pool, my_pool)
    return ComposedDispatcher([
        TypeDispatcher({
            ReadLine: perform_readline_stdin,
            HTTPRequest: perform_request_requests,
            ParallelEffects: pool_performer,
        })
    ])


def main():
    dispatcher = get_dispatcher()
    eff = main_effect()
    print sync_perform(dispatcher, eff)


if __name__ == '__main__':
    main()
