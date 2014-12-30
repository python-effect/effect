# Run these tests with "trial examples.test_github_example"
# or "python -m testtools.run examples.test_github_example"

import json

from testtools import TestCase

from effect import Effect, ParallelEffects, Constant
from effect.testing import resolve_effect
from . import github_example


class GithubTests(TestCase):
    def test_get_orgs_request(self):
        """
        get_orgs returns an effect that makes an HTTP request to
        the GitHub API to look up organizations for a user.
        """
        eff = github_example.get_orgs('radix')
        http = eff.intent
        self.assertEqual(http.method, 'get')
        self.assertEqual(http.url, 'https://api.github.com/users/radix/orgs')

    def test_get_orgs_success(self):
        """get_orgs extracts the result into a simple list of orgs."""
        eff = github_example.get_orgs('radix')
        self.assertEqual(
            resolve_effect(eff, json.dumps([{'login': 'twisted'},
                                            {'login': 'rackerlabs'}])),
            ['twisted', 'rackerlabs'])

    def test_get_org_repos_request(self):
        """
        get_org_repos returns an effect that makes an HTTP request to
        the GitHub API to look up repos in an org.
        """
        eff = github_example.get_org_repos('twisted')
        http = eff.intent
        self.assertEqual(http.method, 'get')
        self.assertEqual(http.url, 'https://api.github.com/orgs/twisted/repos')

    def test_get_org_repos_success(self):
        """get_org_repos extracts the result into a simple list of repos."""
        eff = github_example.get_org_repos('radix')
        self.assertEqual(
            resolve_effect(eff, json.dumps([{'name': 'twisted'},
                                            {'name': 'txstuff'}])),
            ['twisted', 'txstuff'])

    def test_get_orgs_repos(self):
        """
        get_orgs_repos returns an Effect which looks up the organizations for
        a user, and then looks up all of the repositories of those orgs in
        parallel, and returns a single flat list of all repos.
        """
        effect = github_example.get_orgs_repos('radix')
        self.assertEqual(effect.intent.method, 'get')
        self.assertEqual(effect.intent.url,
                         'https://api.github.com/users/radix/orgs')
        next_effect = resolve_effect(
            effect,
            json.dumps([{'login': 'twisted'}, {'login': 'rackerlabs'}]))
        self.assertIsInstance(next_effect.intent, ParallelEffects)
        # Get each parallel effect
        effects = next_effect.intent.effects
        self.assertEqual(effects[0].intent.method, 'get')
        self.assertEqual(effects[0].intent.url,
                         'https://api.github.com/orgs/twisted/repos')
        self.assertEqual(effects[1].intent.method, 'get')
        self.assertEqual(effects[1].intent.url,
                         'https://api.github.com/orgs/rackerlabs/repos')
        self.assertEqual(resolve_effect(next_effect, [['twisted', 'txstuff'],
                                                      ['otter', 'nova']]),
                         ['twisted', 'txstuff', 'otter', 'nova'])

    # These tests don't have 100% coverage, but they should teach you
    # everything you need to know to extend to testing any type of effect.
