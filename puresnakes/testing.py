"""
Testing helpers for effects.
"""

from effect import Callbacks

def succeed_stub(effect):
    """
    Invoke a Callbacks effect with the canned result already available in the
    StubRequest.
    """
    assert type(effect.request) is Callbacks, "{!r} is not a Callbacks!".format(effect.request)
    stub = effect.request.effect.request
    assert type(stub) is StubRequest, "{!r} is not a StubRequest!".format(stub)
    return effect.request.callback(stub.result)


class StubRequest(object):
    """An effect that returns a pre-specified result."""
    def __init__(self, result):
        self.result = result

    def perform_effect(self, handlers):
        return self.result
