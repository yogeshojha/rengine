from django import template
from urllib.parse import urlparse

register = template.Library()


@register.filter(name='split')
def split(value, key):
    return value.split(key)
