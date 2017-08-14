import os
import binascii


def generate_token(lenght: int = 40) -> bytes:
    """
    Generates a random token with a specified length
    :return: bytes-encoded string
    """
    n_of_bytes = lenght // 2

    return binascii.hexlify(os.urandom(n_of_bytes))
