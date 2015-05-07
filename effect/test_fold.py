
import operator

from pytest import raises

from effect import (
    ComposedDispatcher, Effect, Error,
    base_dispatcher, sync_perform)
from effect.fold import FoldError, fold_effect
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


def test_fold_effect_errors():
    """
    When one of the effects in the folding list fails, a FoldError is raised
    with the accumulator so far.
    """
    effs = [Effect('a'), Effect(Error(ZeroDivisionError('foo'))), Effect('c')]

    dispatcher = SequenceDispatcher([
        ('a', lambda i: 'Ei'),
    ])

    eff = fold_effect(operator.add, 'Nil', effs)

    with dispatcher.consume():
        with raises(FoldError) as excinfo:
            sync_perform(_disp(dispatcher), eff)
    assert excinfo.value.accumulator == 'NilEi'
    assert excinfo.value.wrapped_exception[0] is ZeroDivisionError
    assert str(excinfo.value.wrapped_exception[1]) == 'foo'
