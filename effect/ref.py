from characteristic import attributes

from ._base import Effect
from ._dispatcher import TypeDispatcher
from ._sync import sync_performer


class ERef(object):
    """
    An effectful mutable variable, suitable for sharing between multiple
    logical threads of execution, that can be read and modified in a purely
    functional way.

    Compare to Haskell's ``IORef`` or Clojure's ``atom``.
    """

    def __init__(self, initial):
        self._value = initial

    def read(self):
        """Return an Effect that results in the current value."""
        return Effect(ReadERef(eref=self))

    def modify(self, transformer):
        """
        Return an Effect that updates the value with ``fn(old_value)``.
        """
        return Effect(ModifyERef(eref=self, transformer=transformer))


@attributes(['eref'])
class ReadERef(object):
    """Intent that gets an ERef value."""


@attributes(['eref', 'transformer'])
class ModifyERef(object):
    """Intent that modifies an ERef value in-place with a transformer func."""


@sync_performer
def perform_read_eref(dispatcher, intent):
    """Performer for :obj:`ReadERef`."""
    return intent.eref._value


@sync_performer
def perform_modify_eref(dispatcher, intent):
    """
    Performer for :obj:`ModifyERef`.

    Note that while :obj:`ModifyERef` is designed to allow strong consistency,
    this performer is _not_ threadsafe, in the sense that it's possible to
    overwrite unobserved values. This may change in the future.
    """
    new_value = intent.transformer(intent.eref._value)
    intent.eref._value = new_value
    return new_value


eref_dispatcher = TypeDispatcher({ReadERef: perform_read_eref,
                                  ModifyERef: perform_modify_eref})
