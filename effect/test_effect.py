from __future__ import print_function

from testtools import TestCase
from testtools.matchers import (MatchesListwise, Is, Equals, MatchesException,
                                raises, MatchesPredicateWithParams)

from twisted.internet.defer import Deferred, succeed
from twisted.trial.unittest import SynchronousTestCase

from . import Effect, NoEffectHandlerError, parallel
from .testing import StubIntent


class SelfContainedIntent(object):
    """An example effect intent which implements its own perform_effect."""

    def perform_effect(self, handlers):
        return "Self-result", handlers


class POPOIntent(object):
    """
    An example effect intent which doesn't implement its own
    perform_effect.
    """


class ErrorIntent(object):
    def perform_effect(self, handlers):
        raise ValueError("oh dear")


class EffectPerformTests(TestCase):
    """Tests for Effect.perform."""
# - after and on, but these are "obviously correct"
    def test_perform_effect_method_dispatch(self):
        """
        Effect.perform
        - invokes 'perform_effect' on the effect intent,
        - passes the handler table to it
        - returns its result
        """
        table = {}
        self.assertThat(
            Effect(SelfContainedIntent())
                .perform(table),
            MatchesListwise([
                Equals("Self-result"),
                Is(table)]))

    def test_perform_effect_registry_dispatch(self):
        """Effect.perform
        - invokes a function from the handler registry,
        - passes the effect intent and the handler table to it
        - returns its result
        """
        table = {POPOIntent: lambda e, h: (e, h, "dispatched")}
        intent = POPOIntent()
        self.assertThat(
            Effect(intent).perform(table),
            MatchesListwise([
                Is(intent),
                Is(table),
                Equals("dispatched")]))

    def test_error_bubbles_up(self):
        """
        When perform_effect raises an exception, it is raised up through
        Effect.perform.
        """
        self.assertThat(
            lambda: Effect(ErrorIntent()).perform({}),
            raises(ValueError('oh dear')))

    def test_no_effect_handler(self):
        """
        When no effect handler can be found for an effect intent,
        :class:`NoEffectHandlerError` is raised.
        """
        intent = object()
        self.assertThat(
            lambda: Effect(intent).perform({}),
            raises(NoEffectHandlerError(intent)))

    def test_effects_returning_effects(self):
        """
        When the effect handler returns another effect,
        - that effect is immediately performed with the same handler table,
        - the result of that is returned.
        """
        self.assertEqual(
            Effect(StubIntent(Effect(StubIntent("foo"))))
                .perform({}),
            "foo")

    def test_effects_returning_effects_returning_effects(self):
        """
        If an effect returns an effect which immediately returns an effect
        with no callbacks in between, the result of the innermost effect is
        returned from the outermost effect's perform.
        """
        self.assertEqual(
            Effect(StubIntent(Effect(StubIntent(Effect(StubIntent("foo"))))))
                .perform({}),
            "foo")


class CallbackTests(TestCase):
    """Tests for callbacks."""

    def test_success(self):
        """
        An Effect with callbacks
        - performs the wrapped intent, passing the handlers,
        - passes the result of that to the callback,
        - returns the result of the callback.
        """
        table = {}
        self.assertThat(
            Effect(SelfContainedIntent())
                .on_success(lambda x: (x, "amended!"))
                .perform(table),
            MatchesListwise([
                MatchesListwise([
                    Equals("Self-result"),
                    Is(table)]),
                    Equals("amended!")]))

    def test_success_propagates_effect_exception(self):
        """
        An Effect with callbacks propagates exceptions from performing
        the inner effect when there is no errback.
        """
        self.assertThat(
            lambda:
                Effect(ErrorIntent())
                    .on_success(lambda x: 'nope')
                    .perform({}),
            raises(ValueError('oh dear')))

    def test_error_success(self):
        """
        An Effect with callbacks
        - performs the wrapped effect, passing the handlers,
        - returns the result (assuming there is no exception).

        In other words, the error handler is skipped when there's no error.
        """
        table = {}
        self.assertThat(
            Effect(SelfContainedIntent())
                .on_error(lambda x: (x, "recovered!"))
                .perform(table),
            MatchesListwise([
                Equals("Self-result"),
                Is(table)]))

    def test_error(self):
        """
        An Effect with callbacks
        - performs the wrapped effect,
        - in the case of an exception, invokes the errback with exc_info,
        - returns the result of the errback.
        """
        self.assertThat(
            Effect(ErrorIntent())
                .on_error(lambda x: ("handled", x))
                .perform({}),
            MatchesListwise([
                Equals('handled'),
                MatchesException(ValueError('oh dear'))]))

    def test_error_propagates_callback_exceptions(self):
        """
        An Effect with callbacks does _not_ catch errors from effect
        implementations.
        """
        self.assertThat(
            lambda:
                Effect(ErrorIntent())
                    .on_error(lambda x: raise_(ValueError('eb error')))
                    .perform({}),
            raises(ValueError('eb error')))

    def test_nested_effect_exception_passes_to_outer_error_handler(self):
        """
        If an inner effect raises an exception, it bubbles up and the
        exc_info is passed to the outer effect's error handlers.
        """
        self.assertThat(
            Effect(StubIntent(Effect(ErrorIntent())))
                .on_error(lambda x: x)
                .perform({}),
            MatchesException(ValueError('oh dear')))


class DeferredSupportTests(TestCase):
    def test_asynchronous_callback(self):
        """
        When a callback is wrapped around an effect that results in a Deferred,
        - the callback is attached to that Deferred, instead of being invoked
          synchronously,
        - such that the callback will receive the Deferred's ultimate result,
        - and the Deferred will be returned from perform_effect.
        """
        d = Deferred()
        calls = []
        self.assertIs(
            Effect(StubIntent(d))
                .on_success(calls.append)
                .perform({}),
            d)
        self.assertEqual(calls, [])
        d.callback("stuff")
        self.assertEqual(calls, ["stuff"])

    def test_asynchronous_errback(self):
        """
        When an errback is wrapped around an effect that results in a Deferred,
        - the errback is attached to that Deferred, instead of being invoked
          synchronously,
        - such that the errback will receive the Deferred's ultimate Failure,
        - and the Deferred will be returned from perform_effect.
        """
        d = Deferred()
        calls = []
        self.assertIs(
            Effect(StubIntent(d))
                .on_error(calls.append)
                .perform({}),
            d)
        self.assertEqual(calls, [])
        d.errback(ValueError("stuff"))
        self.assertThat(
            calls,
            MatchesListwise([
                MatchesBasicFailure(ValueError("stuff"))]))


class DeferredPerformTests(SynchronousTestCase):

    def test_perform_deferred_result(self):
        """
        An effect which results in a Deferred will have that Deferred returned
        from its perform method.
        """
        result = Effect(StubIntent(succeed("hello"))).perform({})
        self.assertEqual(self.successResultOf(result), 'hello')

    def test_perform_deferred_chaining(self):
        """
        When the top-level effect returns a Deferred that fires with an
        Effect, Effect.perform will perform that effect.
        """
        result = Effect(
            StubIntent(
                succeed(
                    Effect(
                        StubIntent('foo'))))).perform({})
        self.assertEqual(self.successResultOf(result), 'foo')

    def test_deferred_callback_effect(self):
        """
        If a callback on a Deferred-wrapped Effect returns an Effect, that
        effect's result becomes the outer effect's result.
        """
        d = succeed('deferred-result')
        nested_effect = Effect(StubIntent('nested-effect-result'))
        eff = Effect(StubIntent(d)).on_success(lambda x: nested_effect)
        self.assertEqual(self.successResultOf(eff.perform({})),
                         'nested-effect-result')

    def test_intermediate_deferred_callback_returning_effect(self):
        """
        If a callback on a Deferred-wrapped Effect returns an Effect, that
        effect's result becomes the outer effect's result.
        """
        d = succeed('deferred-result')
        nested_effect = Effect(StubIntent('nested-effect-result'))
        eff = (Effect(StubIntent(d))
                   .on_success(lambda x: nested_effect)
                   .on_success(lambda x: (x, 'finally')))
        self.assertEqual(self.successResultOf(eff.perform({})),
                         ('nested-effect-result', 'finally'))


class ParallelTests(SynchronousTestCase):
    """Tests for :func:`parallel`."""
    def test_parallel(self):
        """
        parallel results in a list of results of effects, in the same
        order that they were passed to parallel.
        """
        d = parallel([Effect(StubIntent('a')),
                      Effect(StubIntent('b'))]).perform({})
        self.assertEqual(self.successResultOf(d), ['a', 'b'])

    # - handlers is passed through to child effects
    # - what happens with errors?


def _failure_matches_exception(a, b):
    return type(a.value) is type(b) and a.value.args == b.args


MatchesBasicFailure = MatchesPredicateWithParams(
    _failure_matches_exception,
    "{0} is not an exception similar to {1}.")


def raise_(e):
    raise e
