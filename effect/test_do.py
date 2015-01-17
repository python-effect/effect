import sys

from testtools import TestCase
from testtools.matchers import raises, MatchesException

from . import Constant, Effect, Error, base_dispatcher, sync_perform
from .do import do, do_return


def perf(e):
    return sync_perform(base_dispatcher, e)


class DoTests(TestCase):

    def test_do_non_gf(self):
        """When do is passed a non-generator function, it raises an error."""
        f = lambda: None
        self.assertThat(
            do(f),
            raises(TypeError(
                "%r is not a generator function. It returned None." % (f,)
            )))

    def test_do_return(self):
        """
        When a @do function yields a do_return, the given value becomes the
        eventual result.
        """
        @do
        def f():
            yield do_return("hello")
        self.assertEqual(perf(f()), "hello")

    def test_yield_effect(self):
        """Yielding an effect in @do results in the Effect's result."""
        @do
        def f():
            x = yield Effect(Constant(3))
            yield do_return(x)
        self.assertEqual(perf(f()), 3)

    def test_fall_off_the_end(self):
        """Falling off the end results in None."""
        @do
        def f():
            yield Effect(Constant(3))
        self.assertEqual(perf(f()), None)

    def test_yield_non_effect(self):
        """Yielding a non-Effect results in a TypeError."""
        @do
        def f():
            yield 1
        result = f()
        self.assertThat(
            lambda: perf(result),
            raises(TypeError(
                "@do functions must only yield Effects or results of "
                "do_return. Got 1")))

    def test_raise_from_effect(self):
        """
        If an Effect results in an error, it will be raised as a synchronous
        exception in the generator.
        """
        @do
        def f():
            try:
                yield Effect(Error(ZeroDivisionError('foo')))
            except:
                got_error = sys.exc_info()
            yield do_return(got_error)

        self.assertThat(
            perf(f()),
            MatchesException(ZeroDivisionError('foo')))
