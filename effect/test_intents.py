from __future__ import print_function, absolute_import

from functools import partial

import six

from testtools import TestCase
from testtools.matchers import Equals, MatchesListwise

from pytest import raises

from ._base import Effect
from ._dispatcher import ComposedDispatcher, TypeDispatcher
from ._intents import (
    base_dispatcher,
    Constant, perform_constant,
    Delay, perform_delay_with_sleep,
    Error, perform_error,
    Func, perform_func,
    FirstError,
    ParallelEffects, parallel_all_errors)
from ._sync import sync_perform
from ._test_utils import MatchesReraisedExcInfo, get_exc_info
from .async import perform_parallel_async
from .test_parallel_performers import EquitableException


def test_perform_constant():
    """perform_constant returns the result of a Constant."""
    intent = Constant("foo")
    result = sync_perform(
        TypeDispatcher({Constant: perform_constant}),
        Effect(intent))
    assert result == "foo"


def test_perform_error():
    """perform_error raises the exception of an Error."""
    intent = Error(ValueError("foo"))
    with raises(ValueError):
        sync_perform(TypeDispatcher({Error: perform_error}), Effect(intent))


def test_perform_func():
    """perform_func calls the function given in a Func."""
    intent = Func(lambda: "foo")
    result = sync_perform(
        TypeDispatcher({Func: perform_func}),
        Effect(intent))
    assert result == "foo"

def test_perform_func_args_kwargs():
    """arbitrary positional and keyword arguments can be passed to Func."""
    f = lambda *a, **kw: (a, kw)
    intent = Func(f, 1, 2, key=3)
    result = sync_perform(TypeDispatcher({Func: perform_func}), Effect(intent))
    assert result == ((1, 2), {'key': 3})


def test_first_error_str():
    """FirstErrors have a pleasing format."""
    fe = FirstError(exc_info=(ValueError, ValueError('foo'), None),
                    index=150)
    assert str(fe) == '(index=150) ValueError: foo'


def test_perform_delay_with_sleep(monkeypatch):
    """:func:`perform_delay_with_sleep` calls time.sleep."""
    calls = []
    monkeypatch.setattr('time.sleep', calls.append)
    disp = TypeDispatcher({Delay: perform_delay_with_sleep})
    sync_perform(disp, Effect(Delay(3.7)))
    assert calls == [3.7]


class ParallelAllErrorsTests(TestCase):
    """Tests for :func:`parallel_all_errors`."""

    def test_parallel_all_errors(self):
        """
        Exceptions raised from child effects get turned into (True, exc_info)
        results.
        """
        exc_info1 = get_exc_info(EquitableException(message='foo'))
        reraise1 = partial(six.reraise, *exc_info1)
        exc_info2 = get_exc_info(EquitableException(message='bar'))
        reraise2 = partial(six.reraise, *exc_info2)

        dispatcher = ComposedDispatcher([
            TypeDispatcher({
                ParallelEffects: perform_parallel_async,
            }),
            base_dispatcher])
        es = [Effect(Func(reraise1)),
              Effect(Constant(1)),
              Effect(Func(reraise2))]
        eff = parallel_all_errors(es)
        self.assertThat(
            sync_perform(dispatcher, eff),
            MatchesListwise([
                MatchesListwise([Equals(True),
                                 MatchesReraisedExcInfo(exc_info1)]),
                Equals((False, 1)),
                MatchesListwise([Equals(True),
                                 MatchesReraisedExcInfo(exc_info2)]),
            ]))
