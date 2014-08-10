from __future__ import print_function, absolute_import

from testtools import TestCase
from testtools.matchers import (MatchesListwise, Is, Equals, MatchesException,
                                raises)

from . import (Effect, NoEffectHandlerError, perform,
               default_dispatcher, sync_perform, NotSynchronousError,
               ConstantIntent)


class SelfContainedIntent(object):
    """An example effect intent which implements its own perform_effect."""

    def perform_effect(self, dispatcher):
        return ("Self-result", dispatcher)


class POPOIntent(object):
    """
    An example effect intent which doesn't implement its own
    perform_effect.
    """


class ErrorIntent(object):

    def perform_effect(self, dispatcher):
        raise ValueError("oh dear")


class EffectPerformTests(TestCase):
    """Tests for perform."""

    def test_perform_effect_method_dispatch(self):
        """
        perform
        - invokes 'perform_effect' on the effect intent,
        - passes the default dispatcher to it
        - returns its result
        """
        self.assertThat(
            sync_perform(Effect(SelfContainedIntent())),
            MatchesListwise([
                Equals("Self-result"),
                Is(default_dispatcher)]))

    def test_perform_effect_function_dispatch(self):
        """
        perform
        - invokes the passed in dispatcher
        - passes the effect intent to it
        - returns its result
        """
        dispatcher = lambda i, box: box.succeed((i, 'dispatched'))
        intent = POPOIntent()
        self.assertThat(
            sync_perform(Effect(intent), dispatcher),
            MatchesListwise([
                Is(intent),
                Equals("dispatched")]))

    def test_error_bubbles_up(self):
        """
        When perform_effect raises an exception, it is raised up through
        sync_perform.
        """
        self.assertThat(
            lambda: sync_perform(Effect(ErrorIntent())),
            raises(ValueError('oh dear')))

    def test_no_effect_handler(self):
        """
        When no perform_effect method is on the intent object, the default
        dispatcher raises :class:`NoEffectHandlerError`.
        """
        intent = object()
        self.assertThat(
            lambda: sync_perform(Effect(intent)),
            raises(NoEffectHandlerError(intent)))

    def test_effects_returning_effects(self):
        """
        When the effect dispatcher returns another effect,
        - that effect is immediately performed with the same dispatcher,
        - the result of that is returned.
        """
        self.assertEqual(
            sync_perform(
                Effect(ConstantIntent(Effect(ConstantIntent("foo"))))),
            "foo")

    def test_effects_returning_effects_returning_effects(self):
        """
        If an effect returns an effect which immediately returns an effect
        with no callbacks in between, the result of the innermost effect is
        returned from the outermost effect's perform.
        """
        self.assertEqual(
            sync_perform(
                Effect(
                    ConstantIntent(
                        Effect(
                            ConstantIntent(
                                Effect(
                                    ConstantIntent("foo"))))))),
            "foo")

    def test_sync_perform_async_effect(self):
        """If an effect is asynchronous, sync_effect raises an error."""
        self.assertRaises(NotSynchronousError,
                          lambda: sync_perform(Effect(ConstantIntent("foo")),
                                               dispatcher=lambda i, box: None))


class CallbackTests(TestCase):
    """Tests for callbacks."""

    def test_success(self):
        """
        An Effect with callbacks
        - performs the wrapped intent, passing the default dispatcher,
        - passes the result of that to the callback,
        - returns the result of the callback.
        """
        self.assertThat(
            sync_perform(
                Effect(SelfContainedIntent())
                .on(success=lambda x: (x, "amended!"))),
            MatchesListwise([
                MatchesListwise([
                    Equals("Self-result"),
                    Is(default_dispatcher)]),
                Equals("amended!")]))

    def test_success_propagates_effect_exception(self):
        """
        An Effect with callbacks propagates exceptions from performing
        the inner effect when there is no errback.
        """
        self.assertThat(
            lambda:
                sync_perform(
                    Effect(ErrorIntent()).on(success=lambda x: 'nope')),
            raises(ValueError('oh dear')))

    def test_error_success(self):
        """
        An Effect with callbacks
        - performs the wrapped effect, passing the dispatcher,
        - returns the result (assuming there is no exception).

        In other words, the error handler is skipped when there's no error.
        """
        self.assertThat(
            sync_perform(
                Effect(SelfContainedIntent())
                .on(error=lambda x: (x, "recovered!"))),
            MatchesListwise([
                Equals('Self-result'),
                Is(default_dispatcher)]))

    def test_error(self):
        """
        An Effect with callbacks
        - performs the wrapped effect,
        - in the case of an exception, invokes the errback with exc_info,
        - returns the result of the errback.
        """
        self.assertThat(
            sync_perform(
                Effect(ErrorIntent())
                    .on(error=lambda x: ("handled", x))),
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
                sync_perform(
                    Effect(ErrorIntent())
                        .on(error=lambda x: raise_(ValueError('eb error')))),
            raises(ValueError('eb error')))

    def test_nested_effect_exception_passes_to_outer_error_handler(self):
        """
        If an inner effect raises an exception, it bubbles up and the
        exc_info is passed to the outer effect's error handlers.
        """
        self.assertThat(
            sync_perform(
                Effect(ConstantIntent(Effect(ErrorIntent())))
                    .on(error=lambda x: x)),
            MatchesException(ValueError('oh dear')))

    def test_asynchronous_callback_invocation(self):
        """
        When an Effect that is returned by a callback is resolved
        *asynchronously*, the callbacks will run.
        """
        results = []
        boxes = []
        dispatcher = lambda intent, box: boxes.append(box)
        intent = POPOIntent()
        eff = Effect(intent).on(success=results.append)
        perform(eff, dispatcher)
        boxes[0].succeed('foo')
        self.assertEqual(results, ['foo'])


def raise_(e):
    raise e
