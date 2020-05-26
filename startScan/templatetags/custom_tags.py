from django import template


register = template.Library()

@register.filter(name='split')
def split(value, key):
    return value.split(key)

@register.filter(name='count')
def count(value):
    return len(value.split(','))
