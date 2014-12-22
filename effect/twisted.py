# -*- test-case-name: effect.test_twisted -*-

"""
Twisted integration for the Effect library.

This is largely concerned with bridging the gap between Effects and Deferreds,
and also implementing Twisted-specific performers for standard Intents.

The most important functions here are :func:`perform`,
:func:`make_twisted_dispatcher`, and :func:`deferred_performer`.

Note that the core effect library does *not* depend on Twisted, but this module
does.
"""

from __future__ import absolute_import

from functools import partial
import sys
import warnings

from twisted.internet.defer import Deferred, maybeDeferred, gatherResults
from twisted.python.failure import Failure
from twisted.python.deprecate import deprecated
from twisted.python.versions import Version
from twisted.internet.task import deferLater

from ._base import perform as base_perform
from . import Delay
from .dispatcher import TypeDispatcher
from effect import ParallelEffects


def deferred_to_box(d, box):
    """
    Make a Deferred pass its success or fail events on to the given box.
    """
    d.addCallbacks(box.succeed, lambda f: box.fail((f.type, f.value, f.tb)))


def make_twisted_dispatcher(reactor):
    """
    Create a dispatcher that knows how to perform certain built-in Intents
    with Twisted-specific implementations.
    """
    return TypeDispatcher({
        ParallelEffects: perform_parallel,
        Delay: deferred_performer(partial(perform_delay, reactor)),
    })


@deprecated(Version('effect', 0, 1, 12),
            "put performers in a TypedDispatcher and pass to perform")
def legacy_dispatcher(intent):
    """
    DEPRECATED.

    A dispatcher that supports the old 'perform_effect' methods on intent
    objects. We recommend specifying your performers in a :obj:`TypeDispatcher`.
    """
    method = getattr(intent, 'perform_effect', None)
    if method is not None:
        warnings.warn(
            "Intent %r has a deprecated perform_effect method." % (intent,),
            DeprecationWarning)
        return deferred_performer(lambda dispatcher, intent: method(dispatcher))


def deferred_performer(f):
    """
    A decorator for performers that return Deferreds.

    The wrapped function is expected to take a dispatcher and an intent (and
    not a box), and may return a Deferred. This decorator deals with putting
    the Deferred's result into the box.
    """
    def inner(dispatcher, intent, box):
        try:
            result = f(dispatcher, intent)
        except:
            box.fail(sys.exc_info())
        else:
            if isinstance(result, Deferred):
                deferred_to_box(result, box)
            else:
                box.succeed(result)
    return inner


@deferred_performer
def perform_parallel(dispatcher, parallel):
    """
    Perform a :obj:`ParallelEffects` intent by using Twisted's
        :func:`twisted.internet.defer.gatherResults`.
    """
    return gatherResults(
        map(partial(maybeDeferred, perform, dispatcher), parallel.effects))


def perform_delay(reactor, dispatcher, delay):
    """
    Perform a :obj:`Delay` with Twisted's
        :func:`twisted.internet.task.deferLater`.
    """
    return deferLater(reactor, delay.delay, lambda: None)


def perform(dispatcher, effect):
    """
    Perform an effect, returning a Deferred that will fire with the effect's
    ultimate result.
    """
    d = Deferred()
    eff = effect.on(
        success=d.callback,
        error=lambda e: d.errback(exc_info_to_failure(e)))
    base_perform(dispatcher, eff)
    return d


def exc_info_to_failure(exc_info):
    """Convert an exc_info tuple to a :class:`Failure`."""
    return Failure(exc_info[1], exc_info[0], exc_info[2])
