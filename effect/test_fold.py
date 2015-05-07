
import operator

from effect import Constant, Effect, sync_perform
from effect.fold import fold_effect
from effect.testing import SequenceDispatcher


def test_fold_effect():
    effs = [Effect('a'), Effect('b'), Effect('c')]

    dispatcher = SequenceDispatcher([
        ('a', lambda i: 'Ei'),
        ('b', lambda i: 'Bee'),
        ('c', lambda i: 'Cee'),
    ])
    eff = fold_effect(operator.add, 'Nil', effs)

    with dispatcher.consume():
        result = sync_perform(dispatcher, eff)
    assert result == 'NilEiBeeCee'
