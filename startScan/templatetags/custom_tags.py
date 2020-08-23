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

@register.filter(name='getitem')
def getitem(dictionary, key):
    return dictionary.get(key)


@register.simple_tag
def setvar(val=None):
  return val
