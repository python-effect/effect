from __future__ import absolute_import

from functools import partial
import sys

from testtools import TestCase
from testtools.matchers import MatchesListwise, Equals, MatchesException

from twisted.trial.unittest import SynchronousTestCase
from twisted.internet.defer import Deferred
from twisted.internet.task import Clock
from twisted.python.failure import Failure

from ._base import Effect
from ._intents import (
    Constant,
    Delay,
    base_dispatcher,
    parallel)
from ._dispatcher import ComposedDispatcher
from .twisted import (
    deferred_performer,
    exc_info_to_failure,
    make_twisted_dispatcher,
    perform)

from .test_base import func_dispatcher


def _dispatcher(reactor):
    return ComposedDispatcher([
        make_twisted_dispatcher(reactor),
        base_dispatcher
    ])


class TestCase(TestCase, SynchronousTestCase):

    skip = None  # horrible hack to make trial cooperate with testtools


class ParallelTests(TestCase):
    """Tests for :func:`parallel`."""
    def test_parallel(self):
        """
        'parallel' results in a list of results of the given effects, in the
        same order that they were passed to parallel.
        """
        d = perform(
            _dispatcher(None),
            parallel([Effect(Constant('a')),
                      Effect(Constant('b'))]))
        self.assertEqual(self.successResultOf(d), ['a', 'b'])


class DelayTests(TestCase):
    """Tests for :class:`Delay`."""

    def test_delay(self):
        """
        Delay intents will cause time to pass with reactor.callLater, and
        result in None.
        """
        clock = Clock()
        called = []
        eff = Effect(Delay(1)).on(called.append)
        perform(make_twisted_dispatcher(clock), eff)
        self.assertEqual(called, [])
        clock.advance(1)
        self.assertEqual(called, [None])


class TwistedPerformTests(TestCase):

    def test_perform(self):
        """
        effect.twisted.perform returns a Deferred which fires with the ultimate
        result of the Effect.
        """
        boxes = []
        e = Effect(boxes.append)
        d = perform(func_dispatcher, e)
        self.assertNoResult(d)
        boxes[0].succeed("foo")
        self.assertEqual(self.successResultOf(d), 'foo')

    def test_perform_failure(self):
        """
        effect.twisted.perform fails the Deferred it returns if the ultimate
        result of the Effect is an exception.
        """
        boxes = []
        e = Effect(boxes.append)
        d = perform(func_dispatcher, e)
        self.assertNoResult(d)
        boxes[0].fail((ValueError, ValueError("oh dear"), None))
        f = self.failureResultOf(d)
        self.assertEqual(f.type, ValueError)
        self.assertEqual(str(f.value), 'oh dear')


class DeferredPerformerTests(TestCase):
    """Tests for :func:`deferred_performer`."""

    def test_deferred_success(self):
        """
        @deferred_performer wraps a function taking the dispatcher and intent
        and hooks up its Deferred result to the box.
        """
        deferred = Deferred()
        eff = Effect('meaningless').on(success=lambda x: ('success', x))
        dispatcher = lambda i: deferred_performer(
            lambda dispatcher, intent: deferred)
        result = perform(dispatcher, eff)
        self.assertNoResult(result)
        deferred.callback("foo")
        self.assertEqual(self.successResultOf(result), ('success', 'foo'))

    def test_deferred_failure(self):
        """
        A failing Deferred causes error handlers to be called with an exception
        tuple based on the failure.
        """
        deferred = Deferred()
        eff = Effect('meaningless').on(error=lambda e: ('error', e))
        dispatcher = lambda i: deferred_performer(
            lambda dispatcher, intent: deferred)
        result = perform(dispatcher, eff)
        self.assertNoResult(result)
        deferred.errback(Failure(ValueError('foo')))
        self.assertThat(self.successResultOf(result),
                        MatchesListwise([
                            Equals('error'),
                            MatchesException(ValueError('foo'))]))

    def test_synchronous_success(self):
        """
        If ``deferred_performer`` wraps a function that returns a non-deferred,
        that result is the result of the effect.
        """
        dispatcher = lambda i: deferred_performer(
            lambda dispatcher, intent: "foo")
        result = perform(dispatcher, Effect("meaningless"))
        self.assertEqual(
            self.successResultOf(result),
            "foo")

    def test_synchronous_exception(self):
        """
        If ``deferred_performer`` wraps a function that raises an exception,
        the effect results in that exception.
        """
        def raise_():
            raise ValueError("foo")

        dispatcher = lambda i: deferred_performer(
            lambda dispatcher, intent: raise_())
        eff = Effect('meaningless').on(error=lambda e: ('error', e))
        result = perform(dispatcher, eff)
        self.assertThat(self.successResultOf(result),
                        MatchesListwise([
                            Equals('error'),
                            MatchesException(ValueError('foo'))]))

    def test_instance_method_performer(self):
        """The @deferred_performer decorator works on instance methods."""
        eff = Effect('meaningless')

        class PerformerContainer(object):
            @deferred_performer
            def performer(self, dispatcher, intent):
                return (self, dispatcher, intent)

        container = PerformerContainer()

        dispatcher = lambda i: container.performer
        result = self.successResultOf(perform(dispatcher, eff))
        self.assertEqual(result, (container, dispatcher, 'meaningless'))

    def test_promote_metadata(self):
        """
        The decorator copies metadata from the wrapped function onto the
        wrapper.
        """
        def original(dispatcher, intent):
            """Original!"""
            pass
        original.attr = 1
        wrapped = deferred_performer(original)
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
        wrapped = deferred_performer(new_func)
        self.assertEqual(wrapped.__name__, 'deferred_wrapper')


class ExcInfoToFailureTests(TestCase):
    """Tests for :func:`exc_info_to_failure`."""

    def test_exc_info_to_failure(self):
        """
        :func:`exc_info_to_failure` converts an exc_info tuple to a
        :obj:`Failure`.
        """
        try:
            raise RuntimeError("foo")
        except:
            exc_info = sys.exc_info()

        failure = exc_info_to_failure(exc_info)
        self.assertIs(failure.type, RuntimeError)
        self.assertEqual(str(failure.value), "foo")
        self.assertIs(failure.tb, exc_info[2])
