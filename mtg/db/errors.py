
class DBError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg
    

class DBOpenError(DBError):
    def __init__(self, msg):
        super().__init__(msg)


class AlreadyExistsError(DBError):
    def __init__(self, msg):
        super().__init__(msg)


class NotFoundError(DBError):
    def __init__(self, msg):
        super().__init__(msg)


class MultipleFoundError(DBError):
    def __init__(self, msg):
        super().__init__(msg)


class ForeignKeyError(DBError):
    """
    Raised when there is a foreign key constraint violation.
    """

    def __init__(self, msg, column: str | None=None, bad_value: any=None):
        super().__init__(msg)
        self.column = column
        self.bad_value = bad_value
        