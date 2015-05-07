
import operator

from effect import ComposedDispatcher, Effect, base_dispatcher, sync_perform
from effect.fold import fold_effect, sequence
from effect.testing import SequenceDispatcher


def _disp(dispatcher):
    return ComposedDispatcher([dispatcher, base_dispatcher])

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
        result = sync_perform(_disp(dispatcher), eff)
    assert result == 'NilEiBeeCee'


def test_fold_effect_empty():
    """
    Returns an Effect resulting in the initial value when there are no effects.
    """
    eff = fold_effect(operator.add, 0, [])
    result = sync_perform(base_dispatcher, eff)
    assert result == 0


def test_sequence():
    """Collects each Effectful result into a list."""
    effs = [Effect('a'), Effect('b'), Effect('c')]
    dispatcher = SequenceDispatcher([
        ('a', lambda i: 'Ei'),
        ('b', lambda i: 'Bee'),
        ('c', lambda i: 'Cee'),
    ])
    eff = sequence(effs)

    print "what the heck is sequence returning?", eff
    with dispatcher.consume():
        result = sync_perform(_disp(dispatcher), eff)
    assert result == ['Ei', 'Bee', 'Cee']


def test_sequence_empty():
    """Returns an empty list when there are no Effects."""
    assert sync_perform(base_dispatcher, sequence([])) == []
