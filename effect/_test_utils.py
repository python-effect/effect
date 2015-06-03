"""Another sad little utility module."""

import sys
import traceback

import attr

from testtools.matchers import Equals


@attr.s
class ReraisedTracebackMismatch(object):
    expected_tb = attr.ib()
    got_tb = attr.ib()

    def describe(self):
        return ("The reference traceback:\n"
                + ''.join(self.expected_tb)
                + "\nshould match the tail end of the received traceback:\n"
                + ''.join(self.got_tb)
                + "\nbut it doesn't.")


@attr.s
class MatchesReraisedExcInfo(object):

    expected = attr.ib()

    def match(self, actual):
        valcheck = Equals(self.expected[1]).match(actual[1])
        if valcheck is not None:
            return valcheck
        typecheck = Equals(self.expected[0]).match(actual[0])
        if typecheck is not None:
            return typecheck
        expected = traceback.format_exception(*self.expected)
        new = traceback.format_exception(*actual)
        tail_equals = lambda a, b: a == b[-len(a):]
        if not tail_equals(expected[1:], new[1:]):
            return ReraisedTracebackMismatch(expected_tb=expected,
                                             got_tb=new)


def get_exc_info(exception):
    """Get an exc_info tuple based on an exception instance."""
    try:
        raise exception
    except:
        return sys.exc_info()


def raise_(e):
    """Raise an exception instance. Exists so you can raise in a lambda."""
    raise e
