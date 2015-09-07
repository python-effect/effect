from . import Effect, sync_perform
from .io import Display, Prompt, stdio_dispatcher


def test_perform_display_print(capsys):
    """The stdio dispatcher has a performer that prints output."""
    assert sync_perform(stdio_dispatcher, Effect(Display("foo"))) is None
    out, err = capsys.readouterr()
    assert err == ''
    assert out == 'foo\n'


def test_perform_get_input_raw_input(monkeypatch):
    """The stdio dispatcher has a performer that reads input."""
    monkeypatch.setattr(
        'effect.io.input',
        lambda p: 'my name' if p == '> ' else 'boo')
    assert sync_perform(stdio_dispatcher, Effect(Prompt('> '))) == 'my name'
