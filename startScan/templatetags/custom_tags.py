from django import template
from urllib.parse import urlparse

register = template.Library()


@register.filter(name='split')
def split(value, key):
    return value.split(key)


@register.filter(name='count')
def count(value):
    return len(value.split(','))


@register.filter(name='getpath')
def getpath(value):
    parsed_url = urlparse(value)
    if parsed_url.query:
        return parsed_url.path + '?' + parsed_url.query
    else:
        return parsed_url.path


@register.filter(name='none_or_never')
def none_or_never(value):
    return 'Never' if value is None else value
