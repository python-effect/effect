from __future__ import absolute_import

from functools import partial

from testtools import TestCase
from testtools.matchers import MatchesListwise, Equals, MatchesException

from twisted.trial.unittest import SynchronousTestCase
from twisted.internet.defer import succeed, fail
from twisted.internet.task import Clock

from . import Effect, parallel, ConstantIntent, Delay
from .twisted import perform, twisted_dispatcher
from .test_effect import SelfContainedIntent, ErrorIntent


class ParallelTests(SynchronousTestCase):
    """Tests for :func:`parallel`."""
    def test_parallel(self):
        """
        'parallel' results in a list of results of the given effects, in the
        same order that they were passed to parallel.
        """
        d = perform(
            None,
            parallel([Effect(ConstantIntent('a')),
                      Effect(ConstantIntent('b'))]))
        self.assertEqual(self.successResultOf(d), ['a', 'b'])


class DelayTests(SynchronousTestCase):
    """Tess for :class:`Delay`."""
    def test_delay(self):
        """
        Delay intents will cause time to pass with reactor.callLater, and
        result in None.
        """
        clock = Clock()
        called = []
        eff = Effect(Delay(1)).on(called.append)
        perform(clock, eff)
        self.assertEqual(called, [])
        clock.advance(1)
        self.assertEqual(called, [None])


class TwistedPerformTests(SynchronousTestCase, TestCase):

    skip = None  # Horrible hack to make testtools play with trial...

    def test_perform(self):
        """
        effect.twisted.perform returns a Deferred which fires with the ultimate
        result of the Effect.
        """
        e = Effect(ConstantIntent("foo"))
        d = perform(None, e)
        self.assertEqual(self.successResultOf(d), 'foo')

    def test_perform_failure(self):
        """
        effect.twisted.perform fails the Deferred it returns if the ultimate
        result of the Effect is an exception.
        """
        e = Effect(ErrorIntent())
        d = perform(None, e)
        f = self.failureResultOf(d)
        self.assertEqual(f.type, ValueError)
        self.assertEqual(str(f.value), 'oh dear')

    def test_dispatcher(self):
        """
        The twisted dispatcher passes the twisted dispatcher to the
        handle_effect methods, in case the effects need to run more effects.
        """
        e = Effect(SelfContainedIntent())
        d = perform("reactor", e)
        result = self.successResultOf(d)
        # this is hella white-box
        self.assertEqual(result[0], 'Self-result')
        self.assertIs(type(result[1]), partial)
        self.assertEqual(result[1].args, ('reactor',))
        self.assertEqual(result[1].func, twisted_dispatcher)

    def test_deferred_effect(self):
        """
        When an Effect handler returns a Deferred, the Deferred result is
        passed to the first effect callback.
        """
        d = succeed('foo')
        e = Effect(ConstantIntent(d)).on(success=lambda x: ('success', x))
        result = perform(None, e)
        self.assertEqual(self.successResultOf(result),
                         ('success', 'foo'))

    def test_failing_deferred_effect(self):
        """
        A failing Deferred returned from an effect causes error handlers to be
        called with an exception tuple based on the failure.
        """
        d = fail(ValueError('foo'))
        e = Effect(ConstantIntent(d)).on(error=lambda e: ('error', e))
        result = self.successResultOf(perform(None, e))
        self.assertThat(
            result,
            MatchesListwise([
                Equals('error'),
                MatchesException(ValueError('foo'))]))
        # The traceback element is None, because we constructed the failure
        # without a traceback.
        self.assertIs(result[1][2], None)
