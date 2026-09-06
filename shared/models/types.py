"""Column types that keep a value encrypted at rest."""

import json

from sqlalchemy import Text, TypeDecorator

from shared.utils.crypto import encrypt_secret, try_decrypt


class EncryptedJSON(TypeDecorator):
    """A JSON value stored as a Fernet token, so a database dump carries no secret."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ARG002
        if value is None:
            return None
        return encrypt_secret(json.dumps(value))

    def process_result_value(self, value, dialect):  # noqa: ARG002
        if value is None:
            return None
        # a row written before the column was encrypted is still plain JSON
        plain = try_decrypt(value)
        try:
            return json.loads(plain if plain is not None else value)
        except (TypeError, ValueError):
            return None
