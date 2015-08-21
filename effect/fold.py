import traceback
from functools import reduce

from effect import Constant, Effect


class FoldError(Exception):
    """
    Raised when one of the Effects passed to :func:`fold_effect` fails.

    :ivar accumulator: The data accumulated so far, before the failing Effect.
    :ivar wrapped_exception: The exc_info tuple representing the original
        exception raised by the failing Effect.
    """
    def __init__(self, accumulator, wrapped_exception):
        self.accumulator = accumulator
        self.wrapped_exception = wrapped_exception

    def __str__(self):
        tb_lines = traceback.format_exception(*self.wrapped_exception)
        tb = ''.join(tb_lines)
        st = (
            "<FoldError after accumulating %r> Original traceback follows:\n%s"
            % (self.accumulator, tb))
        return st.rstrip('\n')


def fold_effect(f, initial, effects):
    """
    Fold over the results of effects, left-to-right.

    This is like :func:`functools.reduce`, but instead of acting on plain
    values, it acts on the results of effects.

    The function ``f`` will be called with the accumulator (starting with
    ``initial``) and a result of an effect repeatedly for each effect. The
    result of the previous call will be passed as the accumulator to the next
    call.

    For example, the following code evaluates to an Effect of 6::

        fold_effect(operator.add, 0, [Effect(Constant(1)),
                                      Effect(Constant(2)),
                                      Effect(Constant(3))])

    If no elements were in the list, Effect would result in 0.

    :param callable f: function of ``(accumulator, element) -> accumulator``
    :param initial: The value to be passed as the accumulator to the first
        invocation of ``f``.
    :param effects: sequence of Effects.
    """

    def failed(acc, e):
        raise FoldError(acc, e)

    def folder(acc, element):
        return acc.on(lambda r: element.on(lambda r2: f(r, r2),
                                           error=lambda e: failed(r, e)))

    return reduce(folder, effects, Effect(Constant(initial)))


def sequence(effects):
    """
    Perform each Effect serially, collecting their results into a list.

    :raises: :obj:`FoldError` with the list accumulated so far when an effect
        fails.
    """
    # Could be: folder = lambda acc, el: acc + [el]
    # But, for peformance:
    l = []

    def folder(acc, el):
        l.append(el)
        return l
    return fold_effect(folder, l, effects)
