from six.moves import input

from effect import sync_performer


class ReadLine(object):
    """An effect intent for getting input from the user."""

    def __init__(self, prompt):
        self.prompt = prompt


@sync_performer
def perform_readline_stdin(dispatcher, readline):
    """Perform a :obj:`ReadLine` intent by reading from stdin."""
    return input(readline.prompt)
