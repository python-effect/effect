from functools import partial

from testtools import TestCase
from testtools.matchers import MatchesException, raises

from ._base import Effect
from ._sync import NotSynchronousError, sync_perform, sync_performer


def func_dispatcher(intent):
    def performer(dispatcher, intent, box):
        intent(box)
    return performer


class SyncPerformTests(TestCase):
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
        """Return value of the performer becomes the result of the Effect."""
        @sync_performer
        def succeed(dispatcher, intent):
            return intent

        dispatcher = lambda _: succeed
        result = sync_perform(dispatcher, Effect("foo"))
        self.assertEqual(result, "foo")

    def test_failure(self):
        """
        Errors are caught and cause the effect to fail with the exception info.
        """
        @sync_performer
        def fail(dispatcher, intent):
            raise intent

        dispatcher = lambda _: fail
        self.assertThat(
            sync_perform(dispatcher,
                         Effect(ValueError('oh dear')).on(error=lambda e: e)),
            MatchesException(ValueError('oh dear')))

    def test_instance_method_performer(self):
        """The decorator works on instance methods."""
        eff = Effect('meaningless')

        class PerformerContainer(object):
            @sync_performer
            def performer(self, dispatcher, intent):
                return (self, dispatcher, intent)

        container = PerformerContainer()

        dispatcher = lambda i: container.performer
        result = sync_perform(dispatcher, eff)
        self.assertEqual(result, (container, dispatcher, 'meaningless'))

    def test_promote_metadata(self):
        """
        The decorator copies metadata from the wrapped function onto the
        wrapper.
        """
        def original(dispatcher, intent):
            """Original!"""
            pass
        original.attr = 1
        wrapped = sync_performer(original)
        self.assertEqual(wrapped.__name__, 'original')
        self.assertEqual(wrapped.attr, 1)
        self.assertEqual(wrapped.__doc__, 'Original!')

    def test_ignore_lack_of_metadata(self):
        """
        When the original callable is not a function, a new function is still
        returned.
        """
        def original(something, dispatcher, intent):
            """Original!"""
            pass
        new_func = partial(original, 'something')
        original.attr = 1
        wrapped = sync_performer(new_func)
        self.assertEqual(wrapped.__name__, 'sync_wrapper')

    def test_kwargs(self):
        """Additional kwargs are passed through."""
        @sync_performer
        def p(dispatcher, intent, extra):
            return extra

        dispatcher = lambda _: partial(p, extra='extra val')
        result = sync_perform(dispatcher, Effect('foo'))
        self.assertEqual(result, 'extra val')
