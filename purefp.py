"""
A system for helping you separate your IO and state manipulation code from
everything else, thus allowing the majority of your code to be trivially
testable and composable (that is, have the general benefits of purely
functional code).

Keywords: monad, IO, state, stateless.

The core behavior is as follows:
- IO operations should be represented as instances of IO.
- These IOs wrap a plain-old Python object; this library has no expectation
  of them whatsoever[1].
- In most cases where you'd perform IO or state manipulation in your code,
  you should instead return an IO wrapping an object that describes
  everything necessary to perform that IO.
- Separately, some function should exist that takes an IO-wrapped object and
  performs the actual IO or state manipulation.
- To represent work to be done *after* an IO, use IO.on_success, .on_error,
  etc.
- Near the top level of your code, invoke perform_io on the IO you have
  produced. This will invoke the IO-performing handlers for the IO,
  and successively invoke the callbacks associated with them.
- If the callbacks return another instance of IO, that IO will be performed
  before continuing back down the callback chain.

[1] Actually, as a convenience, perform_io can be implemented as a method on
    the wrapped object, but the implementation can also be specified in a
    separate handlers table.

On top of the implemented behaviors, there are some conventions that these
behaviors synergize with:

- Don't do any state manipulation or IO in your functions that produce an
  IO. This kinda goes without saying, but at the same time, it's ok to
  break the rules. If you do IO/state in your IO-producing functions, the
  benefit of producing IOs is usually lost. However, there are a few cases
  where you may decide to compromise:
  - most commonly, logging.
  - generation of random numbers.
- IO-wrapped objects should be *inert* and *transparent*. That is, they should
  be unchanging data structures that fully describe the behavior to be
  performed with public members. This serves two purposes:
  - First, and most importantly, it makes unit-testing your code trivial.
    No longer will you need to use mocks or stubs to fake out parts of your
    system for the majority of your tests. The tests will simply invoke the
    function, inspect the IO-wrapped object for correctness, and manually
    invoke any callbacks in order to test the post-IO behavior. No need to
    actually perform state manipulation or IO in your unit tests.
  - This allows the IO-code to be *small* and *replaceable*. Using these
    conventions, it's trivial to switch out the implementation of e.g. your
    HTTP client, and even to use either a blocking or non-blocking
    interface, or to configure a threading policy.

In fact, Twisted is supported out of the box: any IO implementations that
return Deferreds will work seamlessly with ``Callback`` and related wrappers.
Other asynchronous frameworks can be trivially added.
"""

from __future__ import print_function

import sys
from functools import partial


class NoIOHandlerError(Exception):
    """No IO Handler could be found for the given IO-wrapped object."""


class IO(object):
    """
    Wrap an object that describes how to do IO, and offer facilities for
    actually performing that IO.

    (You're an object-oriented programmer.
     You probably want to subclass this.
     Don't.)
    """
    def __init__(self, popo):
        self.popo = popo

    def perform_io(self, handlers):
        """
        :param handlers: A dictionary mapping types of IO-wrapped objects to
        handler functions.

        Perform any IO or state manipulation necessary to execute an IO. If
        the type of the wrapped object is in ``handlers``, that handler will be
        invoked.

        Otherwise a ``perform_io`` method will be invoked on the wrapped object.
        """
        func = None
        if type(self.popo) in handlers:
            func = partial(handlers[type(self.popo)], self.popo)
        if func is None:
            func = getattr(self.popo, 'perform_io', None)
        if func is None:
            raise NoIOHandlerError(self.popo)
        result = func(handlers)
        if type(result) is IO:
            return result.perform_io(result)
        return result

    def on_success(self, callback):
        """
        Return a new IO that will invoke the associated callback when this
        IO completes succesfully.
        """
        return IO(Callback(self, callback))

    def on_error(self, callback):
        """
        Return a new IO that will invoke the associated callback when this
        IO fails.
        """
        return IO(Errback(self, callback))

    def after(self, callback):
        """
        Return a new IO that will invoke the associated callback when this
        IO completes, whether successfully or in error.
        """
        return IO(After(self, callback))

    def on(self, success, error):
        """
        Return a new IO that will invoke either the success or error callbacks
        provided based on whether this IO completes sucessfully or in error.
        """



def gather(ios):
    """
    Given multiple IOs, return one IO that represents the aggregate of all of their IO.
    The result of the aggregate IOps will be a list of their results, in order of completion.
    """
    return


class Callback(object):
    """
    A representation of the fact that a call should be made after some IO is performed.

    Hint: This is kinda like bind (>>=).
    """
    def __init__(self, io, callback):
        self.io = io
        self.callback = callback

    def perform_io(self, handlers):
        result = self.io.perform_io(handlers)
        if hasattr(result, 'addCallback'):
            result.addCallback(self.callback)
        else:
            return self.callback(result)


class Errback(object):
    """
    A representation of the fact that a call should be made after some IO fails.
    """
    def __init__(self, io, callback):
        self.io = io
        self.callback = callback

    def perform_io(self, handlers):
        try:
            result = perform_io(self.io, handlers)
            if hasattr(result, 'addErrback'):
                result.addErrback(self.callback)
            else:
                self.callback(result)
        except:
            self.callback(sys.exc_info())


class After(object):
    """
    A representation of the fact that a call should be made after some IO is
    performed, whether it succeeds or fails.
    """
    def __init__(self, io, callback):
        self.io = io
        self.callback = callback

    def perform_io(self, handlers):
        try:
            result = perform_io(self.io, handlers)
            if hasattr(result, 'addBoth'):
                result.addErrback(self.callback)
            else:
                self.callback(result)
        except:
            self.callback(sys.exc_info())
