
class DBError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class AlreadyExistsError(DBError):
    def __init__(self, msg):
        super().__init__(msg)


class NotFoundError(DBError):
    def __init__(self, msg):
        super().__init__(msg)


class MultipleFoundError(DBError):
    def __init__(self, msg):
        super().__init__(msg)

