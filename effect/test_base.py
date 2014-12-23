from __future__ import print_function, absolute_import

import traceback

from testtools import TestCase
from testtools.matchers import MatchesException, MatchesListwise

from ._base import Effect, NoPerformerFoundError, perform


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

    def test_recurse_effects(self):
        """
        If ``recurse_effects`` is ``False``, and an effect returns another
        effect, that effect returned.
        """
        calls = []
        effect = Effect(lambda box: calls.append("foo"))
        perform(func_dispatcher,
                Effect(lambda box: box.succeed(effect)).on(calls.append),
                recurse_effects=False)
        self.assertEqual(calls, [effect])

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

    def test_callback_error(self):
        """
        If a callback raises an error, the exception is passed to the error
        callback.
        """
        calls = []

        def raise_(_):
            raise ValueError("oh dear")

        perform(func_dispatcher,
                Effect(lambda box: box.succeed("foo"))
                .on(success=lambda _: raise_(ValueError("oh dear")))
                .on(error=calls.append))
        self.assertThat(
            calls,
            MatchesListwise([
                MatchesException(ValueError('oh dear'))]))
