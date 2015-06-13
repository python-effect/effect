# This code only works in Python 3, so it's left out of test_do.py, to be
# optionally imported.

from effect import Constant, Effect
from effect.do import do


@do
def py3_generator_with_return():
    yield Effect(Constant(1))
    return 2  # noqa
