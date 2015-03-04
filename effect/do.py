"""
An imperative-looking notation for Effectful code.

See :func:`do`.
"""


from __future__ import print_function

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

    ``@do`` must decorate a generator function. Any yielded values must either
    be Effects or the result of a :func:`do_return` call. The result of a
    yielded Effect will be passed back into the generator as the result of the
    ``yield`` expression. Yielded :func:`do_return` values will provide the
    ultimate result of the Effect that is returned by the decorated function.

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
    """
    return _ReturnSentinel(val)


def _do(result, generator, is_error):
    try:
        if is_error:
            val = generator.throw(*result)
        else:
            val = generator.send(result)
    except StopIteration:
        return None
    if type(val) is _ReturnSentinel:
        return val.result
    elif type(val) is Effect:
        return val.on(success=lambda r: _do(r, generator, False),
                      error=lambda e: _do(e, generator, True))
    else:
        raise TypeError(
            "@do functions must only yield Effects or results of do_return. "
            "Got %r from %r" % (val, generator))
