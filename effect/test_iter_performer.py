import typing as t
import unittest
from toolz import curry
from effect.do import do
from effect import (Effect, sync_perform, sync_performer, TypeDispatcher,
                    ComposedDispatcher, base_dispatcher)
from .iter_performer import (iterator_performer, iter_retriever,
                             iter_retriever__uncurried)


Value = t.NamedTuple('Value', [('text', str)])
RetrieveValues = t.NamedTuple('RetrieveValues', [])
LaunchRockets = t.NamedTuple('LaunchRockets', [])


@sync_performer
def launch_rockets_performer(dispatcher, intent):
    # I don't really do that
    pass


def get_iter_dispatcher():
    iter_performer, iter_retriever = iterator_performer([])
    return ComposedDispatcher([
        TypeDispatcher({
            Value: iter_performer,
            RetrieveValues: iter_retriever,
            LaunchRockets: launch_rockets_performer,
        }),
        base_dispatcher,
    ])


value_retriever = iter_retriever(RetrieveValues)


def sync_perform_iter(e: Effect):
    return sync_perform(get_iter_dispatcher(), e)


class IteratorPerformerTestCase(unittest.TestCase):
    def setUp(self):
        self.values_list = [
            Value('be like'),
            Value('water'),
            Value('my friend'),
        ]

    def test_iterator_performer(self):
        @do
        def f(x):
            yield Effect(self.values_list[0])
            yield Effect(self.values_list[1])
            yield Effect(self.values_list[2])
            return Effect(RetrieveValues())
        effect = f(42)
        yielded_values = list(sync_perform_iter(effect))
        self.assertEqual(self.values_list, yielded_values)

    def test_iter_decorator(self):
        @value_retriever
        def f(x):
            yield Effect(self.values_list[0])
            yield Effect(self.values_list[1])
            yield Effect(self.values_list[2])
        effect = f(42)
        yielded_values = list(sync_perform_iter(effect))
        self.assertEqual(self.values_list, yielded_values)

    def test_iter_decorator__curried(self):
        @value_retriever
        @curry
        def f(x, y, z):
            yield Effect(self.values_list[0])
            yield Effect(self.values_list[1])
            yield Effect(self.values_list[2])
        effect = f("x")("y")("z")
        yielded_values = list(sync_perform_iter(effect))
        self.assertEqual(self.values_list, yielded_values)

    def test_iter_decorator__uncurried(self):
        @iter_retriever__uncurried(RetrieveValues)
        def f(x, y, z):
            yield Effect(self.values_list[0])
            yield Effect(self.values_list[1])
            yield Effect(self.values_list[2])
        effect = f("x", "y", "z")
        yielded_values = list(sync_perform_iter(effect))
        self.assertEqual(self.values_list, yielded_values)

    def test_iter_decorator__other_effects(self):
        @value_retriever
        def f(x):
            yield Effect(LaunchRockets())
            yield Effect(self.values_list[0])
            yield Effect(self.values_list[1])
            yield Effect(LaunchRockets())
            yield Effect(self.values_list[2])
        effect = f(42)
        yielded_values = list(sync_perform_iter(effect))
        self.assertEqual(self.values_list, yielded_values)
