"""
Tests for the effect.testing module.
"""

from unittest import TestCase

from effect import Effect, Callbacks
from effect.testing import resolve_effect, StubRequest


class ResolveEffectTests(TestCase):

    def test_basic_resolution(self):
        """
        When no callbacks are attached to the effect, the result argument is
        returned directly.
        """
        eff = Effect(None)
        self.assertEqual(resolve_effect(eff, "blegh"), "blegh")

    def test_invoke_callbacks(self):
        """
        Callbacks of the effect are invoked successfully.
        """
        def add1(n): return n + 1
        eff = Effect(None).on_success(add1).on_success(add1)
        self.assertEqual(resolve_effect(eff, 0), 2)

    def test_callback_returning_effect(self):
        """
        When a callback returns an effect, that effect is returned.
        """
        stub_effect = Effect(None)
        eff = Effect(None).on_success(lambda r: stub_effect)
        self.assertIs(resolve_effect(eff, "foo"), stub_effect)

    def assert_callbacks(self, effect, callback, errback):
        self.assertIs(type(effect.request), Callbacks)
        self.assertIs(effect.request.callback, callback)
        self.assertIs(effect.request.errback, errback)

    def test_intermediate_callback_returning_effect(self):
        """
        When a callback returns an effect, and that callback has callbacks
        that come after it, the remaining callbacks will be wrapped around
        the returned effect.
        """
        nested_effect = Effect("nested")
        def a(r):
            return nested_effect
        def b(r):
            return "hello"
        eff = Effect("orig").on_success(a).on_success(b)
        result = resolve_effect(eff, "foo")
        self.assert_callbacks(result, b, None)
        self.assertIs(result.request.effect, nested_effect)

    def test_maintain_intermediate_effect_callbacks(self):
        """
        When a nested effect is returned from a callback, and that nested
        effect has callbacks itself, they are flattened along with the
        callbacks remaining on the outer effect.
        """
        nested_effect = Effect("nested")
        def a(r):
            return nested_effect.on_success(nested_b)
        def nested_b(r):
            return "nested-b result"
        def c(r):
            return "c-result"
        eff = Effect("orig").on_success(a).on_success(c)
        result = resolve_effect(eff, "foo")
        # result is nested_effect -> nested_b -> c
        self.assert_callbacks(result, c, None)
        self.assert_callbacks(result.request.effect, nested_b, None)
        self.assertIs(result.request.effect.request.effect,
                      nested_effect)
