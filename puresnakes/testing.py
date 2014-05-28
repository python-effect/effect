"""
Testing helpers for effects.
"""

def succeed(effect, result):
    """
    Cause an effect's outermost callback to succeed with the given value.
    """
    return effect.effect_request.callback(result)


class StubRequest(object):
    """An effect that returns a pre-specified result."""
    def __init__(self, result):
        self.result = result

    def perform_effect(self, handlers):
        return self.result
