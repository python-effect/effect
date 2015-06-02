"""
Dispatcher!
"""

import attr

from six.moves import filter


@attr.s
class TypeDispatcher(object):
    """
    An Effect dispatcher which looks up the performer to use by type.

    :param mapping: mapping of intent type to performer
    """
    mapping = attr.ib()

    def __call__(self, intent):
        return self.mapping.get(type(intent))


@attr.s
class ComposedDispatcher(object):
    """
    A dispatcher which composes other dispatchers.

    The dispatchers given will be searched in order until a performer is found.

    :param dispatchers: Dispatchers to search.
    """

    dispatchers = attr.ib()

    def __call__(self, intent):
        return next(filter(None, (d(intent) for d in self.dispatchers)), None)
