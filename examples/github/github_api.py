"""
Functions for interacting with the GitHub API.

None of this code needs to change based on your I/O strategy -- you can
use blocking interfaces (e.g. the ``requests`` library) or Twisted, asyncio,
or Tornado implementations of an HTTP client with this code.
"""

import json
import operator

from effect import Effect, parallel
from .http_intent import HTTPRequest


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

    :return: An Effect resulting in a list of strings naming the repositories.
    """
    req = Effect(
        HTTPRequest("get",
                    "https://api.github.com/orgs/{0}/repos".format(name)))
    return req.on(success=lambda x: [repo['name'] for repo in json.loads(x)])


def get_orgs_repos(name):
    """
    Fetch ALL of the repos that a user has access to, in any organization.

    :return: An Effect resulting in a list of repositories.
    """
    req = get_orgs(name)
    req = req.on(lambda org_names: parallel(map(get_org_repos, org_names)))
    req = req.on(lambda repo_lists: reduce(operator.add, repo_lists))
    return req
