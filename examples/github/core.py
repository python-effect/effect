"""
Core application / API interaction logic of the GitHub example.

None of this code needs to change based on your I/O strategy -- you can
use blocking API (e.g. the ``requests`` library) or Twisted, asyncio,
or Tornado implementations of an HTTP client with this code, by providing
different performers for the :obj:`HTTPRequest` intent.
"""

from __future__ import print_function

from functools import reduce
import json
import operator

from effect import Effect, parallel

from ..readline_intent import ReadLine
from ..http.http_intent import HTTPRequest


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


def main_effect():
    """
    Request a username from the keyboard, and look up all repos in all of
    that user's organizations.

    :return: an Effect resulting in a list of repositories.
    """
    intent = ReadLine("Enter Github Username> ")
    read_eff = Effect(intent)
    org_repos_eff = read_eff.on(success=get_orgs_repos)
    return org_repos_eff
