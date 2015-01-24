from multiprocessing.pool import ThreadPool

from functools import partial

from testtools import TestCase

from . import Effect, base_dispatcher
from ._dispatcher import ComposedDispatcher, TypeDispatcher
from ._intents import Constant, Error, ParallelEffects, FirstError, parallel
from ._sync import sync_perform
from .threads import perform_parallel_with_pool
from .test_async import EquitableException


class ParallelPoolPerformerTests(TestCase):

    def setUp(self):
        super(ParallelPoolPerformerTests, self).setUp()
        self.pool = ThreadPool()
        p_performer = partial(perform_parallel_with_pool, self.pool)
        self.dispatcher = ComposedDispatcher([
            base_dispatcher,
            TypeDispatcher({ParallelEffects: p_performer})])

    def test_real_threads(self):
        peff = parallel([Effect(Constant(1)), Effect(Constant(2))])
        self.assertEqual(sync_perform(self.dispatcher, peff), [1, 2])

    def test_error(self):
        """
        When given an effect that results in a Error, :obj:`FirstError` is
        raised.
        """
        try:
            sync_perform(
                self.dispatcher,
                parallel([Effect(Error(EquitableException(message="foo")))]))
        except FirstError as fe:
            self.assertEqual(
                fe,
                FirstError(exception=EquitableException(message='foo'),
                           index=0))

    def test_error_index(self):
        """
        The ``index`` of a :obj:`FirstError` is the index of the effect that
        failed in the list.
        """
        try:
            sync_perform(
                self.dispatcher,
                parallel([
                    Effect(Constant(1)),
                    Effect(Error(EquitableException(message="foo"))),
                    Effect(Constant(2))]))
        except FirstError as fe:
            self.assertEqual(
                fe,
                FirstError(exception=EquitableException(message='foo'),
                           index=1))
