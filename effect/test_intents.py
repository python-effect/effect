from __future__ import print_function, absolute_import

from testtools import TestCase

from ._base import Effect
from ._sync import sync_perform
from .dispatcher import TypeDispatcher

from ._intents import (
    ConstantIntent, perform_constant,
    ErrorIntent, perform_error,
    FuncIntent, perform_func,
)


class IntentTests(TestCase):
    """Tests for intents."""

    def test_perform_constant(self):
        """
        perform_constant returns the result of a ConstantIntent.
        """
        intent = ConstantIntent("foo")
        result = sync_perform(
            TypeDispatcher({ConstantIntent: perform_constant}),
            Effect(intent))
        self.assertEqual(result, "foo")

    def test_perform_error(self):
        """
        perform_error raises the exception of a ErrorIntent.
        """
        intent = ErrorIntent(ValueError("foo"))
        self.assertRaises(
            ValueError,
            lambda: sync_perform(
                TypeDispatcher({ErrorIntent: perform_error}),
                Effect(intent)))

    def test_perform_func(self):
        """
        perform_func calls the function given in a FuncIntent.
        """
        intent = FuncIntent(lambda: "foo")
        result = sync_perform(
            TypeDispatcher({FuncIntent: perform_func}),
            Effect(intent))
        self.assertEqual(result, "foo")
