# python -m examples.github_example

# An example that shows
# - usage of HTTP effects
# - chaining effects with callbacks that return more effects
# - a custom effect that reads from the console


from __future__ import print_function

from functools import reduce, partial
from multiprocessing.pool import ThreadPool
import json
import operator

from effect import (
    ComposedDispatcher,
    Effect,
    TypeDispatcher,
    parallel,
    perform,
    perform_parallel_with_pool,
    ParallelEffects)

from .http_example import HTTPRequest
from .sync_http import perform_request_with_requests
from .readline_example import ReadLine, stdin_read_line


def get_orgs(name):
    """
    Fetch the organizations a user belongs to.

    :return: An Effect resulting in a list of strings naming the user's
    organizations.
    """
    req = Effect(
        HTTPRequest("get",
                    "https://api.github.com/users/{0}/orgs".format(name)))
    return req.on(success=lambda x: [org['login'] for org in json.loads(x)])


def get_org_repos(name):
    """
    Fetch the repos that belong to an organization.

    :return: An effect resulting in a list of strings naming the repositories.
    """
    req = Effect(
        HTTPRequest("get",
                    "https://api.github.com/orgs/{0}/repos".format(name)))
    return req.on(success=lambda x: [repo['name'] for repo in json.loads(x)])


def get_orgs_repos(name):
    """
    Fetch ALL of the repos that a user has access to, in any organization.
    """
    req = get_orgs(name)
    req = req.on(lambda org_names: parallel(map(get_org_repos, org_names)))
    req = req.on(lambda repo_lists: reduce(operator.add, repo_lists))
    return req


def main_effect():
    """
    Let the user enter a username, and then list all repos in all of that
    username's organizations.
    """
    return Effect(ReadLine("Enter GitHub Username> ")
    ).on(
        success=get_orgs_repos
    ).on(
        success=print, error=print)


def main(effect):
    my_pool = ThreadPool()
    pool_performer = partial(perform_parallel_with_pool, my_pool)
    dispatcher = ComposedDispatcher([
        TypeDispatcher({
            ReadLine: stdin_read_line,
            HTTPRequest: perform_request_with_requests,
            ParallelEffects: pool_performer,
        })
    ])
    perform(dispatcher, effect)


def twisted_main(reactor, effect):
    from effect.twisted import make_twisted_dispatcher, perform
    from .twisted_http import perform_request_with_treq
    dispatcher = ComposedDispatcher([
        TypeDispatcher({
            ReadLine: stdin_read_line,
            HTTPRequest: perform_request_with_treq,
        }),
        make_twisted_dispatcher(reactor),
    ])
    return perform(dispatcher, effect)

if __name__ == '__main__':
    import sys
    if '--twisted' in sys.argv:
        from twisted.internet.task import react
        react(lambda reactor: twisted_main(reactor, main_effect()), [])
    else:
        main(main_effect())
