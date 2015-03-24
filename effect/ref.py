from characteristic import attributes

from ._base import Effect
from ._dispatcher import TypeDispatcher
from ._sync import sync_performer


class Reference(object):
    """
    An effectful mutable variable, suitable for sharing between multiple
    logical threads of execution, that can be read and modified in a purely
    functional way.

    Compare to Haskell's ``IORef`` or Clojure's ``atom``.
    """

    # TODO: Add modify_atomic that either uses a lock or a low-level
    # compare-and-set operation.

    def __init__(self, initial):
        self._value = initial

    def read(self):
        """Return an Effect that results in the current value."""
        return Effect(ReadReference(ref=self))

    def modify(self, transformer):
        """
        Return an Effect that updates the value with ``fn(old_value)``.

        :param transformer: Function that takes old value and returns the new
            value.

        This is not guaranteed to be linearizable if multiple threads are
        modifying the reference at the same time. It is safe to assume
        consistent modification as long as you're not using multiple threads,
        though.
        """
        return Effect(ModifyReference(ref=self, transformer=transformer))

    def __repr__(self):
        return "<Reference({})>".format(self._value)


@attributes(['ref'])
class ReadReference(object):
    """Intent that gets a Reference's current value."""


@attributes(['ref', 'transformer'])
class ModifyReference(object):
    """
    Intent that modifies a Reference value in-place with a transformer func.

    This intent is not necessarily linearizable if multiple threads are
    modifying the same reference at the same time.
    """


@sync_performer
def perform_read_reference(dispatcher, intent):
    """Performer for :obj:`ReadReference`."""
    return intent.ref._value


@sync_performer
def perform_modify_reference(dispatcher, intent):
    """
    Performer for :obj:`ModifyReference`.

    This performer is not linearizable if multiple physical threads are
    modifying the same reference at the same time.
    """
    new_value = intent.transformer(intent.ref._value)
    intent.ref._value = new_value
    return new_value


reference_dispatcher = TypeDispatcher({
    ReadReference: perform_read_reference,
    ModifyReference: perform_modify_reference})
