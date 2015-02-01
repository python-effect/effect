from __future__ import print_function

import sys
from functools import partial

from characteristic import attributes

import six

from testtools.testcase import TestCase
from testtools.matchers import Equals, MatchesStructure

from ._base import Effect, perform
from ._dispatcher import ComposedDispatcher, TypeDispatcher
from ._intents import (
    Constant, FirstError, Func, ParallelEffects, base_dispatcher,
    parallel)
from ._sync import sync_perform
from .async import perform_parallel_async
from .test_base import func_dispatcher
from ._test_utils import MatchesReraisedExcInfo


@attributes(['message'])
class EquitableException(Exception):
    pass


def get_exc_info(exception):
    try:
        raise exception
    except:
        return sys.exc_info()


class PerformParallelAsyncTests(TestCase):

    def setUp(self):
        super(PerformParallelAsyncTests, self).setUp()
        self.dispatcher = ComposedDispatcher([
            base_dispatcher,
            TypeDispatcher({ParallelEffects: perform_parallel_async})])

    def test_empty(self):
        """
        When given an empty list of effects, ``perform_parallel_async`` returns
        an empty list synchronusly.
        """
        result = sync_perform(
            self.dispatcher,
            parallel([]))
        self.assertEqual(result, [])

    def test_parallel(self):
        """
        'parallel' results in a list of results of the given effects, in the
        same order that they were passed to parallel.
        """
        result = sync_perform(
            self.dispatcher,
            parallel([Effect(Constant('a')),
                      Effect(Constant('b'))]))
        self.assertEqual(result, ['a', 'b'])

    def test_error(self):
        """
        When given an effect that results in a Error,
        ``perform_parallel_async`` result in ``FirstError``.
        """
        expected_exc_info = get_exc_info(EquitableException(message='foo'))
        reraise = partial(six.reraise, *expected_exc_info)
        try:
            sync_perform(
                self.dispatcher,
                parallel([Effect(Func(reraise))]))
        except FirstError as fe:
            self.assertThat(
                fe,
                MatchesStructure(
                    index=Equals(0),
                    exc_info=MatchesReraisedExcInfo(expected_exc_info)))
        else:
            self.fail("sync_perform should have raised FirstError.")

    def test_error_index(self):
        """
        The ``index`` of a :obj:`FirstError` is the index of the effect that
        failed in the list.
        """
        expected_exc_info = get_exc_info(EquitableException(message='foo'))
        reraise = partial(six.reraise, *expected_exc_info)
        try:
            sync_perform(
                self.dispatcher,
                parallel([
                    Effect(Constant(1)),
                    Effect(Func(reraise)),
                    Effect(Constant(2))]))
        except FirstError as fe:
            self.assertThat(
                fe,
                MatchesStructure(
                    index=Equals(1),
                    exc_info=MatchesReraisedExcInfo(expected_exc_info)))

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
