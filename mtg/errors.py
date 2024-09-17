
class CommandError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class TooManyMatchesError(CommandError):
    def __init__(self, msg):
        super().__init__(msg)


class NotFoundError(CommandError):
    def __init__(self, msg):
        super().__init__(msg)


class UserCancelledError(CommandError):
    def __init__(self, msg):
        super().__init__(msg)


# TODO: eventually all arg parsing should be in argparse type funcs and this should be removed
class ArgumentError(CommandError):
    def __init__(self, msg):
        super().__init__(msg)


class DataConflictError(CommandError):
    """
    Raise when current state does not allow the operation; e.g. adding a card to
    a deck when the card has no free copies.
    """
    
    def __init__(self, msg):
        super().__init__(msg)
