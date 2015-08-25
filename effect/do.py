"""
An imperative-looking notation for Effectful code.

See :func:`do`.
"""


from __future__ import print_function

import sys
import types

from . import Effect, Func
from ._utils import wraps


def do(f):
    """
    A decorator which allows you to use ``do`` notation in your functions, for
    imperative-looking code::

        @do
        def foo():
            thing = yield Effect(Constant(1))
            yield do_return('the result was %r' % (thing,))

        eff = foo()
        return eff.on(...)

    ``@do`` must decorate a generator function (not any other type of
    iterator). Any yielded values must either be Effects or the result of a
    :func:`do_return` call. The result of a yielded Effect will be passed back
    into the generator as the result of the ``yield`` expression. Yielded
    :func:`do_return` values will provide the ultimate result of the Effect
    that is returned by the decorated function. Note that :func:`do_return` is
    only necessary for Python 2 compatibility; return statements can be used
    directly in Python 3-only code.

    It's important to note that any generator function decorated by ``@do``
    will no longer return a generator, but instead it will return an Effect,
    which must be used just like any other Effect.

    Errors are also converted to normal exceptions::

        @do
        def foo():
            try:
                thing = yield Effect(Error(RuntimeError('foo')))
            except RuntimeError:
                yield do_return('got a RuntimeError as expected')

    (This decorator is named for Haskell's ``do`` notation, which is similar in
    spirit).
    """
    @wraps(f)
    def do_wrapper(*args, **kwargs):

        def doit():
            gen = f(*args, **kwargs)
            if not isinstance(gen, types.GeneratorType):
                raise TypeError(
                    "%r is not a generator function. It returned %r."
                    % (f, gen))
            return _do(None, gen, False)

        fname = getattr(f, '__name__', None)
        if fname is not None:
            doit.__name__ = 'do_' + fname

        return Effect(Func(doit))
    return do_wrapper


class _ReturnSentinel(object):
    def __init__(self, result):
        self.result = result


def do_return(val):
    """
    Specify a return value for a @do function.

    The result of this function must be yielded.  e.g.::

        @do
        def foo():
            yield do_return('hello')

    If you're writing Python 3-only code, you don't need to use this function,
    and can just use the `return` statement as normal.
    """
    return _ReturnSentinel(val)


def _do(result, generator, is_error):
    try:
        if is_error:
            val = generator.throw(*result)
        else:
            val = generator.send(result)
    except StopIteration as stop:
        # If the generator we're spinning directly raises StopIteration, we'll
        # treat it like returning None from the function. But there may be a
        # case where some other code is raising StopIteration up through this
        # generator, in which case we shouldn't really treat it like a function
        # return -- it could quite easily hide bugs.
        tb = sys.exc_info()[2]
        if tb.tb_next:
            raise
        else:
            # Python 3 allows you to use `return val` in a generator, which
            # will be translated to a `StopIteration` with a `value` attribute
            # set to the return value. So we'll return that value as the
            # ultimate result of the effect. Python 2 doesn't have the 'value'
            # attribute of StopIteration, so we'll fall back to None.
            return getattr(stop, 'value', None)
    if type(val) is _ReturnSentinel:
        return val.result
    elif type(val) is Effect:
        return val.on(success=lambda r: _do(r, generator, False),
                      error=lambda e: _do(e, generator, True))
    else:
        raise TypeError(
            "@do functions must only yield Effects or results of do_return. "
            "Got %r from %r" % (val, generator))
