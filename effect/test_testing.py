"""
Tests for the effect.testing module.
"""

import attr

import pytest

from testtools import TestCase
from testtools.matchers import (MatchesListwise, Equals, MatchesException,
                                raises)

from . import (
    ComposedDispatcher,
    Constant,
    Effect,
    base_dispatcher,
    parallel,
    sync_perform,
    sync_performer)
from .do import do, do_return
from .fold import FoldError, sequence
from .testing import (
    ESConstant,
    ESError,
    ESFunc,
    EQDispatcher,
    EQFDispatcher,
    SequenceDispatcher,
    fail_effect,
    parallel_sequence,
    perform_sequence,
    resolve_effect,
    resolve_stubs)


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
        eff = Effect(None).on(success=add1).on(success=add1)
        self.assertEqual(resolve_effect(eff, 0), 2)

    def test_callback_returning_effect(self):
        """
        When a callback returns an effect, that effect is returned.
        """
        stub_effect = Effect('inner')
        eff = Effect(None).on(success=lambda r: stub_effect)
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
        eff = Effect("orig").on(success=a).on(success=b)
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
            return nested_effect.on(success=nested_b)

        def nested_b(r):
            return ("nested-b-result", r)

        def c(r):
            return ("c-result", r)
        eff = Effect("orig").on(success=a).on(success=c)
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
                    .on(success=lambda r: 1 / 0)
                    .on(error=lambda exc: ('handled', exc)),
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
                    Effect('orig').on(
                        success=lambda r: _raise(ValueError('oh goodness'))),
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

    def test_skip_callbacks(self):
        """
        Intermediate callbacks of the wrong type are skipped.
        """
        eff = (Effect('foo')
               .on(error=lambda f: 1)
               .on(success=lambda x: ('succeeded', x)))
        self.assertEqual(resolve_effect(eff, 'foo'), ('succeeded', 'foo'))


class ResolveStubsTests(TestCase):
    """Tests for resolve_stubs."""

    def test_resolve_stubs(self):
        """
        resolve_stubs automatically performs intents that are wrapped in
        :class:`Stub`.
        """
        eff = ESConstant("foo").on(
            success=lambda r: ESError(RuntimeError("foo")).on(
                error=lambda e: ESFunc(lambda: "heyo")))
        self.assertEqual(resolve_stubs(base_dispatcher, eff), "heyo")

    def test_non_test_intent(self):
        """
        When a non-stub effect intent is found, the effect is returned.
        """
        bare_effect = Effect(object())
        eff = ESConstant("foo").on(success=lambda r: bare_effect)
        result_eff = resolve_stubs(base_dispatcher, eff)
        self.assertIs(result_eff.intent, bare_effect.intent)
        self.assertEqual(result_eff.callbacks, [])

    def test_type_error(self):
        """
        TypeErrors in callbacks (or otherwise performed intents) are propagated
        resolve_stubs.

        (This only exists because the initial implementation was done stupidly,
        and had to be fixed.)
        """
        eff = ESConstant("foo").on(success=lambda r: None["foo"])
        self.assertRaises(TypeError, resolve_stubs, base_dispatcher, eff)

    def test_resolve_stubs_callbacks_only_invoked_once(self):
        """
        Callbacks are run only once.

        This is a regression test for a really dumb bug.
        """
        eff = ESConstant("foo").on(success=lambda r: ("got it", r))
        self.assertEqual(resolve_stubs(base_dispatcher, eff),
                         ("got it", "foo"))

    def test_outer_callbacks_after_intermediate_effect(self):
        """
        When a callback returns an effect, and the outer effect has further
        callbacks, the remaining callbacks will be wrapped around the returned
        effect.
        """
        eff = ESConstant("foo").on(
            success=lambda r: Effect("something")
        ).on(
            lambda r: ("callbacked", r))
        result = resolve_stubs(base_dispatcher, eff)
        self.assertIs(type(result), Effect)
        self.assertEqual(result.intent, "something")
        result2 = resolve_effect(result, "bar")
        self.assertEqual(result2, ("callbacked", "bar"))

    def test_parallel_stubs(self):
        """Parallel effects are recursively resolved."""
        p_eff = parallel([ESConstant(1), ESConstant(2)])
        self.assertEqual(resolve_stubs(base_dispatcher, p_eff), [1, 2])

    def test_parallel_non_stubs(self):
        """
        If a parallel effect contains a non-stub, the parallel effect is
        returned as-is.
        """
        p_eff = parallel(
            [ESConstant(1), Effect(Constant(2))]
        ).on(lambda x: 0)
        self.assertEqual(resolve_stubs(base_dispatcher, p_eff), p_eff)

    def test_parallel_stubs_with_callbacks(self):
        """
        resolve_stubs runs callbacks of parallel effects.
        (bugfix test)
        """
        p_eff = parallel([ESConstant(1), ESConstant(2)]).on(lambda r: r[0])
        self.assertEqual(resolve_stubs(base_dispatcher, p_eff), 1)

    def test_parallel_stubs_with_callbacks_returning_effects(self):
        """
        resolve_stubs further processes effects that are returned from
        callbacks of parallel effects.
        """
        p_eff = parallel([ESConstant(1), ESConstant(2)]).on(
            lambda r: ESConstant(r[0] + 1))
        self.assertEqual(resolve_stubs(base_dispatcher, p_eff), 2)

    def test_parallel_stubs_with_element_callbacks_returning_non_stubs(self):
        """
        When an element of a parallel effect returns a non-stub effect, it will
        NOT be performed.
        """
        p_eff = parallel([ESConstant(1).on(lambda r: Effect(Constant(2)))])
        self.assertEqual(resolve_stubs(base_dispatcher, p_eff),
                         [Effect(Constant(2))])


def _raise(e):
    raise e


class EQDispatcherTests(TestCase):
    """Tests for :obj:`EQDispatcher`."""

    def test_no_intent(self):
        """When the dispatcher can't match the intent, it returns None."""
        d = EQDispatcher([])
        self.assertIs(d('foo'), None)

    def test_perform(self):
        """When an intent matches, performing it returns the canned result."""
        d = EQDispatcher([('hello', 'there')])
        self.assertEqual(sync_perform(d, Effect('hello')), 'there')


class EQFDispatcherTests(TestCase):
    """Tests for :obj:`EQFDispatcher`."""

    def test_no_intent(self):
        """When the dispatcher can't match the intent, it returns None."""
        d = EQFDispatcher([])
        self.assertIs(d('foo'), None)

    def test_perform(self):
        """When an intent matches, performing it returns the canned result."""
        d = EQFDispatcher([('hello', lambda i: (i, 'there'))])
        self.assertEqual(sync_perform(d, Effect('hello')), ('hello', 'there'))


class SequenceDispatcherTests(TestCase):
    """Tests for :obj:`SequenceDispatcher`."""

    def test_mismatch(self):
        """
        When an intent isn't expected, a None is returned.
        """
        d = SequenceDispatcher([('foo', lambda i: 1 / 0)])
        self.assertEqual(d('hello'), None)

    def test_success(self):
        """
        Each intent is performed in sequence with the provided functions, as
        long as the intents match.
        """
        d = SequenceDispatcher([
            ('foo', lambda i: ('performfoo', i)),
            ('bar', lambda i: ('performbar', i)),
        ])
        eff = Effect('foo').on(lambda r: Effect('bar').on(lambda r2: (r, r2)))
        self.assertEqual(
            sync_perform(d, eff),
            (('performfoo', 'foo'), ('performbar', 'bar')))

    def test_ran_out(self):
        """When there are no more items left, None is returned."""
        d = SequenceDispatcher([])
        self.assertEqual(d('foo'), None)

    def test_out_of_order(self):
        """Order of items in the sequence matters."""
        d = SequenceDispatcher([
            ('bar', lambda i: ('performbar', i)),
            ('foo', lambda i: ('performfoo', i)),
        ])
        self.assertEqual(d('foo'), None)

    def test_consumed(self):
        """`consumed` returns True if there are no more elements."""
        d = SequenceDispatcher([])
        self.assertTrue(d.consumed())

    def test_consumed_honors_changes(self):
        """
        `consumed` returns True if there are no more elements after performing
        some.
        """
        d = SequenceDispatcher([('foo', lambda i: 'bar')])
        sync_perform(d, Effect('foo'))
        self.assertTrue(d.consumed())

    def test_not_consumed(self):
        """
        `consumed` returns False if there are more elements.
        """
        d = SequenceDispatcher([('foo', lambda i: 'bar')])
        self.assertFalse(d.consumed())

    def test_consume_good(self):
        """``consume`` doesn't raise an error if all elements are consumed."""
        d = SequenceDispatcher([('foo', lambda i: 'bar')])
        with d.consume():
            sync_perform(d, Effect('foo'))

    def test_consume_raises(self):
        """``consume`` raises an error if not all elements are consumed."""
        d = SequenceDispatcher([('foo', None)])

        def failer():
            with d.consume():
                pass
        e = self.assertRaises(AssertionError, failer)
        self.assertEqual(str(e), "Not all intents were performed: ['foo']")


@attr.s
class MyIntent(object):
    val = attr.ib()


@attr.s
class OtherIntent(object):
    val = attr.ib()


def test_perform_sequence():
    """perform_sequence pretty much acts like SequenceDispatcher by default."""

    @do
    def code_under_test():
        r = yield Effect(MyIntent('a'))
        r2 = yield Effect(OtherIntent('b'))
        yield do_return((r, r2))

    seq = [(MyIntent('a'), lambda i: 'result1'),
           (OtherIntent('b'), lambda i: 'result2')]
    eff = code_under_test()
    assert perform_sequence(seq, eff) == ('result1', 'result2')


def test_perform_sequence_log():
    """
    When an intent isn't found, a useful log of intents is included in the
    exception message.
    """
    @do
    def code_under_test():
        r = yield Effect(MyIntent('a'))
        r2 = yield Effect(OtherIntent('b'))
        yield do_return((r, r2))

    seq = [(MyIntent('a'), lambda i: 'result1')]
    with pytest.raises(AssertionError) as exc:
        perform_sequence(seq, code_under_test())

    expected = ("sequence: MyIntent(val='a')\n"
                "NOT FOUND: OtherIntent(val='b')")
    assert expected in str(exc.value)


def test_parallel_sequence():
    """
    Ensures that all parallel effects are found in the given intents, in
    order, and returns the results associated with those intents.
    """
    seq = [
        parallel_sequence([
            [(1, lambda i: "one!")],
            [(2, lambda i: "two!")],
            [(3, lambda i: "three!")],
        ])
    ]
    p = parallel([Effect(1), Effect(2), Effect(3)])
    assert perform_sequence(seq, p) == ['one!', 'two!', 'three!']


def test_parallel_sequence_fallback():
    """
    Accepts a ``fallback`` dispatcher that will be used when the sequence
    doesn't contain an intent.
    """
    def dispatch_2(intent):
        if intent == 2:
            return sync_performer(lambda d, i: "two!")
    fallback = ComposedDispatcher([dispatch_2, base_dispatcher])
    seq = [
        parallel_sequence([
            [(1, lambda i: 'one!')],
            [],  # only implicit effects in this slot
            [(3, lambda i: 'three!')],
        ],
            fallback_dispatcher=fallback),
    ]
    p = parallel([Effect(1), Effect(2), Effect(3)])
    assert perform_sequence(seq, p) == ['one!', 'two!', 'three!']


def test_parallel_sequence_must_be_parallel():
    """
    If the sequences aren't run in parallel, the parallel_sequence won't
    match and a FoldError of NoPerformerFoundError will be raised.
    """
    seq = [
        parallel_sequence([
            [(1, lambda i: "one!")],
            [(2, lambda i: "two!")],
            [(3, lambda i: "three!")],
        ])
    ]
    p = sequence([Effect(1), Effect(2), Effect(3)])
    with pytest.raises(FoldError) as excinfo:
        perform_sequence(seq, p)
    assert excinfo.value.wrapped_exception[0] is AssertionError
