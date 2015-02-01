from __future__ import print_function

from testtools.testcase import TestCase

from ._base import Effect, perform
from ._dispatcher import ComposedDispatcher, TypeDispatcher
from ._intents import ParallelEffects, base_dispatcher, parallel
from .async import perform_parallel_async
from .test_base import func_dispatcher
from .test_parallel_performers import ParallelPerformerTestsMixin


class PerformParallelAsyncTests(TestCase, ParallelPerformerTestsMixin):
    """Tests for :func:`perform_parallel_async`."""

    def setUp(self):
        super(PerformParallelAsyncTests, self).setUp()
        self.dispatcher = ComposedDispatcher([
            base_dispatcher,
            TypeDispatcher({ParallelEffects: perform_parallel_async})])

    def test_out_of_order(self):
        """
        The result order corresponds to the order of the effects as passed to
        :obj:`ParallelEffects` even when the results become available in a
        different order.
        """
        result = []
        boxes = [None] * 2
        eff = parallel([
            Effect(lambda box: boxes.__setitem__(0, box)),
            Effect(lambda box: boxes.__setitem__(1, box)),
        ])
        perform(
            ComposedDispatcher([
                TypeDispatcher({ParallelEffects: perform_parallel_async}),
                func_dispatcher,
            ]),
            eff.on(success=result.append, error=print))
        boxes[1].succeed('a')
        self.assertEqual(result, [])
        boxes[0].succeed('b')
        self.assertEqual(result[0], ['b', 'a'])
