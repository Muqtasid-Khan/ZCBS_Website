from django import template

from apps.core.utils import absolute_url

register = template.Library()


@register.simple_tag(takes_context=True)
def abs_url(context, url):
    """{% abs_url some.image.url %} -> full https:// address for og:image etc."""
    return absolute_url(context["request"], url)
