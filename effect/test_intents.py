from __future__ import print_function, absolute_import

from testtools import TestCase
from testtools.matchers import (
    Raises, MatchesStructure, MatchesException, Equals)

from ._base import Effect, perform
from ._sync import sync_perform
from ._dispatcher import TypeDispatcher, ComposedDispatcher

from ._intents import (
    Constant, perform_constant,
    Error, perform_error,
    Func, perform_func,
    ParallelEffects, perform_parallel, parallel, FirstError,
)


from .test_base import func_dispatcher


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

    def test_empty(self):
        """
        When given an empty list of effects, ``perform_parallel`` returns
        an empty list synchronusly.
        """
        result = sync_perform(
            TypeDispatcher({ParallelEffects: perform_parallel}),
            parallel([]))
        self.assertEqual(result, [])

    def test_parallel(self):
        """
        'parallel' results in a list of results of the given effects, in the
        same order that they were passed to parallel.
        """
        result = sync_perform(
            TypeDispatcher({ParallelEffects: perform_parallel,
                            Constant: perform_constant}),
            parallel([Effect(Constant('a')),
                      Effect(Constant('b'))]))
        self.assertEqual(result, ['a', 'b'])

    def test_error(self):
        """
        When given an effect that results in a Error, ``perform_parallel``
        result in ``FirstError``.
        """
        self.assertThat(
            lambda: sync_perform(
                TypeDispatcher({ParallelEffects: perform_parallel,
                                Error: perform_error}),
                parallel([Effect(Error(ValueError("foo")))])),
            Raises(
                MatchesException(
                    FirstError,
                    MatchesStructure(
                        failure=MatchesException(ValueError('foo')),
                        index=Equals(0)))))

    def test_out_of_order(self):
        result = []
        boxes = [None]*2
        eff = parallel([
            Effect(lambda box: boxes.__setitem__(0, box)),
            Effect(lambda box: boxes.__setitem__(1, box)),
            ])
        perform(
            ComposedDispatcher([
                TypeDispatcher({ParallelEffects: perform_parallel}),
                func_dispatcher]),
            eff.on(success=result.append, error=print))
        boxes[1].succeed('a')
        self.assertEqual(result, [])
        boxes[0].succeed('b')
        self.assertEqual(result[0], ['b', 'a'])
