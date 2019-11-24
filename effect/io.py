"""Intents and performers for basic user interaction.

Use :obj:`effect.io.stdio_dispatcher` as a dispatcher for :obj:`Display` and
:obj:`Prompt` that uses built-in Python standard io facilities.
"""

import attr

from . import sync_performer, TypeDispatcher


@attr.s
class Display(object):
    """Display some text to the user."""

    output = attr.ib()


@attr.s
class Prompt(object):
    """Get some input from the user, with a prompt."""

    prompt = attr.ib()


@sync_performer
def perform_display_print(dispatcher, intent):
    """Perform a :obj:`Display` intent by printing the output."""
    print(intent.output)


@sync_performer
def perform_get_input_raw_input(dispatcher, intent):
    """
    Perform a :obj:`Prompt` intent by using ``input``.
    """
    return input(intent.prompt)


stdio_dispatcher = TypeDispatcher(
    {Display: perform_display_print, Prompt: perform_get_input_raw_input}
)
