from testtools import TestCase

from ._base import Effect
from ._sync import sync_perform
from .ref import (
    ERef, ModifyERef, ReadERef,
    eref_dispatcher)


class ERefTests(TestCase):
    """Tests for :obj:`ERef`."""

    def test_read(self):
        """``read`` returns an Effect that represents the current value."""
        ref = ERef('initial')
        self.assertEqual(ref.read(), Effect(ReadERef(eref=ref)))

    def test_modify(self):
        """``modify`` returns an Effect that represents modification."""
        ref = ERef(0)
        transformer = lambda x: x + 1
        eff = ref.modify(transformer)
        self.assertEqual(eff,
                         Effect(ModifyERef(eref=ref, transformer=transformer)))

    def test_perform_read(self):
        """Performing the reading results in the current value."""
        ref = ERef('initial')
        result = sync_perform(eref_dispatcher, ref.read())
        self.assertEqual(result, 'initial')

    def test_perform_modify(self):
        """
        Performing the modification results in transforming the current value,
        and also returns the new value.
        """
        ref = ERef(0)
        transformer = lambda x: x + 1
        result = sync_perform(eref_dispatcher, ref.modify(transformer))
        self.assertEqual(result, 1)
        self.assertEqual(sync_perform(eref_dispatcher, ref.read()), 1)
