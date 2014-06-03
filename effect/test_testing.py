"""
Tests for the effect.testing module.
"""

from testtools import TestCase
from testtools.matchers import (MatchesListwise, Equals, MatchesException,
                                raises)

from . import Effect
from .testing import resolve_effect, fail_effect


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

    def test_resolve_effect_cb_exception(self):
        """
        When a callback raises an exception, the next error handler is called
        with the exception info.
        """
        self.assertThat(
            resolve_effect(
                Effect("orig")
                    .on_success(lambda r: 1 / 0)
                    .on_error(lambda exc: ('handled', exc)),
                'result'),
            MatchesListwise([
                Equals('handled'),
                MatchesException(ZeroDivisionError)]))

    def test_raise_if_final_result_is_error(self):
        """
        If the last callback raises an error, that error is raised from
        resolve_effect.
        """
        self.assertThat(
            lambda:
                resolve_effect(
                    Effect('orig')
                        .on_success(
                            lambda r: _raise(ValueError('oh goodness'))),
                    'result'),
            raises(ValueError('oh goodness')))

    def test_fail_effect(self):
        """
        fail_effect allows failing an effect directly, so its first error
        handler is invoked.
        """
        self.assertThat(
            lambda:
                fail_effect(
                    Effect('orig'),
                    ValueError('oh deary me')),
            raises(ValueError('oh deary me')))


def _raise(e):
    raise e
