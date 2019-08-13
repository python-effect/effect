from toolz import curry
from functools import partial
from effect import Effect, sync_performer
from effect.do import do, do_return


def iterator_performer(xs=None):
    """
    Returns performers for isolating iterator among other effects.
    For exemplary usages one may look into tests.
    """
    xs = xs if xs is not None else []
    @sync_performer
    def performer(xs, dispatcher, intent):
        """Chains yielded values and stores them in continuation"""
        xs.append(intent)

    @sync_performer
    def retriever(xs, dispatcher, intent):
        """Provides retrieval of gathered values"""
        return xs

    return partial(performer, xs), partial(retriever, xs)


@curry
def iter_retriever(retrieval_type, f):
    """Appends retrieval of values from continuation at the end of function"""
    def perform(gen):
        for value in gen:
            yield value
        yield do_return(Effect(retrieval_type()))

    @curry
    def fixed_point(f, arg):
        f = f(arg)
        return (fixed_point if callable(f) else do(perform))(f)
    return fixed_point(f)


@curry
def iter_retriever__uncurried(retrieval_type, f):
    """Uncurried version of the above - much less generic!"""
    @do
    def wrapper(*args, **kwargs):
        for value in f(*args, **kwargs):
            yield value
        yield do_return(Effect(retrieval_type()))
    return wrapper
