from testtools import TestCase
from testtools.matchers import raises

from .retry import retry
from . import base_dispatcher
from .testing import ESConstant, ESError, ESFunc, resolve_stubs


class RetryTests(TestCase):

    def test_should_not_retry(self):
        """retry raises the last error if should_retry returns False."""
        result = retry(ESError(RuntimeError("oh no!")),
                       lambda e: ESConstant(False))
        self.assertThat(lambda: resolve_stubs(base_dispatcher, result),
                        raises(RuntimeError("oh no!")))

    def _repeated_effect_func(self, *funcs):
        """
        Return an (impure) function which does different things based on the
        number of times it's been called.
        """
        counter = [0]

        def func():
            count = counter[0]
            counter[0] += 1
            return funcs[count]()

        return func

    def test_retry(self):
        """
        When should_retry returns an Effect of True, the func will be called
        again.
        """
        func = self._repeated_effect_func(
            lambda: raise_(RuntimeError("foo")),
            lambda: "final")
        result = retry(ESFunc(func),
                       lambda e: ESConstant(True))
        self.assertEqual(resolve_stubs(base_dispatcher, result), "final")

    def test_continue_retrying(self):
        """
        should_retry is passed the exception information, and will be
        called until it returns False.
        """

        func = self._repeated_effect_func(
            lambda: raise_(RuntimeError("1")),
            lambda: raise_(RuntimeError("2")),
            lambda: raise_(RuntimeError("3")))

        def should_retry(e):
            return ESConstant(str(e[1]) != "3")

        result = retry(ESFunc(func), should_retry)
        self.assertThat(lambda: resolve_stubs(base_dispatcher, result),
                        raises(RuntimeError("3")))


def raise_(exc):
    raise exc
