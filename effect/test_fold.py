
import operator

from pytest import raises

from effect import Effect, Error, base_dispatcher, sync_perform
from effect.fold import FoldError, fold_effect, sequence
from effect.testing import perform_sequence


def test_fold_effect():
    """
    :func:`fold_effect` folds the given function over the results of the
    effects.
    """
    effs = [Effect('a'), Effect('b'), Effect('c')]

    dispatcher = [
        ('a', lambda i: 'Ei'),
        ('b', lambda i: 'Bee'),
        ('c', lambda i: 'Cee'),
    ]
    eff = fold_effect(operator.add, 'Nil', effs)
    result = perform_sequence(dispatcher, eff)
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

    dispatcher = [('a', lambda i: 'Ei')]

    eff = fold_effect(operator.add, 'Nil', effs)

    with raises(FoldError) as excinfo:
        perform_sequence(dispatcher, eff)
    assert excinfo.value.accumulator == 'NilEi'
    assert excinfo.value.wrapped_exception[0] is ZeroDivisionError
    assert str(excinfo.value.wrapped_exception[1]) == 'foo'


def test_fold_effect_str():
    """str()ing a FoldError returns useful traceback/exception info."""
    effs = [Effect('a'), Effect(Error(ZeroDivisionError('foo'))), Effect('c')]
    dispatcher = [('a', lambda i: 'Ei')]

    eff = fold_effect(operator.add, 'Nil', effs)
    with raises(FoldError) as excinfo:
        perform_sequence(dispatcher, eff)
    assert str(excinfo.value).startswith(
        "<FoldError after accumulating 'NilEi'> Original traceback follows:\n")
    assert str(excinfo.value).endswith('ZeroDivisionError: foo')


def test_sequence():
    """Collects each Effectful result into a list."""
    effs = [Effect('a'), Effect('b'), Effect('c')]
    dispatcher = [
        ('a', lambda i: 'Ei'),
        ('b', lambda i: 'Bee'),
        ('c', lambda i: 'Cee'),
    ]
    eff = sequence(effs)

    result = perform_sequence(dispatcher, eff)
    assert result == ['Ei', 'Bee', 'Cee']


def test_sequence_empty():
    """Returns an empty list when there are no Effects."""
    assert sync_perform(base_dispatcher, sequence([])) == []


def test_sequence_error():
    """
    Allows :obj:`FoldError` to be raised when an Effect fails. The list
    accumulated so far is the `accumulator` value in the :obj:`FoldError`.
    """
    effs = [Effect('a'), Effect(Error(ZeroDivisionError('foo'))), Effect('c')]

    dispatcher = [('a', lambda i: 'Ei')]

    eff = sequence(effs)

    with raises(FoldError) as excinfo:
        perform_sequence(dispatcher, eff)
    assert excinfo.value.accumulator == ['Ei']
    assert excinfo.value.wrapped_exception[0] is ZeroDivisionError
    assert str(excinfo.value.wrapped_exception[1]) == 'foo'
