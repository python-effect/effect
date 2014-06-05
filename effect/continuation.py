"""
An implementation of a CPS (Continuation-Passing Style) trampoline in Python.

Note that this is more interesting than the typical examples of trampolines.
Most trampolines are strictly synchronous; if you haven't called the
continuation* by the time your function completes, the typical trampoline will
uselessly return the continuation. In other words, it only works for purely
functional, synchronous systems.

* or returned the thunk that the trampoline should immediately invoke.

This trampoline has the property that the calls to the continuation
need not be synchronous. Your CPS functions can tuck the continuation
away somewhere, in some little pocket of state, and invoke it later, and
the trampoline will then pick up from there. Of course, if your CPS
function *does* invoke the continuation synchronously, the stack is
rewound so that we don't recurse -- that's the whole point of the
trampoline.

Of course, this means that the trampoline cannot meaningfully return
a value synchronously. If you need access to the final value produced
by your chain of CPS functions, you must make sure to pass in a
continuation that will do whatever you want with it.
"""


class Continuation(object):
    work = None
    finished = False
    def __init__(self, done):
        self._done = done

    def done(self, result):
        if self.finished:
            raise RuntimeError("You can't call done again, it's already been called. new result: %r" % (result,))
        self.finished = True
        self._done(result)

    def more(self, func, *args, **kwargs):
        if self.work is not None:
            raise RuntimeError("You can't specify more work to do, it's already been specified. %r %r %r" % (func, args, kwargs))
        self.work = (func, args, kwargs)


def trampoline(callback, f, *args, **kwargs):
    """
    An asynchronous trampoline.

    Differences from a typical trampoline[1]
    - the continuation is an object with methods, not just a function you can
      call.
    - return values are unconditionally ignored
    - you must register additional functions to "recurse" to with
      continuation.work(f, *args, **kwargs)
    - 'f' will be called with the continuation as the first argument, followed
      by *args and **kwargs
    - both normal results and exceptions are handled (TBD)

    [1] see (http://jtauber.com/blog/2008/03/30/thunks,_trampolines_and_continuation_passing/)
    """
    while True:
        continuation = Continuation(callback)
        f(continuation, *args, **kwargs)
        if continuation.work is not None:
            print "SYNC work", continuation.work
            f, args, kwargs = continuation.work
            continue
        if continuation.finished:
            print "finished!"
            return
        print "ohh! asynchronous!"
        def more(f, *args, **kwargs):
            print "ASYNC work", f, args, kwargs
            trampoline(callback, f, *args, **kwargs)
        continuation.more = more
        return


def rrange(continuation, n, counter=0, l=()):
    if len(l) == n:
        continuation.done(l)
    else:
        continuation.more(rrange, n, counter=counter + 1, l=l + (counter,))

print
print "=== basic ==="
l = []
trampoline(l.append, rrange, 10)
print l

print
print "=== asynchronous *done* ==="
conts = []
def async_bullshit(continuation):
    conts.append(continuation)

l = []
trampoline(l.append, async_bullshit)
print "pre-done", l
conts[0].done('lol')
print "post-done", l

print
print "=== asynchronous *more* ==="
conts = []
l = []
trampoline(l.append, async_bullshit)
print 'pre-more', l
conts[0].more(lambda cont: cont.more(lambda cont: cont.more(lambda cont: cont.done('hey'))))
print 'post-more'
print l


print "=== callbacks! ==="
def run_callbacks(chain, result):
    if not chain:
        return result
    return run_callbacks(chain[1:], chain[0](result))

print 'recursive', run_callbacks([lambda thing: ('one', thing),
                     lambda thing: ('two', thing),
                     lambda thing: ('three', thing)],
                   'initial result')

def run_callbacks(continuation, chain, result):
    if not chain:
        continuation.done(result)
        return
    continuation.more(run_callbacks, chain[1:], chain[0](result))

l = []
trampoline(l.append,
           run_callbacks,
           [lambda thing: ('one', thing),
            lambda thing: ('two', thing),
            lambda thing: ('three', thing)],
           'initial result'
          )
print 'cps', l
