# Effect Examples

## http

The "http" directory contains a very simple HTTPRequest intent and performers
using common HTTP client libraries:
[requests](http://warehouse.python.org/project/requests/) and
[treq](https://warehouse.python.org/project/treq/).


## readline_intent

The "readline_intent.py" file has a simple ReadLine intent that uses raw_input
(or 'input' in Py3) to prompt the user for input.

## github

The "github" directory contains a simple application that lets the user input a
GitHub username, and prints out a list of all repositories that that user has
access to. It depends on the "http" and "readline_intent" modules.

There are two entrypoints into the example: examples.github.sync_main and
examples.github.twisted_main. sync_main does typical blocking IO, and
twisted_main uses asynchronous IO. Note that the vast majority of the code
doesn't need to care about this difference; the only part that cares about it
is the *_main.py files. All of the logic in core.py is generic. Tests are in
test_core.py.

To run them:

    python -m examples.github.sync_main

or

    python -m examples.github.twisted_main


Note that the twisted example does not run on Python 3, but all other examples
do.