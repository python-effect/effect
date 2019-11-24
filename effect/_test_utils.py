"""Another sad little utility module."""

import traceback

import attr

from testtools.matchers import Equals, Mismatch


@attr.s
class ReraisedTracebackMismatch(object):
    expected_tb = attr.ib()
    got_tb = attr.ib()

    def describe(self):
        return (
            "The reference traceback:\n"
            + "".join(self.expected_tb)
            + "\nshould match the tail end of the received traceback:\n"
            + "".join(self.got_tb)
            + "\nbut it doesn't."
        )


@attr.s
class MatchesException(object):
    expected = attr.ib()

    def match(self, other):
        expected_type = type(self.expected)
        if type(other) is not expected_type:
            return Mismatch("{} is not a {}".format(other, expected_type))
        if other.args != self.expected.args:
            return Mismatch(
                "{} has different arguments: {}.".format(other.args, self.expected.args)
            )


@attr.s
class MatchesReraisedExcInfo(object):

    expected = attr.ib()

    def match(self, actual):
        valcheck = Equals(self.expected.args).match(actual.args)
        if valcheck is not None:
            return valcheck
        typecheck = Equals(type(self.expected)).match(type(actual))
        if typecheck is not None:
            return typecheck
        expected = list(
            traceback.TracebackException.from_exception(self.expected).format()
        )
        new = list(traceback.TracebackException.from_exception(actual).format())
        tail_equals = lambda a, b: a == b[-len(a) :]
        if not tail_equals(expected[1:], new[1:]):
            return ReraisedTracebackMismatch(expected_tb=expected, got_tb=new)


def raise_(e):
    """Raise an exception instance. Exists so you can raise in a lambda."""
    raise e
