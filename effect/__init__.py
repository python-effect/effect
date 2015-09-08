"""
A system for helping you separate your IO and state-manipulation code
(hereafter referred to as "effects") from everything else, thus allowing
the majority of your code to be easier to test and compose (that is,
have the general benefits of purely functional code).

See https://effect.readthedocs.org/ for documentation.
"""

from __future__ import absolute_import

from ._base import Effect, perform, NoPerformerFoundError, catch, raise_
from ._sync import (
    NotSynchronousError,
    sync_perform,
    sync_performer)
from ._intents import (
    Delay, perform_delay_with_sleep,
    ParallelEffects, parallel, parallel_all_errors, FirstError,
    Constant, Error, Func,
    base_dispatcher)
from ._dispatcher import ComposedDispatcher, TypeDispatcher


__all__ = [
    # Order here affects the order that these things show up in the API docs.
    "Effect", "sync_perform", "sync_performer",
    "base_dispatcher",
    "TypeDispatcher", "ComposedDispatcher",
    "Delay", "perform_delay_with_sleep",
    "ParallelEffects", "parallel", "parallel_all_errors",
    "Constant", "Error", "Func",
    "catch", "raise_",
    "NoPerformerFoundError", "NotSynchronousError", "perform",
    "FirstError",
]
