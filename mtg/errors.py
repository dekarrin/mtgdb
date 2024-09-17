
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