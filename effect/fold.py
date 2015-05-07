_sneaky = object()


def fold_effect(f, initial, effects):
    """
    Fold over effects.

    The function will be called with the accumulator (starting with
    ``initial``) and a result of an effect repeatedly for each effect. The
    result of the previous call will be passed as the accumulator to the next
    call.

    :param callable f: function of ``(accumulator, element) -> accumulator``
    :param initial: The value to be passed as the accumulator to the first
        invocation of ``f``.
    :param effects: sequence of Effects.
    """

    def folder(acc, element):
        # A bit of a hack here. We could just wrap `initial` in a
        # Effect(Constant()), but to simplify testing we avoid the additional
        # Effect by "sneaking" it in this way.

        # This way people can use SequenceDispatcher and not get anything
        # unexpected.
        if acc is _sneaky:
            return element.on(lambda r: f(initial, r))
        else:
            return acc.on(lambda r: element.on(lambda r2: f(r, r2)))

    return reduce(folder, effects, _sneaky)
