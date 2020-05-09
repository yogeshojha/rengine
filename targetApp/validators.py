from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import validators

def validate_domain(value):
    if not validators.domain(value):
        raise ValidationError(
        _('%(value)s is not a valid domain Name'),
            params={'value': value},
        )
