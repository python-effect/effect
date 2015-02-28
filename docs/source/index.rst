.. Effect documentation master file, created by
   sphinx-quickstart on Mon Dec 22 12:01:30 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Effect
======
Effect is a library for helping you write purely functional code by
isolating the effects (that is, IO or state manipulation) in your code.


API
===

Effect comes with thorough API documentation.

.. toctree::
   :maxdepth: 2

   api/modules



Explanation by Example
======================

Effect starts with a very simple idea: instead of having a function which
performs side-effects (such as IO):

.. code:: python

    def get_user_name():
        return raw_input("Enter User Name> ")

you instead have a function which *returns* a representation of the
side-effect:

.. code:: python

    def get_user_name():
        return Effect(ReadLine("Enter User Name> "))

We call objects like ``ReadLine`` an *intent* -- that is, the *intent* of this
effect is to read a line of input from the user. Ideally, intents are very
simple objects with public attributes and no behavior, only data.

.. code:: python

    class ReadLine(object):
	def __init__(self, prompt):
	    self.prompt = prompt

To perform the ReadLine intent, we must implement a performer function:

.. code:: python

    @sync_performer
    def perform_read_line(dispatcher, readline):
	return raw_input(readline.prompt)


To do something with the result of the effect, we must attach callbacks with
the ``on`` method:

.. code:: python

    def greet():
        return get_user_name().on(
            success=lambda r: Effect(Print("Hello,", r)),
	    error=lambda exc_info: Effect(Print("There was an error!", exc_info[1])))


(Here we assume another intent, ``Print``, which shows some text to the user.)

A (sometimes) nicer syntax is provided for adding callbacks, with the
:func:`effect.do.do` decorator.

.. code:: python

    from effect.do import do

    @do
    def greet():
        try:
            name = yield get_user_name()
        except Exception as e:
            yield Effect(Print("There was an error!", e))
        else:
            yield Effect(Print("Hello,", name))

Finally, to actually perform these effects, they can be passed to
:func:`effect.perform`, along with a dispatcher which looks up the performer
based on the intent.

.. code:: python

    def main():
        eff = greet()
	dispatcher = TypeDispatcher({ReadLine: perform_read_line})
        perform(dispatcher, effect)

This has a number of advantages. First, your unit tests for ``get_user_name``
become simpler. You don't need to mock out or parameterize the ``raw_input``
function - you just call ``get_user_name`` and assert that it returns a
``ReadLine`` object with the correct 'prompt' value.

Second, you can implement ``ReadLine`` in a number of different ways - it's
possible to override the way an intent is performed to do whatever you want.
For example, you could implement an HTTPRequest client either using the popular
``requests`` package by Kenneth Reitz, or using the Twisted-based ``treq``
package from David Reid -- without needing to change any of your application
code, since it's all in terms of the Effect API.


A quick tour, with definitions
==============================

- Intent: An object which describes a desired action, ideally with simple
  inert data in public attributes. For example, ``ReadLine(prompt='> ')`` could
  be an intent that describes the desire to read a line from the user after
  showing a prompt.
- :obj:`effect.Effect`: An object which binds callbacks to receive the result
  of performing an intent.
- Performer: A callable that takes the Dispatcher, an Intent, and a Box. It
  executes the Intent and puts the result in the Box. For example, the
  performer for ``ReadLine()`` could call ``raw_input(intent.prompt)``.
- Dispatcher: A callable that takes an Intent and finds the Performer that can
  execute it (or None). See :obj:`TypeDispatcher` and :obj:`ComposedDispatcher`
  for handy pre-built dispatchers.
- Box: An object that has ``succeed`` and ``fail`` methods for providing the
  result of an effect (potentially asynchronously). Usually you don't need
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
  effect(s) with :func:`effect.perform`.
- You will need to pass a dispatcher to :func:`effect.perform`. You should create one
  by creating a :class:`effect.TypeDispatcher` with your own performers (e.g. for
  ``HTTPRequest``), and composing it with :obj:`effect.base_dispatcher` (which
  has performers for built-in effects) using :class:`effect.ComposedDispatcher`.


Callback chains
===============

Effect allows you to build up chains of callbacks that process data in turn.
That is, if you attach a callback ``a`` and then a callback ``b`` to an Effect,
``a`` will be called with the original result, and ``b`` will be called with
the result of ``a``. This is exactly how Twisted's Deferreds work, and similar
to the monadic ``bind`` (``>>=``) function from Haskell.

This is a great way to build abstractions, compared to non-chaining callback
systems like Python's Futures. You can easily build abstractions like the
following:

.. code:: python

    def request_url(method, url, str_body):
        """Perform an HTTP request."""
        return Effect(HTTPRequest(method, url, str_body))

    def request_200_url(method, url, str_body):
        """
        Perform an HTTP request, and raise an error if the response is not 200.
        """
        def check_status(response):
            if response.code != 200:
                raise HTTPError(response.code)
            return response
        return request_url(method, url, str_body).on(success=check_status)

    def json_request(method, url, dict_body):
        """
        Perform an HTTP request where the body is sent as JSON and the response
        is automatically decoded as JSON if the Content-type is
	application/json.
        """
        str_body = json.dumps(dict_body)
        return request_200_url(method, url, str_body).on(success=decode_json)




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

