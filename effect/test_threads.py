from multiprocessing.pool import ThreadPool

from functools import partial

from testtools import TestCase
from testtools.matchers import raises

from . import Effect, base_dispatcher
from ._dispatcher import ComposedDispatcher, TypeDispatcher
from ._intents import Constant, Error, ParallelEffects, FirstError, parallel
from ._sync import sync_perform
from .threads import perform_parallel_with_pool
from .test_intents import EquibleException


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
        peff = parallel([Effect(Constant(1)),
                          Effect(Error(EquibleException(message="foo")))])
        self.assertThat(
            lambda: sync_perform(self.dispatcher, peff),
            raises(FirstError(exception=EquibleException(message='foo'),
                              index=1)))
