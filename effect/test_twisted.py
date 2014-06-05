from __future__ import absolute_import

from twisted.trial.unittest import SynchronousTestCase

from . import Effect, parallel
from .twisted import perform
from .testing import StubIntent


class ParallelTests(SynchronousTestCase):
    """Tests for :func:`parallel`."""
    def test_parallel(self):
        """
        parallel results in a list of results of effects, in the same
        order that they were passed to parallel.
        """
        d = perform(
            parallel([Effect(StubIntent('a')),
                      Effect(StubIntent('b'))]))
        self.assertEqual(self.successResultOf(d), ['a', 'b'])

    # - handlers is passed through to child effects
    # - what happens with errors?


class TwistedPerformTests(SynchronousTestCase):
    def test_perform(self):
        e = Effect(StubIntent("foo"))
        d = perform(e)
        self.assertEqual(self.successResultOf(d), 'foo')
