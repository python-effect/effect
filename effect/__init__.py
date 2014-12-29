"""
A system for helping you separate your IO and state-manipulation code
(hereafter referred to as "effects") from everything else, thus allowing
the majority of your code to be easier to test and compose (that is,
have the general benefits of purely functional code).


Here's a quick tour of the Effect library:

- Intent: An object which describes a desired action, ideally with simple
  inert data in public attributes. For example, ``ReadLine(prompt='> ')`` could
  be an intent that describes the desire to read a line from the user after
  showing a prompt.
- :obj:`Effect`: An object which binds callbacks to receive the result of
  performing an intent.
- Performer: A callable that takes the Dispatcher, an Intent, and a Box. It
  executes the Intent and puts the result in the Box. For example, the
  performer for ``ReadLine()`` could call ``raw_input(intent.prompt)``.
- Dispatcher: A callable that takes an Intent and finds the Performer that can
  execute it (or None). See :obj:`TypeDispatcher` and :obj:`ComposedDispatcher`
  for handy pre-built dispatchers.
- Box: An object that has ``succeed`` and ``fail`` methods for providing the
  result of an execution (potentially asynchronously). Usually you don't need
  to care about this, if you define your performers with
  :func:`effect.sync_performer` or :func:`effect.twisted.deferred_performer`.

There's a few main things you need to do to use Effect.

- Define some intents to describe your side-effects (or use a library
  containing intents that already exist). For example, an ``HTTPRequest``
  intent that has ``method``, ``url``, etc attributes.
- Write your application code to create effects like
  ``Effect(HTTPRequest(...))`` and attach callbacks to them with
  :func:`Effect.on`.
- As close as possible to the top-level of your application, perform your
  effect(s) with :func:`perform`.
- You will need to pass a dispatcher to :func:`perform`. You should create one
  by creating a :class:`TypeDispatcher` with your own performers (e.g. for
  ``HTTPRequest``), and composing it with :obj:`effect.base_dispatcher` (which
  has performers for built-in effects) using :class:`ComposedDispatcher`.
"""

from __future__ import absolute_import

from ._base import Effect, perform, NoPerformerFoundError
from ._sync import NotSynchronousError, sync_perform, sync_performer
from ._intents import (
    Delay, ParallelEffects, parallel,
    ConstantIntent, ErrorIntent, FuncIntent,
    base_dispatcher)
from ._dispatcher import ComposedDispatcher, TypeDispatcher


__all__ = [
    "Effect", "perform", "NoPerformerFoundError",
    "NotSynchronousError", "sync_perform", "sync_performer",
    "Delay", "ParallelEffects", "parallel",
    "ConstantIntent", "ErrorIntent", "FuncIntent",
    "base_dispatcher",
    "TypeDispatcher", "ComposedDispatcher",
]
