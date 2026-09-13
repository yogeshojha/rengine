"""Column types that keep a value encrypted at rest."""

import json

from sqlalchemy import Text, TypeDecorator

from shared.utils.crypto import SecretDecryptionError, decrypt_stored, encrypt_secret


class EncryptedJSON(TypeDecorator):
    """A JSON value stored as a Fernet token."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ARG002
        if value is None:
            return None
        return encrypt_secret(json.dumps(value))

    def process_result_value(self, value, dialect):  # noqa: ARG002
        if value is None:
            return None
        plain = decrypt_stored(value, label="A stored configuration value")
        try:
            return json.loads(plain)
        except (TypeError, ValueError) as exc:
            msg = (
                "A stored configuration value could not be read. "
                "Save the setting again."
            )
            raise SecretDecryptionError(msg) from exc
