from __future__ import print_function, absolute_import

from testtools import TestCase

from ._base import Effect
from ._sync import sync_perform
from ._dispatcher import TypeDispatcher

from ._intents import (
    Constant, perform_constant,
    Error, perform_error,
    Func, perform_func,
    FirstError)


class IntentTests(TestCase):
    """Tests for intents."""

    def test_perform_constant(self):
        """
        perform_constant returns the result of a Constant.
        """
        intent = Constant("foo")
        result = sync_perform(
            TypeDispatcher({Constant: perform_constant}),
            Effect(intent))
        self.assertEqual(result, "foo")

    def test_perform_error(self):
        """
        perform_error raises the exception of a Error.
        """
        intent = Error(ValueError("foo"))
        self.assertRaises(
            ValueError,
            lambda: sync_perform(
                TypeDispatcher({Error: perform_error}),
                Effect(intent)))

    def test_perform_func(self):
        """
        perform_func calls the function given in a Func.
        """
        intent = Func(lambda: "foo")
        result = sync_perform(
            TypeDispatcher({Func: perform_func}),
            Effect(intent))
        self.assertEqual(result, "foo")


class ParallelTests(TestCase):
    """Tests for :func:`parallel`."""

    def test_first_error_str(self):
        """FirstErrors have a pleasing format."""
        fe = FirstError(exc_info=(ValueError, ValueError('foo'), None),
                        index=150)
        self.assertEqual(
            str(fe),
            '(index=150) ValueError: foo')
