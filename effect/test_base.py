from __future__ import print_function, absolute_import

import sys
import traceback

from testtools import TestCase
from testtools.matchers import MatchesException, MatchesListwise

from ._base import Effect, NoPerformerFoundError, catch, perform
from ._test_utils import raise_


def func_dispatcher(intent):
    """
    Simple effect dispatcher that takes callables taking a box,
    and calls them with the given box.
    """
    def performer(dispatcher, intent, box):
        intent(box)
    return performer


class EffectPerformTests(TestCase):
    """Tests for perform."""

    def test_no_performer(self):
        """
        When a dispatcher returns None, :class:`NoPerformerFoundError` is
        provided as an error to the Effect's callbacks.
        """
        dispatcher = lambda i: None
        calls = []
        intent = object()
        eff = Effect(intent).on(error=calls.append)
        perform(dispatcher, eff)
        self.assertThat(
            calls,
            MatchesListwise([
                MatchesException(NoPerformerFoundError(intent))
            ]))

    def test_dispatcher(self):
        """
        ``perform`` calls the provided dispatcher, with the intent of the
        provided effect. The returned perform is called with the dispatcher and
        intent.
        """
        calls = []

        def dispatcher(intent):
            calls.append(intent)

            def performer(dispatcher, intent, box):
                calls.append((dispatcher, intent))

            return performer

        intent = object()
        perform(dispatcher, Effect(intent))
        self.assertEquals(calls, [intent, (dispatcher, intent)])

    def test_success_with_callback(self):
        """
        perform uses the result given to the box as the argument of an
          effect's callback
        """
        calls = []
        intent = lambda box: box.succeed('dispatched')
        perform(func_dispatcher, Effect(intent).on(calls.append))
        self.assertEqual(calls, ['dispatched'])

    def test_error_with_callback(self):
        """
        When an effect performer calls ``box.fail``, the exception is passed to
        the error callback.
        """
        calls = []
        intent = lambda box: box.fail(
            (ValueError, ValueError('dispatched'), None))
        perform(func_dispatcher, Effect(intent).on(error=calls.append))
        self.assertThat(
            calls,
            MatchesListwise([
                MatchesException(ValueError('dispatched'))]))

    def test_dispatcher_raises(self):
        """
        When a dispatcher raises an exception, the exc_info is passed to the
        error handler.
        """
        calls = []
        eff = Effect('meaningless').on(error=calls.append)
        dispatcher = lambda i: raise_(ValueError('oh dear'))
        perform(dispatcher, eff)
        self.assertThat(
            calls,
            MatchesListwise([
                MatchesException(ValueError('oh dear'))
            ])
        )

    def test_performer_raises(self):
        """
        When a performer raises an exception, the exc_info is passed to the
        error handler.
        """
        calls = []
        eff = Effect('meaningless').on(error=calls.append)
        performer = lambda d, i, box: raise_(ValueError('oh dear'))
        dispatcher = lambda i: performer
        perform(dispatcher, eff)
        self.assertThat(
            calls,
            MatchesListwise([
                MatchesException(ValueError('oh dear'))
            ])
        )

    def test_success_propagates_effect_exception(self):
        """
        If an succes callback is specified, but a exception result occurs,
        the exception is passed to the next callback.
        """
        calls = []
        intent = lambda box: box.fail(
            (ValueError, ValueError('dispatched'), None))
        perform(func_dispatcher,
                Effect(intent)
                .on(success=lambda box: calls.append("foo"))
                .on(error=calls.append))
        self.assertThat(
            calls,
            MatchesListwise([
                MatchesException(ValueError('dispatched'))]))

    def test_error_propagates_effect_result(self):
        """
        If an error callback is specified, but a succesful result occurs,
        the success is passed to the next callback.
        """
        calls = []
        intent = lambda box: box.succeed("dispatched")
        perform(func_dispatcher,
                Effect(intent)
                .on(error=lambda box: calls.append("foo"))
                .on(success=calls.append))
        self.assertEqual(calls, ["dispatched"])

    def test_callback_sucecss_exception(self):
        """
        If a success callback raises an error, the exception is passed to the
        error callback.
        """
        calls = []

        perform(func_dispatcher,
                Effect(lambda box: box.succeed("foo"))
                .on(success=lambda _: raise_(ValueError("oh dear")))
                .on(error=calls.append))
        self.assertThat(
            calls,
            MatchesListwise([
                MatchesException(ValueError('oh dear'))]))

    def test_callback_error_exception(self):
        """
        If a error callback raises an error, the exception is passed to the
        error callback.
        """
        calls = []

        intent = lambda box: box.fail(
            (ValueError, ValueError('dispatched'), None))

        perform(func_dispatcher,
                Effect(intent)
                .on(error=lambda _: raise_(ValueError("oh dear")))
                .on(error=calls.append))
        self.assertThat(
            calls,
            MatchesListwise([
                MatchesException(ValueError('oh dear'))]))

    def test_effects_returning_effects(self):
        """
        When the effect performer returns another effect,
        - that effect is immediately performed with the same dispatcher,
        - the result of that is returned.
        """
        calls = []
        perform(func_dispatcher,
                Effect(lambda box: box.succeed(
                    Effect(lambda box: calls.append("foo")))))
        self.assertEqual(calls, ['foo'])

    def test_effects_returning_effects_returning_effects(self):
        """
        If an effect returns an effect which immediately returns an effect
        with no callbacks in between, the result of the innermost effect is
        returned from the outermost effect's perform.
        """
        calls = []
        perform(func_dispatcher,
                Effect(lambda box: box.succeed(
                    Effect(lambda box: box.succeed(
                        Effect(lambda box: calls.append("foo")))))))
        self.assertEqual(calls, ['foo'])

    def test_nested_effect_exception_passes_to_outer_error_handler(self):
        """
        If an inner effect raises an exception, it bubbles up and the
        exc_info is passed to the outer effect's error handlers.
        """
        calls = []
        intent = lambda box: box.fail(
            (ValueError, ValueError('oh dear'), None))
        perform(func_dispatcher,
                Effect(lambda box: box.succeed(Effect(intent)))
                .on(error=calls.append))
        self.assertThat(
            calls,
            MatchesListwise([
                MatchesException(ValueError('oh dear'))]))

    def test_bounced(self):
        """
        The callbacks of a performer are called after the performer returns.
        """
        calls = []

        def out_of_order(box):
            box.succeed("foo")
            calls.append("bar")
        perform(func_dispatcher, Effect(out_of_order).on(success=calls.append))
        self.assertEqual(calls, ["bar", "foo"])

    def test_callbacks_bounced(self):
        """
        Multiple callbacks don't increase the stack depth.
        """
        calls = []

        def get_stack(_):
            calls.append(traceback.extract_stack())
        perform(func_dispatcher,
                Effect(lambda box: box.succeed(None))
                .on(success=get_stack).on(success=get_stack))
        self.assertEqual(calls[0], calls[1])

    def test_effect_bounced(self):
        """
        When an effect returns another effect, the effects are performed at the
        same stack depth.
        """
        calls = []

        def get_stack(box):
            calls.append(traceback.extract_stack())
            box.succeed(None)

        perform(func_dispatcher,
                Effect(get_stack).on(success=lambda _: Effect(get_stack)))
        self.assertEqual(calls[0], calls[1])

    def test_asynchronous_callback_invocation(self):
        """
        When an Effect that is returned by a callback is resolved
        *asynchronously*, the callbacks will run.
        """
        results = []
        boxes = []
        eff = Effect(boxes.append).on(success=results.append)
        perform(func_dispatcher, eff)
        boxes[0].succeed('foo')
        self.assertEqual(results, ['foo'])

    def test_asynchronous_callback_bounced(self):
        """
        When an Effect that is returned by a callback is resolved
        *asynchronously*, the callbacks are performed at the same stack depth.
        """
        calls = []

        def get_stack(_):
            calls.append(traceback.extract_stack())

        boxes = []
        eff = Effect(boxes.append).on(success=get_stack).on(success=get_stack)
        perform(func_dispatcher, eff)
        boxes[0].succeed('foo')
        self.assertEqual(calls[0], calls[1])


class CatchTests(TestCase):
    """Tests for :func:`catch`."""

    def test_caught(self):
        """
        When the exception type matches the type in the ``exc_info`` tuple, the
        callable is invoked and its result is returned.
        """
        try:
            raise RuntimeError('foo')
        except:
            exc_info = sys.exc_info()
        result = catch(RuntimeError, lambda e: ('caught', e))(exc_info)
        self.assertEqual(result, ('caught', exc_info))

    def test_missed(self):
        """
        When the exception type does not match the type in the ``exc_info``
        tuple, the callable is not invoked and the original exception is
        reraised.
        """
        try:
            raise ZeroDivisionError('foo')
        except:
            exc_info = sys.exc_info()
        e = self.assertRaises(
            ZeroDivisionError,
            lambda: catch(RuntimeError, lambda e: ('caught', e))(exc_info))
        self.assertEqual(str(e), 'foo')
