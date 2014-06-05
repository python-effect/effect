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

from six.moves import input

from effect import Effect, parallel, synchronous_performer
from effect.twisted import perform
from .http_example import HTTPRequest


def get_orgs(name):
    """
    Fetch the organizations a user belongs to.

    :return: An Effect resulting in a list of strings naming the user's
    organizations.
    """
    req = Effect(
        HTTPRequest("get",
                    "https://api.github.com/users/{0}/orgs".format(name)))
    return req.on_success(lambda x: [org['login'] for org in json.loads(x)])


def get_org_repos(name):
    """
    Fetch the repos that belong to an organization.

    :return: An effect resulting in a list of strings naming the repositories.
    """
    req = Effect(
        HTTPRequest("get",
                    "https://api.github.com/orgs/{0}/repos".format(name)))
    return req.on_success(lambda x: [repo['name'] for repo in json.loads(x)])


def get_orgs_repos(name):
    """
    Fetch ALL of the repos that a user has access to, in any organization.
    """
    req = get_orgs(name)
    req = req.on_success(
        lambda org_names:
            parallel(map(get_org_repos, org_names)))
    req = req.on_success(
        lambda repo_lists: reduce(operator.add, repo_lists))
    return req


def get_first_org_repos(name):
    """
    A silly function that fetches the repositories that belong to the
    first organization found that a user is in.

    This demonstrates how to chain effects.
    """
    req = get_orgs(name)
    return req.on_success(lambda orgs: get_org_repos(orgs[0]))


class ReadLine(object):
    """An effect intent for getting input from the user."""

    def __init__(self, prompt):
        self.prompt = prompt

    @synchronous_performer
    def perform_effect(self, dispatcher):
        return input(self.prompt)


def main_effect():
    return Effect(ReadLine("Enter GitHub Username> ")).on_success(
        get_first_org_repos)


def main_effect_2():
    return Effect(ReadLine("Enter GitHub Username> ")).on_success(
        get_orgs_repos)


# Only the code below here depends on Twisted.
def main(reactor):
    return perform(main_effect_2()).addCallback(print)

if __name__ == '__main__':
    from twisted.internet.task import react
    react(main, [])
