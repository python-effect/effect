"""
Testing helpers for effects.
"""

def succeed(effect, result):
    """
    Cause an effect's outermost callback to succeed with the given value.
    """
    return effect.effect_request.callback(result)