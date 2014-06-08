from __future__ import absolute_import

from twisted.trial.unittest import SynchronousTestCase

from . import Effect, parallel
from .twisted import perform, twisted_dispatcher
from .testing import StubIntent
from .test_effect import SelfContainedIntent, ErrorIntent


class ParallelTests(SynchronousTestCase):
    """Tests for :func:`parallel`."""
    def test_parallel(self):
        """
        'parallel' results in a list of results of the given effects, in the
        same order that they were passed to parallel.
        """
        d = perform(
            parallel([Effect(StubIntent('a')),
                      Effect(StubIntent('b'))]))
        self.assertEqual(self.successResultOf(d), ['a', 'b'])


class TwistedPerformTests(SynchronousTestCase):
    def test_perform(self):
        """
        effect.twisted.perform returns a Deferred which fires with the ultimate
        result of the Effect.
        """
        e = Effect(StubIntent("foo"))
        d = perform(e)
        self.assertEqual(self.successResultOf(d), 'foo')

    def test_perform_failure(self):
        """
        effect.twisted.perform fails the Deferred it returns if the ultimate
        result of the Effect is an exception.
        """
        e = Effect(ErrorIntent())
        d = perform(e)
        f = self.failureResultOf(d)
        self.assertEqual(f.type, ValueError)
        self.assertEqual(str(f.value), 'oh dear')

    def test_dispatcher(self):
        """
        The twisted dispatcher passes the twisted dispatcher to the
        handle_effect methods, in case the effects need to run more effects.
        """
        e = Effect(SelfContainedIntent())
        d = perform(e)
        self.assertEqual(self.successResultOf(d),
                         ('Self-result', twisted_dispatcher))
