Testing Effectful Code
----------------------

The most useful testing tool you'll want to familiarize yourself with is
:func:`effect.testing.perform_sequence`. Using this in your unit tests will
allow you to perform your effects while ensuring that the expected intents are
performed in the expected order, as well as provide the results of those
effects.
