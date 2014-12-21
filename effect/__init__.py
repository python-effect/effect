"""
A system for helping you separate your IO and state-manipulation code
(hereafter referred to as "effects") from everything else, thus allowing
the majority of your code to be trivially testable and composable (that is,
have the general benefits of purely functional code).

TODO: an effect implementation of ParallelEffects that uses threads?
TODO: an effect implementation of ParallelEffects that is actually serial,
      as a fallback?
TODO: integration with other asynchronous libraries like asyncio, trollius,
      eventlet

Tour:

- :obj:`Effect`: An object which wraps an Intent and specifies callbacks to be
  run.
- Intent: An object which specifies some action to perform.
- Dispatcher: A callable that takes an Intent and finds the Performer that can
  execute it (or None).
- Performer: A callable that takes the dispatcher and a Box. It executes the
  Intent and puts the result in the Box.
- Box: An object that has 'succeed' and 'fail' methods for providing the result
  of an execution (potentially asynchronously).
"""

from __future__ import absolute_import

from ._base import Effect, perform, NoPerformerFoundError
from ._sync import NotSynchronousError, sync_perform, sync_performer
from ._intents import (
    Delay, ParallelEffects, parallel,
    ConstantIntent, ErrorIntent, FuncIntent,
    base_dispatcher)

__all__ = [
    "Effect", "perform", "NoPerformerFoundError",
    "NotSynchronousError", "sync_perform", "sync_performer",
    "Delay", "ParallelEffects", "parallel",
    "ConstantIntent", "ErrorIntent", "FuncIntent",
    "base_dispatcher",
]
