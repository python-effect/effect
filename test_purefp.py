from __future__ import print_function

from unittest import TestCase

from purefp import IO


class PureTests(TestCase):
    def test_perform_io_method_dispatch(self):
        """perform_io invokes a method on the IOp."""
        io = IO(SelfContainedIO())
        self.assertEqual(io.perform_io({}), "Self-result")

    def test_perform_io_registry_dispatch(self):
        """perform_io invokes a function from the handler registry."""
        def handle_io(iop, handlers):
            return "dispatched"
        io = IO(POPOIO())
        self.assertEqual(
            io.perform_io({POPOIO: handle_io}),
            "dispatched")

    def test_callback(self):
        """
        Callbacks can wrap IOs, will be passed the IO's result, and are
        able to return a new value.
        """
        io = IO(SelfContainedIO())
        io = io.on_success(lambda x: x + ": amended!")
        self.assertEqual(
            io.perform_io({}),
            "Self-result: amended!")

    def test_callback_chain(self):
        """
        Callbacks can be wrapped in more callbacks.
        """
        io = IO(SelfContainedIO())
        io = io.on_success(lambda x: x + ": amended!")
        io = io.on_success(lambda x: x + " Again!")
        self.assertEqual(
            io.perform_io({}),
            "Self-result: amended! Again!")


class SelfContainedIO(object):
    """An example IO object which implements its own perform_io."""

    def perform_io(self, handlers):
        return "Self-result"

class POPOIO(object):
    """An example IO object which doesn't implement its own perform_io."""




# tests:
# - basic "after"
# - basic "on"
# - callbacks returning instances of IO
# - gather
# - Deferred support (I think this is broken but not sure).
