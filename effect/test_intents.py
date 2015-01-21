from __future__ import print_function, absolute_import

from characteristic import attributes

from testtools import TestCase
from testtools.matchers import raises

from ._base import Effect, perform
from ._sync import sync_perform
from ._dispatcher import TypeDispatcher, ComposedDispatcher

from ._intents import (
    Constant, perform_constant,
    Error, perform_error,
    Func, perform_func,
    ParallelEffects, perform_parallel_async, parallel, FirstError,
)


from .test_base import func_dispatcher


@attributes(['message'])
class EquibleException(Exception):
    pass


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
        When given an empty list of effects, ``perform_parallel_async`` returns
        an empty list synchronusly.
        """
        result = sync_perform(
            TypeDispatcher({ParallelEffects: perform_parallel_async}),
            parallel([]))
        self.assertEqual(result, [])

    def test_parallel(self):
        """
        'parallel' results in a list of results of the given effects, in the
        same order that they were passed to parallel.
        """
        result = sync_perform(
            TypeDispatcher({ParallelEffects: perform_parallel_async,
                            Constant: perform_constant}),
            parallel([Effect(Constant('a')),
                      Effect(Constant('b'))]))
        self.assertEqual(result, ['a', 'b'])

    def test_error(self):
        """
        When given an effect that results in a Error, ``perform_parallel_async``
        result in ``FirstError``.
        """
        self.assertThat(
            lambda: sync_perform(
                TypeDispatcher({ParallelEffects: perform_parallel_async,
                                Error: perform_error}),
                parallel([Effect(Error(EquibleException(message="foo")))])),
            raises(FirstError(exception=EquibleException(message='foo'),
                              index=0)))

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
                func_dispatcher]),
            eff.on(success=result.append, error=print))
        boxes[1].succeed('a')
        self.assertEqual(result, [])
        boxes[0].succeed('b')
        self.assertEqual(result[0], ['b', 'a'])

    def test_first_error_str(self):
        """FirstErrors have a pleasing format."""
        fe = FirstError(exception=ValueError('foo'), index=150)
        self.assertEqual(
            str(fe),
            '(index=150) ValueError: foo')
