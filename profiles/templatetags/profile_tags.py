from django import template
from profiles.countries import country_flag, country_name

register = template.Library()


@register.filter
def flag(country_code):
    return country_flag(country_code)


@register.filter
def country_label(country_code):
    return country_name(country_code)
