from six.moves import input

from effect import sync_performer


class ReadLine(object):
    """An effect intent for getting input from the user."""

    def __init__(self, prompt):
        self.prompt = prompt


@sync_performer
def stdin_read_line(dispatcher, readline):
    """Perform a :obj:`ReadLine` intent by reading from STDIN."""
    return input(readline.prompt)

