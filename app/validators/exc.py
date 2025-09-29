class EmptySpaceError(Exception):
    raise "Nickname cannot contain empty spaces"

class TooShortError(Exception):
    raise "Nickname must be at least 6 characters long"

class TooLongError(Exception):
    raise "Nickname must be at most 16 characters long"

class AlreadyExistsError(Exception):
    raise "Nickname already exists"

class InvalidCharactersError(Exception):
    raise "Nickname must contain only latin characters and numbers"