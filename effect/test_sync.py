from testtools import TestCase
from testtools.matchers import (
    MatchesException, raises)

from . import Effect
from ._sync import sync_perform, NotSynchronousError, sync_performer


def func_dispatcher(intent):
    def performer(dispatcher, intent, box):
        intent(box)
    return performer


class SyncPerformtTests(TestCase):
    """Tests for :func:`sync_perform`."""

    def test_sync_perform_effect_function_dispatch(self):
        """
        sync_perform returns the result of the effect.
        """
        intent = lambda box: box.succeed("foo")
        self.assertEqual(
            sync_perform(func_dispatcher, Effect(intent)),
            'foo')

    def test_sync_perform_async_effect(self):
        """If an effect is asynchronous, sync_effect raises an error."""
        intent = lambda box: None
        self.assertRaises(
            NotSynchronousError,
            lambda: sync_perform(func_dispatcher, Effect(intent)))

    def test_error_bubbles_up(self):
        """
        When effect performance fails, the exception is raised up through
        sync_perform.
        """
        def fail(box):
            box.fail((ValueError, ValueError("oh dear"), None))
        self.assertThat(
            lambda: sync_perform(func_dispatcher, Effect(fail)),
            raises(ValueError('oh dear')))


class SyncPerformerTests(TestCase):
    """
    Tests for :func:`sync_performer`.
    """

    def test_success(self):
        @sync_performer
        def succeed(dispatcher, intent):
            return intent

        dispatcher = lambda _: succeed
        result = sync_perform(dispatcher, Effect("foo"))
        self.assertEqual(result, "foo")

    def test_failure(self):
        @sync_performer
        def fail(dispatcher, intent):
            raise intent

        dispatcher = lambda _: fail
        self.assertThat(
            sync_perform(dispatcher,
                         Effect(ValueError('oh dear')).on(error=lambda e: e)),
            MatchesException(ValueError('oh dear')))
