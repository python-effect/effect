from __future__ import print_function

from unittest import TestCase

from .effect import Effect


class PureTests(TestCase):
    def test_perform_effect_method_dispatch(self):
        """Effect.perform invokes 'perform_effect' on the effect request."""
        effect = Effect(SelfContainedEffect())
        self.assertEqual(effect.perform({}), "Self-result")

    def test_perform_effect_registry_dispatch(self):
        """Effect.perform invokes a function from the handler registry."""
        def handle_effect(effect, handlers):
            return "dispatched"
        effect = Effect(POPORequest())
        self.assertEqual(
            effect.perform({POPORequest: handle_effect}),
            "dispatched")

    def test_callback(self):
        """
        Callbacks can wrap Effects, will be passed the Effect's result, and
        are able to return a new value.
        """
        effect = Effect(SelfContainedEffect())
        effect = effect.on_success(lambda x: x + ": amended!")
        self.assertEqual(
            effect.perform({}),
            "Self-result: amended!")

    def test_callback_chain(self):
        """
        Callbacks can be wrapped in more callbacks.
        """
        effect = Effect(SelfContainedEffect())
        effect = effect.on_success(lambda x: x + ": amended!")
        effect = effect.on_success(lambda x: x + " Again!")
        self.assertEqual(
            effect.perform({}),
            "Self-result: amended! Again!")


class SelfContainedEffect(object):
    """An example effect request which implements its own perform_effect."""

    def perform_effect(self, handlers):
        return "Self-result"


class POPORequest(object):
    """
    An example effect request which doesn't implement its own
    perform_effect.
    """




# tests:
# - basic "after"
# - basic "on"
# - chain with error/after/on.
# - callbacks returning instances of effect
# - gather
# - Deferred support (I think this is broken but not sure).
