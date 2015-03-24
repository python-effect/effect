"""
Various functions for testing effects.

The main goal of this code is to allow you to safely tests your effects
in a way that makes it hard to *accidentally* perform real effects in your
tests.
"""

from __future__ import print_function

from functools import partial
import sys

from characteristic import attributes

from ._base import Effect, guard, _Box, NoPerformerFoundError
from ._sync import NotSynchronousError, sync_performer
from ._intents import Constant, Error, Func, ParallelEffects

import six


@attributes(['intent'], apply_with_init=False)
class Stub(object):
    """
    An intent which wraps another intent, to flag that the intent should
    be automatically resolved by :func:`resolve_stub`.

    :class:`Stub` is intentionally not performable by any default
    mechanism.
    """

    def __init__(self, intent):
        """
        :param intent: The intent to perform with :func:`resolve_stub`.
        """
        self.intent = intent


def ESConstant(x):
    """Return Effect(Stub(Constant(x)))"""
    return Effect(Stub(Constant(x)))


def ESError(x):
    """Return Effect(Stub(Error(x)))"""
    return Effect(Stub(Error(x)))


def ESFunc(x):
    """Return Effect(Stub(Func(x)))"""
    return Effect(Stub(Func(x)))


def resolve_effect(effect, result, is_error=False):
    """
    Supply a result for an effect, allowing its callbacks to run.

    The return value of the last callback is returned, unless any callback
    returns another Effect, in which case an Effect representing that
    operation plus the remaining callbacks will be returned.

    This allows you to test your code in a somewhat "channel"-oriented
    way:

        eff = do_thing()
        next_eff = resolve_effect(eff, first_result)
        next_eff = resolve_effect(next_eff, second_result)
        result = resolve_effect(next_eff, third_result)

    Equivalently, if you don't care about intermediate results::

        result = resolve_effect(
            resolve_effect(
                resolve_effect(
                    do_thing(),
                    first_result),
                second_result),
            third_result)

    NOTE: parallel effects have no special support. They can be resolved with
    a sequence, and if they're returned from another effect's callback they
    will be returned just like any other effect.
    """
    for i, (callback, errback) in enumerate(effect.callbacks):
        cb = errback if is_error else callback
        if cb is None:
            continue
        is_error, result = guard(cb, result)
        if type(result) is Effect:
            return Effect(
                result.intent,
                callbacks=result.callbacks + effect.callbacks[i + 1:])
    if is_error:
        six.reraise(*result)
    return result


def fail_effect(effect, exception):
    """
    Resolve an effect with an exception, so its error handler will be run.
    """
    try:
        raise exception
    except:
        return resolve_effect(effect, sys.exc_info(), is_error=True)


def resolve_stub(dispatcher, effect):
    """
    Automatically perform an effect, if its intent is a :obj:`Stub`.

    Note that resolve_stubs is preferred to this function, since it handles
    chains of stub effects.
    """
    if type(effect.intent) is Stub:
        performer = dispatcher(effect.intent.intent)
        if performer is None:
            raise NoPerformerFoundError(effect.intent.intent)
        result_slot = []
        box = _Box(result_slot.append)
        performer(dispatcher, effect.intent.intent, box)
        if len(result_slot) == 0:
            raise NotSynchronousError(
                "Performer %r was not synchronous during stub resolution for "
                "effect %r"
                % (performer, effect))
        if len(result_slot) > 1:
            raise RuntimeError(
                "Pathological error (too many box results) while running "
                "performer %r for effect %r"
                % (performer, effect))
        return resolve_effect(effect, result_slot[0][1],
                              is_error=result_slot[0][0])
    else:
        raise TypeError("resolve_stub can only resolve stubs, not %r"
                        % (effect,))


def resolve_stubs(dispatcher, effect):
    """
    Successively performs effects with resolve_stub until a non-Effect value,
    or an Effect with a non-stub intent is returned, and return that value.

    Parallel effects are supported by recursively invoking resolve_stubs on
    the child effects, if all of their children are stubs.
    """
    if type(effect) is not Effect:
        raise TypeError("effect must be Effect: %r" % (effect,))

    while type(effect) is Effect:
        if type(effect.intent) is Stub:
            effect = resolve_stub(dispatcher, effect)
        elif type(effect.intent) is ParallelEffects:
            if not all(isinstance(x.intent, Stub)
                       for x in effect.intent.effects):
                break
            else:
                effect = resolve_effect(
                    effect,
                    list(map(partial(resolve_stubs, dispatcher),
                             effect.intent.effects)))
        else:
            break

    return effect


class EQDispatcher(object):
    """
    An equality-based (constant) dispatcher.

    This dispatcher looks up intents by equality and performs them by returning
    an associated constant value.

    Users provide a mapping of intents to results, where the intents are
    matched against the intents being performed with a simple equality check
    (not a type check!).

    The mapping must be provided as a sequence of two-tuples. We don't use a
    dict because we don't want to require that the intents be hashable (in
    practice a lot of them aren't, and it's a pain to require it). If you want
    to construct your mapping as a dict, you can, just pass in the result of
    ``d.items()``.

    e.g.::

        >>> sync_perform(EQDispatcher([(MyIntent(1, 2), 'the-result')]),
        ...              Effect(MyIntent(1, 2)))
        'the-result'

    assuming MyIntent supports ``__eq__`` by value.
    """
    def __init__(self, mapping):
        """
        :param list mapping: A sequence of tuples of (intent, result).
        """
        self.mapping = mapping

    def __call__(self, intent):
        # Avoid hashing, because a lot of intents aren't hashable.
        for k, v in self.mapping:
            if k == intent:
                return sync_performer(lambda d, i: v)


class EQFDispatcher(object):
    """
    An Equality-based function dispatcher.

    This dispatcher looks up intents by equality and performs them by invoking
    an associated function.

    Users provide a mapping of intents to functions, where the intents are
    matched against the intents being performed with a simple equality check
    (not a type check!). The functions in the mapping will be passed only the
    intent and are expected to return the result or raise an exception.

    The mapping must be provided as a sequence of two-tuples. We don't use a
    dict because we don't want to require that the intents be hashable (in
    practice a lot of them aren't, and it's a pain to require it). If you want
    to construct your mapping as a dict, you can, just pass in the result of
    ``d.items()``.

    e.g.::

        >>> sync_perform(
        ...     EQFDispatcher([(
        ...         MyIntent(1, 2), lambda i: 'the-result')]),
        ...     Effect(MyIntent(1, 2)))
        'the-result'

    assuming MyIntent supports ``__eq__`` by value.
    """
    def __init__(self, mapping):
        """
        :param list mapping: A sequence of two-tuples of (intent, function).
        """
        self.mapping = mapping

    def __call__(self, intent):
        # Avoid hashing, because a lot of intents aren't hashable.
        for k, v in self.mapping:
            if k == intent:
                return sync_performer(lambda d, i: v(i))


class SequenceDispatcher(object):
    """
    A dispatcher which steps through a sequence of (intent, func) tuples and
    runs ``func`` to perform intents in strict sequence.

    So, if you expect to first perform an intent like ``MyIntent('a')`` and
    then an intent like ``OtherIntent('b')``, you can create a dispatcher like
    this::

        SequenceDispatcher([
            (MyIntent('a'), lambda i: 'my-intent-result'),
            (OtherIntent('b'), lambda i: 'other-intent-result')
        ])

    :obj:`None` is returned if the next intent in the sequence is not equal to
    the intent being performed, or if there are no more items left in the
    sequence.
    """
    def __init__(self, sequence):
        """:param list sequence: Sequence of (intent, fn)."""
        self.sequence = sequence

    def __call__(self, intent):
        if len(self.sequence) == 0:
            return
        exp_intent, func = self.sequence[0]
        if intent == exp_intent:
            self.sequence = self.sequence[1:]
            return sync_performer(lambda d, i: func(i))
