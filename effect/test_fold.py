
import operator

from effect import ComposedDispatcher, Effect, base_dispatcher, sync_perform
from effect.fold import fold_effect
from effect.testing import SequenceDispatcher


def test_fold_effect():
    """Behaves like foldM."""
    effs = [Effect('a'), Effect('b'), Effect('c')]

    dispatcher = SequenceDispatcher([
        ('a', lambda i: 'Ei'),
        ('b', lambda i: 'Bee'),
        ('c', lambda i: 'Cee'),
    ])
    eff = fold_effect(operator.add, 'Nil', effs)

    with dispatcher.consume():
        result = sync_perform(
            ComposedDispatcher([dispatcher, base_dispatcher]),
            eff)
    assert result == 'NilEiBeeCee'


def test_fold_effect_empty():
    """
    Returns an Effect resulting in the initial value when there are no effects.
    """
    eff = fold_effect(operator.add, 0, [])
    result = sync_perform(base_dispatcher, eff)
    assert result == 0
