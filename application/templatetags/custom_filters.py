from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Split a string by the given separator."""
    return value.split(arg)

@register.filter
def trim(value):
    """Strip whitespace from a string."""
    return str(value).strip()

@register.filter
def type_img(value):
    """Return the image filename for a resource type."""
    mapping = {
        'article':    'Article.jpg',
        'guide':      'Guide.jpg',
        'video':      'Video.jpg',
        'podcast':    'Podcast.jpg',
        'formation':  'Formation.jpg',
        'atelier':    'Atelier.jpg',
        'conference': 'Conference.jpg',
    }
    return mapping.get(str(value).lower(), '')
