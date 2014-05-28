from __future__ import print_function

from testtools import TestCase
from testtools.matchers import (MatchesListwise, Is, Equals, MatchesException,
                                raises, MatchesPredicateWithParams)

from twisted.internet.defer import Deferred, succeed
from twisted.trial.unittest import SynchronousTestCase

from . import Effect, NoEffectHandlerError, parallel
from .testing import StubRequest


## Fun testing objects
class SelfContainedRequest(object):
    """An example effect request which implements its own perform_effect."""

    def perform_effect(self, handlers):
        return "Self-result", handlers


class POPORequest(object):
    """
    An example effect request which doesn't implement its own
    perform_effect.
    """


class ErrorRequest(object):
    def perform_effect(self, handlers):
        raise ValueError("oh dear")


## The test cases

class EffectPerformTests(TestCase):
    """Tests for Effect.perform."""
# - after and on, but these are "obviously correct"
    def test_perform_effect_method_dispatch(self):
        """
        Effect.perform
        - invokes 'perform_effect' on the effect request,
        - passes the handler table to it
        - returns its result
        """
        table = {}
        self.assertThat(
            Effect(SelfContainedRequest())
                .perform(table),
            MatchesListwise([
                Equals("Self-result"),
                Is(table)]))

    def test_perform_effect_registry_dispatch(self):
        """Effect.perform
        - invokes a function from the handler registry,
        - passes the effect request and the handler table to it
        - returns its result
        """
        table = {POPORequest: lambda e, h: (e, h, "dispatched")}
        request = POPORequest()
        self.assertThat(
            Effect(request).perform(table),
            MatchesListwise([
                Is(request),
                Is(table),
                Equals("dispatched")]))

    def test_error_bubbles_up(self):
        """
        When perform_effect raises an exception, it is raised up through
        Effect.perform.
        """
        self.assertThat(
            lambda: Effect(ErrorRequest()).perform({}),
            raises(ValueError('oh dear')))

    def test_no_effect_handler(self):
        """
        When no effect handler can be found for an effect request,
        :class:`NoEffectHandlerError` is raised.
        """
        request = object()
        self.assertThat(
            lambda: Effect(request).perform({}),
            raises(NoEffectHandlerError(request)))

    def test_effects_returning_effects(self):
        """
        When the effect handler returns another effect,
        - that effect is immediately performed with the same handler table,
        - the result of that is returned.
        """
        table = {POPORequest: lambda r, h: Effect(SelfContainedRequest())}
        self.assertEqual(
            Effect(POPORequest())
                .perform(table),
            ("Self-result", table))


class CallbackTests(TestCase):
    """Tests for callbacks."""

    def test_success(self):
        """
        Callbacks.perform_effect
        - performs the wrapped effect, passing the handlers,
        - passes the result of that to the callback,
        - returns the result of the callback.
        """
        table = {}
        self.assertThat(
            Effect(SelfContainedRequest())
                .on_success(lambda x: (x, "amended!"))
                .perform(table),
            MatchesListwise([
                MatchesListwise([
                    Equals("Self-result"),
                    Is(table)]),
            Equals("amended!")]))

    def test_success_propagates_effect_exception(self):
        """
        Callbacks.perform_effect propagates exceptions from performing
        the inner effect when there is no errback.
        """
        self.assertThat(
            lambda:
                Effect(ErrorRequest())
                    .on_success(lambda x: 'nope')
                    .perform({}),
            raises(ValueError('oh dear')))

    def test_error_success(self):
        """
        Callbacks.perform_effect
        - performs the wrapped effect, passing the handlers,
        - returns the result (assuming there is no exception).
        """
        table = {}
        self.assertThat(
            Effect(SelfContainedRequest())
                .on_error(lambda x: (x, "recovered!"))
                .perform(table),
            MatchesListwise([
                Equals("Self-result"),
                Is(table)]))

    def test_error(self):
        """
        Callbacks.perform_effect
        - performs the wrapped effect,
        - in the case of an exception, invokes the errback with exc_info,
        - returns the result of the errback.
        """
        self.assertThat(
            Effect(ErrorRequest())
                .on_error(lambda x: ("handled", x))
                .perform({}),
            MatchesListwise([
                Equals('handled'),
                MatchesException(ValueError('oh dear'))]))

    def test_error_propagates_callback_exceptions(self):
        """
        Callbacks.perform_effect does _not_ catch errors from callbacks.
        """
        self.assertThat(
            lambda:
                Effect(ErrorRequest())
                    .on_error(lambda x: raise_(ValueError('eb error')))
                    .perform({}),
            raises(ValueError('eb error')))


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
            Effect(StubRequest(d))
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
            Effect(StubRequest(d))
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
    def test_perform_deferred_chaining(self):
        """
        When the top-level callback returns a Deferred that fires with an
        Effect, Effect.perform will perform that effect.
        """
        d = succeed(Effect(StubRequest('foo')))
        result = Effect(StubRequest(d)).perform({})
        self.assertEqual(self.successResultOf(result), 'foo')


class ParallelTests(SynchronousTestCase):
    """Tests for :func:`parallel`."""
    def test_parallel(self):
        """
        parallel results in a list of results of effects, in the same
        order that they were passed to parallel.
        """
        d = parallel([Effect(StubRequest('a')),
                      Effect(StubRequest('b'))]).perform({})
        self.assertEqual(self.successResultOf(d), ['a', 'b'])

    # - handlers is passed through to child effects
    # - what happens with errors?

## Boring test utilities

def _failure_matches_exception(a, b):
    return type(a.value) is type(b) and a.value.args == b.args


MatchesBasicFailure = MatchesPredicateWithParams(
    _failure_matches_exception,
    "{0} is not an exception similar to {1}.")


def raise_(e):
    raise e
