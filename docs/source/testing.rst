Testing Effectful Code
----------------------

The most useful testing tool you'll want to familiarize yourself with is
:obj:`effect.testing.SequenceDispatcher`. Using this with
:func:`effect.sync_perform` in your unit tests will allow you to perform your
effects while both ensuring that the expected intents are performed, as well as
provide the results of those effects.
