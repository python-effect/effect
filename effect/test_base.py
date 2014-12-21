from __future__ import print_function, absolute_import

from functools import partial

import sys
import traceback

from testtools import TestCase
from testtools.matchers import MatchesException, MatchesListwise

from ._base import (Effect, perform, NoPerformerFoundError)


class POPOIntent(object):
    """An example effect intent."""


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
        raised.
        """
        dispatcher = lambda i: None
        self.assertRaises(
            NoPerformerFoundError,
            perform, dispatcher, Effect(object()))

    def test_dispatcher(self):
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
        When effect performance fails, the exception is passed to the error
        callback.
        """
        calls = []
        intent = lambda box: box.fail(
            (ValueError, ValueError('dispatched'), None))
        perform(func_dispatcher, Effect(intent).on(error=calls.append))
        self.assertThat(
            calls,
            MatchesListwise([
                MatchesException(ValueError('dispatched'))]))

    def test_effects_returning_effects(self):
        """
        When the effect dispatcher returns another effect,
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

    def test_bounced(self):
        calls = []

        def out_of_order(box):
            box.succeed("foo")
            calls.append("bar")
        perform(func_dispatcher, Effect(out_of_order).on(success=calls.append))
        self.assertEqual(calls, ["bar", "foo"])

    def test_double_bounced(self):
        calls = []

        def out_of_order(result, after, box):
            box.succeed(result)
            calls.append(after)
        effect = Effect(partial(out_of_order,
                                Effect(partial(out_of_order, "foo", "bar")),
                                "baz"))
        perform(func_dispatcher, effect.on(success=calls.append))
        self.assertEqual(calls, ["baz", "bar", "foo"])

    def test_callbacks_bounced(self):
        calls = []

        def get_stack(_):
            calls.append(traceback.extract_stack())
        perform(func_dispatcher,
                Effect(None).on(success=get_stack).on(success=get_stack))
        self.assertEqual(calls[0], calls[1])

    def test_effect_bounced(self):
        calls = []

        def get_stack(box):
            calls.append(traceback.extract_stack())
            box.succeed(None)

        perform(func_dispatcher,
                Effect(get_stack).on(success=lambda _: Effect(get_stack)))
        self.assertEqual(calls[0], calls[1])

    def test_callback_error(self):
        calls = []

        def raise_(_):
            try:
                raise ValueError("oh dear")
            except ValueError:
                calls.append(sys.exc_info())
                raise

        perform(func_dispatcher,
                Effect(lambda box: box.succeed("foo"))
                .on(success=lambda _: raise_(ValueError("oh dear")))
                .on(error=calls.append))
        self.assertEqual(traceback.extract_tb(calls[0][2]),
                         traceback.extract_tb(calls[1][2])[-1:])
        self.assertEqual(calls[0][:2], calls[1][:2])
