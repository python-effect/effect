"""
An "asynchronous" CPS trampoline.
"""


class Continuation(object):
    work = None
    finished = False

    def done(self):
        if self.finished:
            raise RuntimeError(
                "Can't call done again, it's already been called.")
        self.finished = True

    def more(self, func, *args, **kwargs):
        if self.work is not None:
            raise RuntimeError(
                "Already specified work %r, refusing to set to (%r %r %r)"
                % (self.work, func, args, kwargs))
        self.work = (func, args, kwargs)


def trampoline(f, *args, **kwargs):
    """
    An asynchronous trampoline.

    Differences from a typical trampoline
    - the continuation is an object with methods, not just a function you can
      call.
    - return values are unconditionally ignored
    - you must register additional functions to "recurse" to with
      continuation.work(f, *args, **kwargs)
    - 'f' will be called with the continuation as the first argument, followed
      by *args and **kwargs
    - both normal results and exceptions are handled (TBD)
    """
    while True:
        continuation = Continuation()
        f(continuation, *args, **kwargs)
        if continuation.work is not None:
            f, args, kwargs = continuation.work
            continue
        if continuation.finished:
            return

        continuation.more = lambda f, *args, **kwargs: trampoline(
            f, *args, **kwargs)
        return
