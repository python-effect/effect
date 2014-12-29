# python -m examples.github_example

# An example that shows
# - usage of HTTP effects
# - chaining effects with callbacks that return more effects
# - a custom effect that reads from the console
# - very simple Twisted-based usage

# Unfortunately python3 is not yet supported by this example since treq
# has not been ported.

from __future__ import print_function

import operator
import json
from functools import reduce

from effect import (
    ComposedDispatcher,
    Effect,
    TypeDispatcher,
    parallel)
from effect.twisted import perform, make_twisted_dispatcher
from .http_example import HTTPRequest, treq_http_request
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
    return Effect(ReadLine("Enter GitHub Username> ")).on(
        success=get_orgs_repos)


# Only the code below here depends on Twisted.
def main(reactor):
    dispatcher = ComposedDispatcher([
        TypeDispatcher({
            ReadLine: stdin_read_line,
            HTTPRequest: treq_http_request,
        }),
        make_twisted_dispatcher(reactor)
    ])
    return perform(dispatcher, main_effect()).addCallback(print)

if __name__ == '__main__':
    from twisted.internet.task import react
    react(main, [])
