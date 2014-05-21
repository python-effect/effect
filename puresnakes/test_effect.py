from __future__ import print_function

from testtools import TestCase
from testtools.matchers import MatchesListwise, Is, Equals, MatchesAny, MatchesException, raises

from .effect import Effect


class PureTests(TestCase):
    def test_perform_effect_method_dispatch(self):
        """Effect.perform invokes 'perform_effect' on the effect request."""
        self.assertEqual(
            Effect(SelfContainedRequest())
                .perform({}),
            "Self-result")

    def test_perform_effect_registry_dispatch(self):
        """Effect.perform invokes a function from the handler registry."""
        self.assertEqual(
            Effect(POPORequest())
                .perform({POPORequest: lambda e, h: "dispatched"}),
            "dispatched")

    def test_success(self):
        """
        Callbacks can wrap Effects, will be passed the Effect's result, and
        are able to return a new value.
        """
        self.assertEqual(
            Effect(SelfContainedRequest())
                .on_success(lambda x: x + ": amended!")
                .perform({}),
            "Self-result: amended!")

    def test_success_chain(self):
        """
        Callbacks can be wrapped in more callbacks.
        """
        self.assertEqual(
            Effect(SelfContainedRequest())
                .on_success(lambda x: x + ": amended!")
                .on_success(lambda x: x + " Again!")
                .perform({}),
            "Self-result: amended! Again!")

    def test_error(self):
        self.assertThat(
            Effect(ErrorRequest())
                .on_error(lambda x: ("handled", x))
                .perform({}),
            MatchesListwise([
                Equals('handled'),
                MatchesException(ValueError('oh dear'))]))

    def test_error_recovery(self):
        self.assertEqual(
            Effect(ErrorRequest())
                .on_error(lambda x: "handled")
                .on_success(lambda x: ("chained", x))
                .perform({}),
            ('chained', 'handled'))

    def test_error_bubbles_up(self):
        self.assertThat(
            lambda:
                Effect(ErrorRequest())
                    .on_error(lambda x: raise_(ValueError("eb error")))
                    .perform({}),
            raises(ValueError('eb error')))

    def test_error_error_recovery(self):
        self.assertThat(
            Effect(ErrorRequest())
                .on_error(lambda x: raise_(ValueError("eb error")))
                .on_error(lambda x: ("handled", x))
                .perform({}),
            MatchesListwise([
                Equals('handled'),
                MatchesException(ValueError('eb error'))]))

    def test_success_error_recovery(self):
        pass


def raise_(e):
    raise e


class SelfContainedRequest(object):
    """An example effect request which implements its own perform_effect."""

    def perform_effect(self, handlers):
        return "Self-result"


class POPORequest(object):
    """
    An example effect request which doesn't implement its own
    perform_effect.
    """


class ErrorRequest(object):
    def perform_effect(self, handlers):
        raise ValueError("oh dear")


# tests:
# - basic "after"
# - basic "on"
# - chain with error/after/on.
# - callbacks returning instances of effect
# - gather
# - Deferred support (I think this is broken but not sure).
