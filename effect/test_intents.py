from __future__ import print_function, absolute_import

from functools import partial

import six

from testtools import TestCase
from testtools.matchers import (
    Equals, MatchesListwise,
    Raises, MatchesException,
    MatchesStructure,
)

from ._base import Effect
from ._dispatcher import ComposedDispatcher, TypeDispatcher
from ._intents import (
    base_dispatcher,
    Constant, perform_constant,
    Error, perform_error,
    Func, perform_func,
    FirstError,
    ParallelEffects, parallel_all_errors,
    Sequence, SequenceFailed)
from ._sync import sync_perform
from ._test_utils import MatchesReraisedExcInfo, get_exc_info
from .async import perform_parallel_async
from .test_parallel_performers import EquitableException


class IntentTests(TestCase):
    """Tests for intents."""

    def test_perform_constant(self):
        """
        perform_constant returns the result of a Constant.
        """
        intent = Constant("foo")
        result = sync_perform(
            TypeDispatcher({Constant: perform_constant}),
            Effect(intent))
        self.assertEqual(result, "foo")

    def test_perform_error(self):
        """
        perform_error raises the exception of a Error.
        """
        intent = Error(ValueError("foo"))
        self.assertRaises(
            ValueError,
            lambda: sync_perform(
                TypeDispatcher({Error: perform_error}),
                Effect(intent)))

    def test_perform_func(self):
        """
        perform_func calls the function given in a Func.
        """
        intent = Func(lambda: "foo")
        result = sync_perform(
            TypeDispatcher({Func: perform_func}),
            Effect(intent))
        self.assertEqual(result, "foo")


class ParallelTests(TestCase):
    """Tests for :func:`parallel`."""

    def test_first_error_str(self):
        """FirstErrors have a pleasing format."""
        fe = FirstError(exc_info=(ValueError, ValueError('foo'), None),
                        index=150)
        self.assertEqual(
            str(fe),
            '(index=150) ValueError: foo')


class ParallelAllErrorsTests(TestCase):
    """Tests for :func:`parallel_all_errors`."""

    def test_parallel_all_errors(self):
        """
        Exceptions raised from child effects get turned into (True, exc_info)
        results.
        """
        exc_info1 = get_exc_info(EquitableException(message='foo'))
        reraise1 = partial(six.reraise, *exc_info1)
        exc_info2 = get_exc_info(EquitableException(message='bar'))
        reraise2 = partial(six.reraise, *exc_info2)

        dispatcher = ComposedDispatcher([
            TypeDispatcher({
                ParallelEffects: perform_parallel_async,
            }),
            base_dispatcher])
        es = [Effect(Func(reraise1)),
              Effect(Constant(1)),
              Effect(Func(reraise2))]
        eff = parallel_all_errors(es)
        self.assertThat(
            sync_perform(dispatcher, eff),
            MatchesListwise([
                MatchesListwise([Equals(True),
                                 MatchesReraisedExcInfo(exc_info1)]),
                Equals((False, 1)),
                MatchesListwise([Equals(True),
                                 MatchesReraisedExcInfo(exc_info2)]),
            ]))


class SequenceTests(TestCase):
    """
    Tests for :class:`Sequence`.
    """

    def test_no_effects(self):
        intent = Sequence([])
        result = sync_perform(base_dispatcher, Effect(intent))
        self.assertEqual(result, [])

    def test_single_effect(self):
        """
        When :class:`Sequence` is given a single effect, the result
        is  a list with the result of that effect.
        """
        intent = Sequence([Effect(Constant("foo"))])
        result = sync_perform(base_dispatcher, Effect(intent))
        self.assertEqual(result, ["foo"])

    def test_two_effect(self):
        """
        When :class:`Sequence` is given a sequence of effects, the result
        is the result is the list of results of those effects in order.
        """
        intent = Sequence([Effect(Constant("foo")), Effect(Constant("bar"))])
        result = sync_perform(base_dispatcher, Effect(intent))
        self.assertEqual(result, ["foo", "bar"])

    def test_error(self):
        """
        When an effect given to :class:`Sequence` fails, the effect raises
        :exception:`SequenceFailed` with the results of the preceding effects,
        and the triggering error.
        """
        intent = Sequence([Effect(Constant("foo")),
                           Effect(Error(ValueError("bar")))])
        self.assertThat(
            lambda: sync_perform(base_dispatcher, Effect(intent)),
            Raises(MatchesException(
                SequenceFailed,
                MatchesStructure(
                    results=Equals(["foo"]),
                    exc_info=MatchesException(ValueError, value_re="bar")))))
