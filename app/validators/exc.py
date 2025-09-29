class EmptySpaceError(BaseException):
    raise "Nickname cannot contain empty spaces"

class TooShortError(BaseException):
    raise "Nickname must be at least 6 characters long"

class TooLongError(BaseException):
    raise "Nickname must be at most 16 characters long"

class AlreadyExistsError(BaseException):
    raise "Nickname already exists"

class InvalidCharactersError(BaseException):
    raise "Nickname must contain only latin characters and numbers"