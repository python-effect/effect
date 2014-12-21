from testtools import TestCase
from testtools.matchers import (
    # MatchesListwise, Equals, MatchesException,
    raises)

from . import Effect
from ._sync import sync_perform, NotSynchronousError


def func_dispatcher(intent):
    def performer(dispatcher, intent, box):
        intent(box)
    return performer


class SyncPerformEffectTests(TestCase):
    """Tests for :func:`perform_effect`."""

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
