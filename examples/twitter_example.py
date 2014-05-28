import operator

from puresnakes.effect import Effect, parallel
from puresnakes.testing import succeed
from http_example import HTTPRequest


def get_followers(name):
    """
    Fetch Twitter followers.

    :return: a list of strings of twitter follower usernames.
    """
    req = Effect(HTTPRequest("get", "http://twitter.com/%s/followers" % name))
    return req.on_success(lambda x: [f['name'] for f in x])

def get_first_followers_followers(name):
    """
    A silly function that returns the followers of the first follower of the given user.

    This demonstrates how to chain effects.
    """
    req = get_followers(name)
    def got_init_followers(names):
        return get_followers(names[0])
    return req.on_success(got_init_followers)


class ReadLine(object):
    """An effect request for getting input from the user."""
    def perform_effect(self, handlers):
        return raw_input("Enter Input> ")


def main_effect():
    return Effect(ReadLine()).on_success(get_first_followers_followers)


if __name__ == '__main__':
    print(main_effect().perform({}))

