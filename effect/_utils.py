"""A sad little module."""


def wraps(original):
    """
    Return a decorator that updates the decorated function to look like the
    ``original`` function -- in name, documentation, module, and any other
    attributes found in __dict__.

    This is like :func:`functools.wraps`, except you can wrap non-functions
    without blowing up.
    """
    def wraps_decorator(wrapper):
        try:
            wrapper.__name__ = original.__name__
            wrapper.__doc__ = original.__doc__
            wrapper.__dict__.update(original.__dict__)
            wrapper.__module__ = original.__module__
        except:
            pass
        return wrapper
    return wraps_decorator
