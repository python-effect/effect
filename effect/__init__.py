"""
A system for helping you separate your IO and state-manipulation code
(hereafter referred to as "effects") from everything else, thus allowing
the majority of your code to be easier to test and compose (that is,
have the general benefits of purely functional code).

See https://effect.readthedocs.org/ for documentation.
"""

from __future__ import absolute_import

from ._base import Effect, perform, NoPerformerFoundError, catch
from ._sync import (
    NotSynchronousError,
    sync_perform,
    sync_performer)
from ._intents import (
    Delay, ParallelEffects, parallel,
    Constant, Error, FirstError, Func,
    base_dispatcher)
from ._dispatcher import ComposedDispatcher, TypeDispatcher


__all__ = [
    "Effect", "perform", "NoPerformerFoundError",
    "NotSynchronousError", "sync_perform", "sync_performer",
    "Delay", "ParallelEffects", "parallel",
    "Constant", "Error", "FirstError", "Func",
    "base_dispatcher",
    "TypeDispatcher", "ComposedDispatcher",
    "catch",
]
