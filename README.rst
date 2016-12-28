Effect
======

.. image:: https://travis-ci.org/python-effect/effect.svg?branch=master
    :target: https://travis-ci.org/python-effect/effect

.. image:: https://img.shields.io/pypi/v/effect.svg
    :target: https://pypi.python.org/pypi/effect

Effect is a library for helping you write purely functional code by isolating
the effects (that is, IO or state manipulation) in your code. Documentation is
available at https://effect.readthedocs.org/, and its PyPI page is
https://pypi.python.org/pypi/effect.

It `supports`_ Python 2.7, 3.4 and 3.5 as well as PyPy.

.. _`supports`: https://travis-ci.org/python-effect/effect

You can install it by running ``pip install effect``.

.. image:: https://radix.github.io/effect/sigh-defects.png
    :target: https://twitter.com/extempore2/status/553597279463305218


What Is It?
===========

Effect lets you isolate your IO and state-manipulation code.

The benefits of this are many: first, the majority of your code can become
purely functional, leading to easier testing and ability to reason about
behavior. Also, because it separates the specification of an effect from the
performance of the effect, there are two more benefits: testing becomes easier
still, and it's easy to provide alternative implementations of effects.

Effect is somewhat similar to "algebraic effects", as implemented in various
typed functional programming languages. It also has similarities to Twisted's
Deferred objects.

Example
=======

A very quick example of using Effects:

.. code:: python

    from __future__ import print_function
    from effect import sync_perform, sync_performer, Effect, TypeDispatcher

    class ReadLine(object):
        def __init__(self, prompt):
            self.prompt = prompt

    def get_user_name():
        return Effect(ReadLine("Enter a candy> "))

    @sync_performer
    def perform_read_line(dispatcher, readline):
        return raw_input(readline.prompt)

    def main():
        effect = get_user_name()
        effect = effect.on(
            success=lambda result: print("I like {} too!".format(result)),
            error=lambda e: print("sorry, there was an error. {}".format(e)))

        dispatcher = TypeDispatcher({ReadLine: perform_read_line})
        sync_perform(dispatcher, effect)

    if __name__ == '__main__':
        main()


``Effect`` takes what we call an ``intent``, which is any object. The
``dispatcher`` argument to ``sync_perform`` must have a ``performer`` function
for your intent.

This has a number of advantages. First, your unit tests for ``get_user_name``
become simpler. You don't need to mock out or parameterize the ``raw_input``
function - you just call ``get_user_name`` and assert that it returns a ReadLine
object with the correct 'prompt' value.

Second, you can implement ReadLine in a number of different ways - it's
possible to override the way an intent is performed to do whatever you want.

For more information on how to implement the actual effect-performing code,
and other details, see the `documentation`_. There is also a full example
of interacting with the user and using an HTTP client to talk to the GitHub
API in the `effect-examples`_ repository.

.. _`documentation`: https://effect.readthedocs.org/
.. _`effect-examples`: https://github.com/python-effect/effect-examples



Videos
======

Some talks have been given about Effect.

- `Side Effects are a Public API`_ by Chris Armstrong at `Strange Loop`_ (2015-09-26)
- `Functionalish Programming in Python with Effect`_ by Robert Collins at `Kiwi PyCon`_ (2015-09-05)

.. _`Side Effects are a Public API`: https://www.youtube.com/watch?v=D37dc9EoFus
.. _`Strange Loop`: https://thestrangeloop.com/
.. _`Functionalish Programming in Python with Effect`: https://www.youtube.com/watch?v=fM5d_2BS6FY
.. _`Kiwi PyCon`: https://nzpug.org/


Thanks
======

Thanks to Rackspace for allowing me to work on this project, and having an
*excellent* `open source employee contribution policy`_

.. _`open source employee contribution policy`: https://www.rackspace.com/blog/rackspaces-policy-on-contributing-to-open-source/


Authors
=======

Effect was originally written by `Christopher Armstrong`_,
but now has contributions from the following people:

.. _`Christopher Armstrong`: https://github.com/radix

- `cyli`_
- `lvh`_
- `Manish Tomar`_
- `Tom Prince`_

.. _`cyli`: https://github.com/cyli
.. _`lvh`: https://github.com/lvh
.. _`Manish Tomar`: https://github.com/manishtomar
.. _`Tom Prince`: https://github.com/tomprince


IRC
===

There is a ``#python-effect`` IRC channel on irc.freenode.net.


See Also
========

For integrating Effect with Twisted's Deferreds, see the ``txEffect`` package
(`pypi`_, `github`_).

.. _`pypi`: https://warehouse.python.org/project/txeffect
.. _`github`: https://github.com/python-effect/txeffect

Over the past few years, the ecosystem of libraries to help with functional
programming in Python has exploded. Here are some libraries I recommend:

- `pyrsistent`_ - persistent (optimized immutable) data structures in Python
- `toolz`_ - a general library of pure FP functions
- `fn.py`_ - a Scala-inspired set of tools, including a weird lambda syntax, option type, and monads

.. _`pyrsistent`: https://pypi.python.org/pypi/pyrsistent/
.. _`toolz`: https://pypi.python.org/pypi/toolz
.. _`fn.py`: https://pypi.python.org/pypi/fn


License
=======

Effect is licensed under the MIT license:

Copyright (C) 2014 Christopher Armstrong

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
