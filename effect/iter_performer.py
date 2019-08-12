from toolz import curry
from itertools import chain
from effect import Effect, sync_performer
from effect.do import do


def iterator_performer(xs=None):
    """
    Returns performers for isolating iterator among other effects.
    For exemplary usages one may look into tests.
    """
    xs = xs if xs is not None else []
    @sync_performer
    def performer(dispatcher, intent):
        """Chains yielded values and stores them in continuation"""
        nonlocal xs
        xs = chain(xs, [intent])

    @sync_performer
    def retriever(dispatcher, intent):
        """Provides retrieval of gathered values"""
        nonlocal xs
        return xs

    return performer, retriever


@curry
def iter_retriever(retrieval_type, f):
    """Appends retrieval of values from continuation at the end of function"""
    @curry
    def aux(f, arg):
        f = f(arg)
        if callable(f):
            return aux(f)

        def perform():
            yield from f
            return Effect(retrieval_type())
        return do(perform)()
    return aux(f)


@curry
def iter_retriever__uncurried(retrieval_type, f):
    """Uncurried version of the above - much less generic!"""
    @do
    def wrapper(*args, **kwargs):
        yield from f(*args, **kwargs)
        return Effect(retrieval_type())
    return wrapper
