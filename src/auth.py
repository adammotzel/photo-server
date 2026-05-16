from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    """
    Hash a user password for db storage.

    Parameters
    ----------
    password : str
        Un-hashed password string.

    Returns
    -------
    str
        Hashed password string for db storage.
    """
    return _ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    Check a given password string against a hashed string.

    Parameters
    ----------
    password : str
        Un-hashed password string.
    hashed : str
        Hashed password string.

    Returns
    -------
    bool
        If the passwords align.
    """
    try:
        return _ph.verify(hashed, password)
    except VerifyMismatchError:
        return False
