# Run these tests with "trial example.test_twitter_example"

from testtools import TestCase

from puresnakes.effect import Effect
from puresnakes.testing import StubRequest, succeed
import twitter_example


class TwitterTests(TestCase):
    def test_get_followers_request(self):
        """
        The first thing get_followers does is make a request to the Twitter
        API.
        """
        req = twitter_example.get_followers('radix')
        http = req.effect_request.effect.effect_request
        self.assertEqual(http.method, 'get')
        self.assertEqual(http.url, 'http://twitter.com/radix/followers')

    def test_get_followers_success(self):
        """get_followers extracts the result into a simple list of names."""
        req = twitter_example.get_followers('radix')
        callbacks = req.effect_request
        self.assertEqual(
            callbacks.callback([{'name': 'bob'}, {'name': 'jane'}]),
            ['bob', 'jane'])

    def test_get_followers_followers(self):
        """
        The first thing get_followers_followers does is make a request
        for the passed user's followers.
        """
        # A very primitive mocking is actually Not Evil (I know, it's hard to
        # believe) when you're just mocking out pure functions.
        # - order/timing dependence is not an issue
        # - behavior based on non-argument state is not an issue
        # - repeated calls are not an issue
        # so don't freak out, patching is ok :)
        mocks = {'radix': Effect(StubRequest(['sally', 'raph'])),
                 'sally': Effect(StubRequest(['tim', 'bob']))}
        self.patch(twitter_example, 'get_followers', mocks.get)
        req = twitter_example.get_first_followers_followers('radix')
        self.assertEqual(req.perform({}), ['tim', 'bob'])

    def test_main(self):
        effect = twitter_example.main_effect()
        self.assertIsInstance(effect.effect_request.effect.effect_request,
                              twitter_example.ReadLine)
        next_effect = succeed(effect, "radix")
        next_effect = succeed(next_effect, ["bob", "cindy"])
