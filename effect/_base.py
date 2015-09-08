# -*- test-case-name: effect.test_base -*-
from __future__ import print_function, absolute_import

import sys

from functools import partial

import attr

import six

from ._continuation import trampoline


@attr.s
class Effect(object):
    """
    Take an object that describes a desired effect (called an "Intent"), and
    allow binding callbacks to be called with the result of the effect.

    Effects can be performed with :func:`perform`.

    :param intent: The intent to be performed.
    """

    intent = attr.ib()
    callbacks = attr.ib(default=attr.Factory(list))

    def on(self, success=None, error=None):
        """
        Return a new Effect with the given success and/or error callbacks
        bound.

        The result of the Effect will be passed to the first callback. Any
        callbacks added afterwards will receive the result of the previous
        callback. Normal return values are passed on to the next ``success``
        callback, and exceptions are passed to the next ``error`` callback
        as a ``sys.exc_info()`` tuple.

        If a callback returns an :obj:`Effect`, the result of that
        :obj:`Effect` will be passed to the next callback.
        """
        return Effect(self.intent,
                      callbacks=self.callbacks + [(success, error)])


class _Box(object):
    """
    An object into which an effect dispatcher can place a result.
    """
    def __init__(self, cont):
        """
        :param callable cont: Called with (bool is_error, result)
        """
        self._cont = cont

    def succeed(self, result):
        """
        Indicate that the effect has succeeded, and the result is available.
        """
        self._cont((False, result))

    def fail(self, result):
        """
        Indicate that the effect has failed. result must be an exc_info tuple.
        """
        self._cont((True, result))


def guard(f, *args, **kwargs):
    """
    Run a function.

    Return (is_error, result), where is_error is a boolean indicating whether
    it raised an exception. In that case result will be ``sys.exc_info()``.
    """
    try:
        return (False, f(*args, **kwargs))
    except:
        return (True, sys.exc_info())


class NoPerformerFoundError(Exception):
    """Raised when a performer for an intent couldn't be found."""


def perform(dispatcher, effect):
    """
    Perform an effect and invoke callbacks bound to it. You probably don't want
    to use this. Instead, use :func:`sync_perform` (or, if you're using
    Twisted, see the `txeffect`_ library).

    The dispatcher will be called with the intent, and is expected to return a
    performer (another callable). See :obj:`TypeDispatcher` and
    :obj:`ComposedDispatcher` for some implementations of dispatchers, and
    :obj:`effect.base_dispatcher` for a dispatcher supporting basic intents
    like :obj:`Constant` et al.

    The performer will often be decorated with :func:`sync_performer` or the
    ``deferred_performer`` from `txeffect`_ and will be invoked with the
    dispatcher [#dispatcher]_ and the intent, and should perform the desired
    effect. [#box]_ The performer should return the result of the effect, or
    raise an exception, and the result will be passed on to the first callback,
    then the result of the first callback will be passed to the next callback,
    and so on.

    .. _`txeffect`: https://warehouse.python.org/project/txeffect

    Both performers and callbacks may return regular values, raise exceptions,
    or return another Effect, which will be recursively performed, such that
    the result of the returned Effect becomes the result passed to the next
    callback. In the case of exceptions, the next error-callback will be called
    with a ``sys.exc_info()``-style tuple.

    :returns: None

    .. [#dispatcher] The dispatcher is passed because some performers need to
       make recursive calls to :func:`perform`, because they need to perform
       other effects (see :func:`parallel` and :func:`.perform_parallel_async`
       for an example of this).

    .. [#box] Without using one of those decorators, the performer is actually
       passed three arguments, not two: the dispatcher, the intent, and a
       "box". The box is an object that lets the performer provide the result,
       optionally asynchronously. To provide the result, use
       ``box.succeed(result)`` or ``box.fail(exc_info)``, where ``exc_info`` is
       a ``sys.exc_info()``-style tuple. Decorators like :func:`sync_performer`
       simply abstract this away.
    """
    def _run_callbacks(bouncer, chain, result):
        is_error, value = result

        if type(value) is Effect:
            bouncer.bounce(
                _perform,
                Effect(value.intent, callbacks=value.callbacks + chain))
            return

        if not chain:
            return

        cb = chain[0][is_error]
        if cb is not None:
            result = guard(cb, value)
        chain = chain[1:]
        bouncer.bounce(_run_callbacks, chain, result)

    def _perform(bouncer, effect):
        try:
            performer = dispatcher(effect.intent)
            if performer is None:
                raise NoPerformerFoundError(effect.intent)
            else:
                performer(
                    dispatcher,
                    effect.intent,
                    _Box(partial(bouncer.bounce,
                                 _run_callbacks, effect.callbacks)))
        except:
            e = sys.exc_info()
            _run_callbacks(bouncer, effect.callbacks, (True, e))

    trampoline(_perform, effect)


def catch(exc_type, callable):
    """
    A helper for handling errors of a specific type::

        eff.on(error=catch(SpecificException,
                           lambda exc_info: "got an error!"))

    If any exception other than a ``SpecificException`` is thrown, it will be
    ignored by this handler and propogate further down the chain of callbacks.
    """
    def catcher(exc_info):
        if isinstance(exc_info[1], exc_type):
            return callable(exc_info)
        six.reraise(*exc_info)
    return catcher


def raise_(exception, tb=None):
    """Simple convenience function to allow raising exceptions from lambdas.

    This is slightly more convenient than ``six.reraise`` because it takes an
    exception instance instead of needing the type separate from the instance.

    :param exception: An exception *instance* (not an exception type).

    - ``raise_(exc)`` is the same as ``raise exc``.
    - ``raise_(exc, tb)`` is the same as ``raise type(exc), exc, tb``.
    """
    six.reraise(type(exception), exception, tb)
