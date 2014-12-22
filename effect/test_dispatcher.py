from testtools import TestCase

from ._dispatcher import TypeDispatcher, ComposedDispatcher


class Foo(object):
    pass


class TypeDispatcherTests(TestCase):
    """Tests for :obj:`TypeDispatcher`."""

    def test_lookup(self):
        performer = object()
        td = TypeDispatcher({Foo: performer})
        self.assertIs(td(Foo()), performer)

    def test_not_found(self):
        td = TypeDispatcher({})
        self.assertIs(td(Foo()), None)


class ComposedDispatcherTests(TestCase):
    """Tests for :obj:`ComposedDispatcher`."""

    def test_lookup_first(self):
        performer = object()
        cd = ComposedDispatcher([lambda x: performer])
        self.assertIs(cd(Foo()), performer)

    def test_lookup_later(self):
        performer = object()
        cd = ComposedDispatcher([lambda x: None, lambda x: performer])
        self.assertIs(cd(Foo()), performer)

    def test_not_found(self):
        cd = ComposedDispatcher([lambda x: None, lambda x: None])
        self.assertIs(cd(Foo()), None)
