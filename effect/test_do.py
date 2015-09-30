import sys
from functools import partial

from py.test import raises as raises
from py.test import mark

import six

from . import (
    ComposedDispatcher, Constant, Effect, Error, TypeDispatcher,
    base_dispatcher, sync_perform, sync_performer)
from .do import do, do_return


def perf(e):
    return sync_perform(base_dispatcher, e)


def test_do_non_gf():
    """When do is passed a non-generator function, it raises an error."""
    f = lambda: None
    with raises(TypeError) as err_info:
        perf(do(f)())
    assert (str(err_info.value)
            == "%r is not a generator function. It returned None." % (f,))


def test_do_return():
    """
    When a @do function yields a do_return, the given value becomes the
    eventual result.
    """
    @do
    def f():
        yield do_return("hello")
    assert perf(f()) == "hello"


def test_do_return_effect():
    @do
    def f():
        yield do_return(Effect(Constant("hello")))
    assert perf(f()) == "hello"


def test_yield_effect():
    """Yielding an effect in @do results in the Effect's result."""
    @do
    def f():
        x = yield Effect(Constant(3))
        yield do_return(x)
    perf(f()) == 3


def test_fall_off_the_end():
    """Falling off the end results in None."""
    @do
    def f():
        yield Effect(Constant(3))
    assert perf(f()) is None


def test_yield_non_effect():
    """Yielding a non-Effect results in a TypeError."""
    @do
    def f():
        yield 1
    result = f()
    with raises(TypeError) as err_info:
        perf(result)
    assert str(err_info.value).startswith(
        '@do functions must only yield Effects or results of '
        'do_return. Got 1 from <generator object f at')


def test_raise_from_effect():
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

    exc_type, exc, _ = perf(f())
    assert exc_type is ZeroDivisionError
    assert str(exc) == 'foo'


def test_works_with_sync_perform():
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
    assert sync_perform(disp, Effect(MyIntent())) == 2


def test_promote_metadata():
    """
    The decorator copies metadata from the wrapped function onto the
    wrapper.
    """
    def original(dispatcher, intent):
        """Original!"""
        yield do_return(1)
    original.attr = 1
    wrapped = do(original)
    assert wrapped.__name__ == 'original'
    assert wrapped.attr == 1
    assert wrapped.__doc__ == 'Original!'


def test_ignore_lack_of_metadata():
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
    assert wrapped.__name__ == 'do_wrapper'


def test_repeatable_effect():
    """
    The Effect returned by the call to the @do function is repeatable.
    """
    @do
    def f():
        x = yield Effect(Constant('foo'))
        yield do_return(x)
    eff = f()
    assert perf(eff) == 'foo'
    perf(eff) == 'foo'


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
