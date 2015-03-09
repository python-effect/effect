from testtools import TestCase

from ._base import Effect
from ._sync import sync_perform
from .ref import (
    Reference, ModifyReference, ReadReference,
    reference_dispatcher)


class ReferenceTests(TestCase):
    """Tests for :obj:`Reference`."""

    def test_read(self):
        """``read`` returns an Effect that represents the current value."""
        ref = Reference('initial')
        self.assertEqual(ref.read(), Effect(ReadReference(ref=ref)))

    def test_modify(self):
        """``modify`` returns an Effect that represents modification."""
        ref = Reference(0)
        transformer = lambda x: x + 1
        eff = ref.modify(transformer)
        self.assertEqual(eff,
                         Effect(ModifyReference(ref=ref,
                                                transformer=transformer)))

    def test_perform_read(self):
        """Performing the reading results in the current value."""
        ref = Reference('initial')
        result = sync_perform(reference_dispatcher, ref.read())
        self.assertEqual(result, 'initial')

    def test_perform_modify(self):
        """
        Performing the modification results in transforming the current value,
        and also returns the new value.
        """
        ref = Reference(0)
        transformer = lambda x: x + 1
        result = sync_perform(reference_dispatcher, ref.modify(transformer))
        self.assertEqual(result, 1)
        self.assertEqual(sync_perform(reference_dispatcher, ref.read()), 1)
