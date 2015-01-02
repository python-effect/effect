"""
Run this example with:
    python -m examples.github.twisted_main

This is an example of using Effect with Twisted.

It's important to note that none of the application code relies on Twisted --
this is the only file that has any dependencies on Twisted. There's also an
example of running the same application code in ``sync_main.py`` in the same
directory.

This code has these responsibilities:

- set up a dispatcher that knows how to find performers for all intents
  used in this application. The application uses ReadLine, HTTPRequest, and
  ParallelEffects.
- use :func:`effect.twisted.perform` to perform an effect, which returns a
  Deferred that we can return from our react function.
"""

from __future__ import print_function

from twisted.internet.task import react

from effect.twisted import make_twisted_dispatcher, perform
from effect import (
    ComposedDispatcher,
    TypeDispatcher)

from ..http.http_intent import HTTPRequest
from ..http.twisted_http import perform_request_with_treq
from ..readline_intent import ReadLine, perform_readline_stdin

from .core import main_effect


def get_dispatcher(reactor):
    """
    Create a dispatcher that can find performers for :obj:`ReadLine`,
    :obj:`HTTPRequest`, and :obj:`ParallelEffects`.
    :func:`make_twisted_dispatcher` is able to provide the ``ParallelEffects``
    performer, so we compose it with our own custom :obj:`TypeDispatcher`.
    """
    return ComposedDispatcher([
        TypeDispatcher({
            ReadLine: perform_readline_stdin,
            HTTPRequest: perform_request_with_treq,
        }),
        make_twisted_dispatcher(reactor),
    ])


def main(reactor):
    dispatcher = get_dispatcher(reactor)
    eff = main_effect()
    return perform(dispatcher, eff).addCallback(print)

if __name__ == '__main__':
    react(main, [])
