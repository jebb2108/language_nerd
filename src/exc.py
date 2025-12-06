class PaymentException(Exception):
    """ Класс исключения для оплаты """
    pass


class StorageDataException(Exception):
    """ Ошибка при извлечении данных о пользователе """
    pass

class EmojiesNotAllowed(Exception):
    """ Исключение для эмодзи в никнейме """
    pass


class EmptySpaceError(Exception):
    """ Исключение для пустых пробелов в никнейме """
    pass


class TooShortError(Exception):
    """ Исключение для уже существующего никнейма """
    pass


class TooLongError(Exception):
    """ Исключение для слишком короткого никнейма """
    pass


class AlreadyExistsError(Exception):
    """ Исключение для слишком длинного никнейма """
    pass


class InvalidCharactersError(Exception):
    """ Исключение для недопустимых символов в никнейме """
    pass


class FailToCreateToken(Exception):
    """ Ошибка при создании токена """