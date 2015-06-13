import sys
from functools import partial

from py.test import raises as raises
from py.test import mark

import six

from testtools import TestCase
from testtools.matchers import raises as match_raises, MatchesException

from . import (
    ComposedDispatcher, Constant, Effect, Error, TypeDispatcher,
    base_dispatcher, sync_perform, sync_performer)
from .do import do, do_return


def perf(e):
    return sync_perform(base_dispatcher, e)


class DoTests(TestCase):

    def test_do_non_gf(self):
        """When do is passed a non-generator function, it raises an error."""
        f = lambda: None
        self.assertThat(
            lambda: perf(do(f)()),
            match_raises(TypeError(
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
        e = self.assertRaises(TypeError, lambda: perf(result))
        self.assertTrue(
            str(e).startswith(
                '@do functions must only yield Effects or results of '
                'do_return. Got 1 from <generator object f at'))

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

    def test_works_with_sync_perform(self):
        """@sync_performer and @do cooperate fine."""
        @sync_performer
        @do
        def perform_myintent(dispatcher, myintent):
            result = yield Effect(Constant(1))
            yield do_return(result + 1)

        class MyIntent(object):
            pass

        disp = ComposedDispatcher([
            TypeDispatcher({MyIntent: perform_myintent}),
            base_dispatcher])
        self.assertEqual(sync_perform(disp, Effect(MyIntent())), 2)

    def test_promote_metadata(self):
        """
        The decorator copies metadata from the wrapped function onto the
        wrapper.
        """
        def original(dispatcher, intent):
            """Original!"""
            yield do_return(1)
        original.attr = 1
        wrapped = do(original)
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
        wrapped = do(new_func)
        self.assertEqual(wrapped.__name__, 'do_wrapper')

    def test_repeatable_effect(self):
        """
        The Effect returned by the call to the @do function is repeatable.
        """
        @do
        def f():
            x = yield Effect(Constant('foo'))
            yield do_return(x)
        eff = f()
        self.assertEqual(perf(eff), 'foo')
        self.assertEqual(perf(eff), 'foo')


def test_stop_iteration_only_local():
    """
    Arbitrary :obj:`StopIteration` exceptions are not treated the same way as
    falling off the end of the generator -- they are raised through.
    """
    @do
    def f():
        raise StopIteration()
        yield Effect(Constant('foo'))

    eff = f()
    with raises(StopIteration):
        perf(eff)


@mark.skipif(not six.PY3, reason="Testing a Py3-specific feature")
def test_py3_return():
    """The `return x` syntax in Py3 sets the result of the Effect to `x`."""
    from effect._test_do_py3 import py3_generator_with_return
    eff = py3_generator_with_return()
    assert perf(eff) == 2
