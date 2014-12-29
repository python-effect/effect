"""An asynchronous trampoline."""


class Bouncer(object):
    work = None
    _asynchronous = False

    def bounce(self, func, *args, **kwargs):
        """
        Bounce a function off the trampoline -- in other words, signal to the
        trampoline that the given function should be run. It will be passed a
        new bouncer and the args and kwargs specified.

        If the calling trampoline has finished, the function will be run
        synchronously in a new trampoline.

        This method may only be called once, to enforce a tail-call style.
        """
        if self.work is not None:
            raise RuntimeError(
                "Already specified work %r, refusing to set to (%r %r %r)"
                % (self.work, func, args, kwargs))
        self.work = (func, args, kwargs)
        if self._asynchronous:
            trampoline(func, *args, **kwargs)
            return


def trampoline(f, *args, **kwargs):
    """
    An asynchronous trampoline.

    Calls f with a new Bouncer, and *args and **kwargs.

    The Bouncer can have its :function:`Bouncer.bounce` method called with
    another function to call. If the bounce method is called with a new
    function by the time that 'f' returns, then the function passed
    will be called immediately.

    If the function returns without calling bounce, then the trampoline
    returns.

    The interesting difference from a typical trampoline, however, is that the
    bounce method can be called *after* f returns -- in other words, the
    bounce method can be called asynchronously, assuming it stashes the bouncer
    object away somewhere, and something else triggers a call to it. Of course,
    by then this trampoline will no longer be running. In that case,
    :func:`Bouncer.bounce` will immediately start up another trampoline and
    call the passed function.

    Given this asynchronous nature, return values of functions disappear into
    the void. This trampoline is for intrinsically side-effecting operations.
    """
    while True:
        bouncer = Bouncer()
        f(bouncer, *args, **kwargs)
        if bouncer.work is not None:
            f, args, kwargs = bouncer.work
        else:
            bouncer._asynchronous = True
            return
