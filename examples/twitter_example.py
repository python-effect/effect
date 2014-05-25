from puresnakes.effect import Effect, parallel
from puresnakes.testing import succeed
from http_example import HTTPRequest


def get_followers(name):
    req = Effect(HTTPRequest("get", "http://twitter.com/%s/followers" % name))
    return req.on_success(lambda x: [f['name'] for f in x])

def get_followers_followers(name):
    req = get_followers(name)
    def got_init_followers(names):
        reqs = [get_followers(name) for name in names]
        return parallel(reqs).on_success(lambda x: reduce(operator.add, x))
    return req.on_success(got_init_followers)


class ReadLine(object):
    """An effect request for getting input from the user."""
    def perform_effect(self, handlers):
        return raw_input("Enter Input> ")

def main():
    return Effect(ReadLine()).on_success(get_followers_followers)


## An example of how to test this code
from unittest import TestCase

class TwitterTests(TestCase):
    def test_get_followers_request(self):
        """
        The first thing get_followers does is make a request to the Twitter API.
        """
        req = get_followers('radix')
        http = req.effect_request.effect.effect_request
        self.assertEqual(http.method, 'get')
        self.assertEqual(http.url, 'http://twitter.com/radix/followers')

    def test_get_followers_success(self):
        """get_followers extracts the result into a simple list of names."""
        req = get_followers('radix')
        callbacks = req.effect_request
        self.assertEqual(
            callbacks.callback([{'name': 'bob'}, {'name': 'jane'}]),
            ['bob', 'jane'])

    def test_get_followers_followers_request(self):
        """
        The first thing get_followers_followers does is make a request
        for the passed user's followers.
        """
        req = get_followers_followers('radix')
        http = req.effect_request.effect.effect_request.effect.effect_request
        self.assertEqual(http.method, 'get')
        self.assertEqual(http.url, 'http://twitter.com/radix/followers')

    def test_get_followers_followers_inner_requests(self):
        """
        When the list of initial followers arrives, the rest of the followers
        are looked up in parallel.
        """
        req = get_followers_followers('radix')
#         from pprint import pprint
#         pprint(req.serialize())
        callbacks = req.effect_request
        parallel = callbacks.callback(['bob', 'jane'])
#         pprint(parallel.serialize())

    def test_main(self):
        # I'll be happy if I can write a test that does the following:
        # - resolves a data dependency for getting input from the user
        # - resolves a data dependency for getting the list of followers for the named user
        #   WITHOUT caring about how that data is actually retrieved (that is, it should be
        #   okay to refactor the function to look up data from memcached instead of http, and
        #   the unit test should still pass)
        # - resolves data dependencies for getting followers of each follower, with the same constraints.
        from pprint import pprint
        effect = main()
        self.assertIsInstance(effect.effect_request.effect.effect_request, ReadLine)
        next_effect = succeed(effect, "radix")
        # XXX how do I make sure that this effect is looking up the followers of _radix_, without actually asserting stuff about the HTTP request it makes?
        next_effect = succeed(next_effect, ["bob", "cindy"])
        pprint(next_effect)
#         pprint(effect.serialize())


# [request, Callbacks, Callbacks]
# [parallel(request, request), Callbacks, Callbacks]


#     def test_pipes_style_get_followers_followers(self):
#         effect = get_followers_followers('radix')
#         channel = get_channel_for_effect(effect)
#         top_http_req = channel.get_next_primitive()
#         channel.send_result([{'name': 'bob'}, {'name': 'jane'}])
#         http_reqs = channel.get_next_primitive()
#         self.assertEqual(len(http_reqs), 2)
#         self.assertEqual(http_reqs[0].url, 'http://twitter.com/bob/followers')
#         self.assertEqual(http_reqs[1].url, 'http://twitter.com/jane/followers')
#         channel.send_result([{'name': 'cindy'}, {'name': 'manish'}])
#         channel.send_result([{'name': 'sakura'}, {'name': 'radix'}])
#         self.assertEqual(
#             channel.get_result(),
#             ['cindy', 'manish', 'sakura', 'radix'])


