"""
Tests for the effect.testing module.
"""

from unittest import TestCase

from effect import Effect
from effect.testing import resolve_effect


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
        Callbacks of the effect are invoked to calculate the final result.
        """

        def add1(n):
            return n + 1
        eff = Effect(None).on_success(add1).on_success(add1)
        self.assertEqual(resolve_effect(eff, 0), 2)

    def test_callback_returning_effect(self):
        """
        When a callback returns an effect, that effect is returned.
        """
        stub_effect = Effect('inner')
        eff = Effect(None).on_success(lambda r: stub_effect)
        result = resolve_effect(eff, 'foo')
        self.assertEqual(result.intent, 'inner')
        self.assertEqual(resolve_effect(result, 'next-result'),
                         'next-result')

    def test_intermediate_callback_returning_effect(self):
        """
        When a callback returns an effect, and that outer callback has
        callbacks that come after it, the remaining callbacks will be wrapped
        around the returned effect.
        """
        nested_effect = Effect("nested")

        def a(r):
            return nested_effect

        def b(r):
            return ("b-result", r)
        eff = Effect("orig").on_success(a).on_success(b)
        result = resolve_effect(eff, "foo")
        self.assertEqual(
            resolve_effect(result, "next-result"),
            ('b-result', 'next-result'))

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
            return ("nested-b-result", r)

        def c(r):
            return ("c-result", r)
        eff = Effect("orig").on_success(a).on_success(c)
        result = resolve_effect(eff, "foo")
        self.assertEqual(resolve_effect(result, 'next-result'),
                         ('c-result', ('nested-b-result', 'next-result')))
