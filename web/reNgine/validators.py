import re

import validators
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_domain(value):
    if not validators.domain(value):
        raise ValidationError(_('%(value)s is not a valid domain Name'
                                ), params={'value': value})


def validate_url(value):
    if not validators.url(value):
        raise ValidationError(_('%(value)s is not a valid URL Name'),
                              params={'value': value})


def validate_short_name(value):
    regex = re.compile(r'[@!#$%^&*()<>?/\|}{~:]')
    if regex.search(value):
        raise ValidationError(_('%(value)s is not a valid short name,'
                                + ' can only contain - and _'),
                              params={'value': value})
