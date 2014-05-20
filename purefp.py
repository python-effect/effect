"""
A system for helping you separate your IO and state manipulation code from
everything else, thus allowing the majority of your code to be trivially
testable and composable (that is, have the general benefits of purely
functional code).
"""

from __future__ import print_function

def schedule_iop_QBANG(iop, handlers):
    return handlers[type(iop)](iop, handlers)


def gather(iops):
    """
    Given multiple IOps, return one IOp that represents the aggregate of all of their IO.
    The result of the aggregate IOps will be a list of their results, in order of completion.
    """
    return


class Callback(object):
    """
    A representation of the fact that a call should be done after some IO is performed.
    """
    def __init__(self, iop, callback):
        self.iop = iop
        self.callback = callback


def schedule_callback_QBANG(callback, handlers):
    result = schedule_iop_QBANG(callback.iop, handlers)
    if hasattr(result, 'addCallback'):
        result.addCallback(callback.callback)
    else:
        callback.callback(result)


standard_handlers = {Callback: schedule_callback_QBANG}

