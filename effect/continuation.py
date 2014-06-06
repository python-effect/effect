"""
An "asynchronous" trampoline.
"""


class Bouncer(object):
    work = None
    _asynchronous = False

    def bounce(self, func, *args, **kwargs):
        """
        Bounce a function off the trampoline -- in other words, signal to the
        trampoline that the given function should be run.

        If the calling trampoline has finished, the function will be run
        synchronously in a new trampoline.
        """
        if self.work is not None:
            raise RuntimeError(
                "Already specified work %r, refusing to set to (%r %r %r)"
                % (self.work, func, args, kwargs))
        if self._asynchronous:
            trampoline(func, *args, **kwargs)
            return
        self.work = (func, args, kwargs)


def trampoline(f, *args, **kwargs):
    """
    An asynchronous trampoline.

    Differences from a typical trampoline
    - return values disappear into the void. This is for intrinsically
      side-effecting operations.
    - To indicate more work to be done, call bouncer.bounce(f, *args, **kwargs)
    """
    while True:
        bouncer = Bouncer()
        f(bouncer, *args, **kwargs)
        if bouncer.work is not None:
            f, args, kwargs = bouncer.work
            continue
        else:
            bouncer._asynchronous = True
            return
