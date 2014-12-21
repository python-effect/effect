from __future__ import print_function, absolute_import

from functools import partial

import sys
import six
import traceback

from testtools import TestCase
from testtools.matchers import (MatchesListwise, Is, Equals, MatchesException,
                                raises)

from ._base import (Effect, perform, NoPerformerFoundError)


class POPOIntent(object):
    """An example effect intent."""


def raise_(e):
    raise e


class EffectPerformTests(TestCase):
    """Tests for perform."""

    def test_no_performer(self):
        """
        When a dispatcher returns None, :class:`NoPerformerFoundError` is raised.
        """
        dispatcher = lambda i: None
        self.assertRaises(
            NoPerformerFoundError,
            perform, dispatcher, Effect(object()))


    def test_success_with_callback(self):
        """
        perform
        - invokes the given dispatcher with the intent and a box
        - uses the result given to the box as the argument of an
          effect's callback
        """
        calls = []
        dispatcher = lambda i: lambda d, i, box: box.succeed((i, 'dispatched'))
        intent = POPOIntent()
        perform(dispatcher, Effect(intent).on(calls.append))
        self.assertEqual(calls, [(intent, 'dispatched')])


    def test_error_with_callback(self):
        """
        When effect performance fails, the exception is raised up through
        sync_perform.
        """
        calls = []
        # FIXME: this fails with somethign that isn't sys.exc_info() data
        dispatcher = lambda i: lambda d, i, box: box.fail((i, 'dispatched'))
        intent = POPOIntent()
        perform(dispatcher, Effect(intent).on(error=calls.append))
        self.assertEqual(calls, [(intent, 'dispatched')])


    def test_effects_returning_effects(self):
        """
        When the effect dispatcher returns another effect,
        - that effect is immediately performed with the same dispatcher,
        - the result of that is returned.
        """
        calls = []
        dispatcher = lambda i: lambda d, i, box: i(box)
        perform(dispatcher, Effect(lambda box: box.succeed(Effect(lambda box: calls.append("foo")))))
        self.assertEqual(calls, ['foo'])


    def test_effects_returning_effects_returning_effects(self):
        """
        If an effect returns an effect which immediately returns an effect
        with no callbacks in between, the result of the innermost effect is
        returned from the outermost effect's perform.
        """
        calls = []
        dispatcher = lambda i: lambda d, i, box: i(box)
        perform(dispatcher,
                Effect(lambda box: box.succeed(
                    Effect(lambda box: box.succeed(
                        Effect(lambda box: calls.append("foo")))))))
        self.assertEqual(calls, ['foo'])


    def test_bounced(self):
        calls = []
        dispatcher = lambda i: lambda d, i, box: i(box)
        def out_of_order(box):
            box.succeed("foo")
            calls.append("bar")
        perform(dispatcher, Effect(out_of_order).on(success=calls.append))
        self.assertEqual(calls, ["bar", "foo"])


    def test_double_bounced(self):
        calls = []
        dispatcher = lambda i: lambda d, i, box: i(box)
        def out_of_order(result, after, box):
            box.succeed(result)
            calls.append(after)
        effect = Effect(partial(out_of_order, Effect(partial(out_of_order, "foo", "bar")), "baz"))
        perform(dispatcher, effect.on(success=calls.append))
        self.assertEqual(calls, ["baz", "bar", "foo"])

    def test_callbacks_bounced(self):
        calls = []
        dispatcher = lambda i: lambda d, i, box: box.succeed("foo")
        def get_stack(_):
            calls.append(traceback.extract_stack())
        perform(dispatcher, Effect(None).on(success=get_stack).on(success=get_stack))
        self.assertEqual(calls[0], calls[1])

    def test_effect_bounced(self):
        calls = []
        dispatcher = lambda i: lambda d, i, box: i(box)
        def get_stack(box):
            calls.append(traceback.extract_stack())
            box.succeed(None)

        perform(dispatcher, Effect(get_stack).on(success=lambda _: Effect(get_stack)))
        self.assertEqual(calls[0], calls[1])


    def test_callback_error(self):
        calls = []
        dispatcher = lambda i: lambda d, i, box: box.succeed("foo")
        def raise_(_):
            try:
                raise ValueError("oh dear")
            except ValueError:
                calls.append(sys.exc_info())
                raise

        perform(dispatcher, Effect(None).on(success=lambda _: raise_(ValueError("oh dear"))).on(error=calls.append))
        self.assertEqual(traceback.extract_tb(calls[0][2]), traceback.extract_tb(calls[1][2])[-1:])
        self.assertEqual(calls[0][:2], calls[1][:2])
