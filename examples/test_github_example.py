# Run these tests with "trial example.test_github_example"

import json

from testtools import TestCase

from effect import Effect
from effect.testing import StubRequest, succeed_stub
import github_example


class GithubTests(TestCase):
    def test_get_orgs_request(self):
        """
        get_orgs returns an effect that makes an HTTP request to
        the GitHub API to look up organizations for a user.
        """
        eff = github_example.get_orgs('radix')
        http = eff.request.effect.request
        self.assertEqual(http.method, 'get')
        self.assertEqual(http.url, 'https://api.github.com/users/radix/orgs')

    def test_get_orgs_success(self):
        """get_orgs extracts the result into a simple list of orgs."""
        eff = github_example.get_orgs('radix')
        callbacks = eff.request
        self.assertEqual(
            callbacks.callback(json.dumps([{'login': 'twisted'},
                                           {'login': 'rackerlabs'}])),
            ['twisted', 'rackerlabs'])

    def test_get_org_repos_request(self):
        """
        get_org_repos returns an effect that makes an HTTP request to
        the GitHub API to look up repos in an org.
        """
        eff = github_example.get_org_repos('twisted')
        http = eff.request.effect.request
        self.assertEqual(http.method, 'get')
        self.assertEqual(http.url, 'https://api.github.com/orgs/twisted/repos')

    def test_get_org_repos_success(self):
        """get_org_repos extracts the result into a simple list of repos."""
        eff = github_example.get_org_repos('radix')
        callbacks = eff.request
        self.assertEqual(
            callbacks.callback(json.dumps([{'name': 'twisted'},
                                           {'name': 'txstuff'}])),
            ['twisted', 'txstuff'])

    def test_get_first_org_repos(self):
        """
        get_first_org_repos returns an Effect returned by looking up the
        repositories of the first organization of the specified user.
        """
        # A very primitive mocking is actually Not Evil (I know, it's hard to
        # believe) when you're just mocking out pure functions.
        # - order/timing dependence is not an issue
        # - behavior based on non-argument state is not an issue
        # - repeated calls are not an issue
        # so don't freak out, patching is ok :)
        get_orgs = {'radix': Effect(StubRequest(['twisted', 'rackerlabs']))}
        get_org_repos = {'twisted': Effect(StubRequest(['twisted',
                                                        'txstuff']))}
        self.patch(github_example, 'get_orgs', get_orgs.get)
        self.patch(github_example, 'get_org_repos', get_org_repos.get)
        eff = github_example.get_first_org_repos('radix')
        self.assertIs(succeed_stub(eff), get_org_repos['twisted'])

    # These tests don't have 100% coverage, but they should teach you
    # everything you need to know to extend to testing any type of effect.
