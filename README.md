# Effect

[![Build Status](https://travis-ci.org/radix/effect.svg?branch=master)](https://travis-ci.org/radix/effect)

Effect is a library for helping you write purely functional code by
isolating the effects (that is, IO or state manipulation) in your code.

You can [read the code](effect/__init__.py).


# Status: Alpha

Right now Effect is in alpha, and is likely to change incompatibly. Once it's
being used in production, I'll release a final version.


# What Is It?

It's a number of things, depending on your perspective:

- the IO monad for Python, or
- an immutable/purely functional version of Twisted's Deferred, or
- a way to improve test quality, by promoting "stub" objects to the real
  implementation
- a way to decouple the "intent" of an effect from the implementation, thus
  allowing alternative implementations of effects.

Each of these perspectives has a section below describing that approach.

Effect starts with a very simple idea: instead of having a function which
performs side-effects (such as IO):

    def get_user_name():
        return raw_input("Enter User Name> ")

you instead have a function which *returns* a representation of the
side-effect:

    def get_user_name():
        return Effect(ReadLine("Enter User Name> "))

We call objects like "ReadLine" an *intent* -- that is, the *intent* of this
effect is to read a line.

This function now returns an object which can later be "performed":

    def main():
        effect = get_user_name()
        effect.on_success(print)
        perform(effect)

This has a number of advantages. First, your unit tests for `get_user_name`
become simpler. You don't need to mock out or parameterize the `raw_input`
function - you just call `get_user_name` and assert that it returns a ReadLine
object with the correct 'prompt' value.

Second, you can implement ReadLine in a number of different ways - it's
possible to override the "perform" implementations for effects to do whatever
you want.

Third, your function is now purely functional, letting you rest easy knowing
that you've improved the amount of quality code in the world ;-)

For more information on how to implement the actual effect-performing code,
and other details, see the [API documentation](effect/__init__.py).


# Callback chains

Effect allows you to build up chains of callbacks that process data in turn.
That is, if you attach a callback `a` and then a callback `b` to an Effect,
`a` will be called with the original result and `b` will be called with with
the result of `a`. This is inspired directly by Twisted's Deferreds.

This is a great way to build end-to-end abstractions, compared to non-chaining
callback systems like Python's Futures. You can easily build abstractions
like the following:

    def request_url(method, url, str_body):
        """Perform an HTTP request."""
        return Effect(Request(method, url, str_body))

    def request_200_url(method, url, str_body):
        """
        Perform an HTTP request, and raise an error if the response is not 200.
        """
        return request_url(method, url, str_body).on_success(check_status)

    def json_request(method, url, dict_body):
        """
        Perform an HTTP request where the body is sent as JSON and the response
        is automatically decoded as JSON if the Content-type is
        application/json.
        """
        str_body = json.dumps(dict_body)
        return request_url(method, url, str_body).on_success(decode_json)

The monadic bind function has these same properties. Those Haskell people sure
have some good ideas.


# Learning more

I've tried to ensure that the docstrings of all the public functions and
classes are up to snuff. There are also real-world examples available in
the [examples](examples/) directory, including how to write idiomatic tests.

Following are a number of sections where the utility of the Effect library is
highlighted from a number of different use cases.


## Monads for Python

Effects are very analogus to IO monads. The Effect class is similar to the
IO type, in that it "tags" (or wraps) your return type, and
`Effect.on_success` is like the bind function (`>>=`), indicating that the
function passed is to be called with the result of the effect.

This library encourages a convention of representing your effects as
*transparent data*, which we call the "intent" of an effect. By transparent,
I specifically mean that it should be an inert data structure with public
attributes describing everything necessary to perform the effect. In Haskell,
typically you write an IO function, the only thing you can do with it is
return it up to main to perform it. No way to inspect the operation.
Representing effects as transparent data gives us two advantages:

- the ability to provide alternative implementations (such as an asynchronous
  Twisted-based implementation, or a standard blocking implementation), since
  the effect performance is late-bound to the effect intent.
- the ability to perform simple value comparisons in your unit tests to ensure
  the right effects will be performed.

Similar things have been done in Haskell (in a perhaps more elegant way) by
using free monads, which are essentially a way to "parse" and interpret your
monadic code without really performing its effects. This would be difficult in
Python.

## Immutable Deferreds

There are two main differences between Effects and Deferreds, and one is only
conventional. One, of course, is that Effects are immutable. The second is that
the functions that *produce* Effects are (or *can* be) pure.

In almost every case, Deferred-producing functions must have side effects.
They kick off some IO and tuck the Deferred away somewhere so they can fire
it later.

Functions that produce Effects, on the other hand, should not have
side-effects. They should simply describe the *intent* of the effect. They
don't need to tuck the Effect away to fire later, because that whole process
comes later, when the effect is performed.

In some sense, an Effect is an inside-out Deferred -- instead of performing
the effects in the innermost function that produces the Deferred, with
callbacks being attached on the way out, the effect is performed after the
whole tree of callbacks has been constructed, higher up the stack.

This avoids the problems with Deferred that require it to have a special
garbage-collection handler to log errors that haven't yet been handled --
we know that when all of an Effect's callbacks have been run, no more can
possibly be attached, so we can immediately raise an exception if the final
result was an error (this is the behavior of the `sync_perform` function).


## Testability by promoting stub objects

In unit tests, we often use stub objects to replace objects that are
considered "expensive", or otherwise difficult to deal with. The Effect
library encourages the promotion of these stub objects to the implementation.
This allows us to stop worrying if our stub is close enough to the real thing,
since it *is* the real thing -- if the stub is wrong, the effect implementation wouldn't work.


## Alternative effect implementations

Effect is a good way to write code that can be used in any number of IO
frameworks: either with standard blocking IO, or with an asynchronous IO
system like Twisted or asyncio (or Trollius, or Tornado, or eventlet, etc
etc). This is because it forces you to decouple the plain, pure functions that
perform only the work *between* IO from the IO work itself.


## A history of the development

For pedagogical purposes, I'll describe the thought process that led me to
write this library. There were a couple of desires that led to me thinking
about this problem.

First, I had been thinking for a long time that more of my code should be
purely functional. The benefits of pure FP code are well understood, if not
fully accepted by the majority of programmers. Needless to say, I buy into
it.

I long had the idea that an HTTP client library, for example, should separate
the request from the performance of that request. My ideal client would return
an inert "Request" object from the http.get() method, instead of actually
performing the IO.

At the same time, I had also been struggling with testing in the Python
ecosystem. Mocking and stubbing have become extremely widespread in the
community, but over and over I saw that the result of ubiquitous usage of
mocking were test suites that were extremely difficult to understand and
maintain. I saw test suites that were overly tied to the implementation of
code under test, and much duplicated mock boilerplate -- code that would
set up detailed mocks that were very subtly different from test to test.

For a while, I thought that "verified fakes" would solve the problem. Instead
of having every one of your tests mocking out the specific IO methods that a
piece of implementation code will use, write a class that implements the same
interface as the IO code and acts on a test model. This is a good way to do it,
but then you have to concern yourself with ensuring the fake has the same
behavior as the real implementation.

Then I realized that stubs were a lot like my idea for the "Request" object
that my ideal HTTP client library would return -- in other words, the stubs
could be promoted to being used in the real implementation. That way the
majority of my tetss wouldn't need any mocking or stubbing, and would just
invoke the pure 'get' method and ensure that it returned a Request object that
looked right.

Once I got serious about writing code that was purely functional and which
returned transparent objects I quickly came to the conclusion that *just*
returning a Request object wasn't enough. I realized I needed *end to end
abstractions*. Specifically, for example, I wanted an HTTP client abstraction
that could specify a request *and* process the result -- by checking to see
if the response code was something other than 200 and raising an error, for
example. Or automatically decoding JSON responses to Python objects.

Basically, I needed callbacks, or the `>>=` operator from Haskell. Deferreds
are a great abstraction for callbacks, but I wanted something purely
functional, and which let you decouple the intent of the effect from the
performance of the effect. From all these ideas came the Effect library.


# Thanks

Thanks to Rackspace for allowing me to work on this project, and having an
*excellent* [open source employee contribution policy](https://www.rackspace.com/blog/rackspaces-policy-on-contributing-to-open-source/).


# License

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
