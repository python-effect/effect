from __future__ import print_function

from functools import partial

from multiprocessing.pool import ThreadPool

from testtools import TestCase

from ._intents import ParallelEffects, base_dispatcher
from ._dispatcher import ComposedDispatcher, TypeDispatcher
from .threads import perform_parallel_with_pool
from .test_parallel_performers import ParallelPerformerTestsMixin


class ParallelPoolPerformerTests(TestCase, ParallelPerformerTestsMixin):
    """Tests for :func:`perform_parallel_with_pool`."""

    def setUp(self):
        super(ParallelPoolPerformerTests, self).setUp()
        self.pool = ThreadPool()
        self.p_performer = partial(perform_parallel_with_pool, self.pool)
        self.dispatcher = ComposedDispatcher([
            base_dispatcher,
            TypeDispatcher({ParallelEffects: self.p_performer})])
