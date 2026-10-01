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

@register.filter
def specialiste_img(value):
    """Return the image path (under static/) for a specialist category."""
    mapping = {
        'psychologue':       'specialistes/Psychologue.jpg',
        'psychiatre':        'specialistes/Psychiatre.jpg',
        'psychotherapeute':  'specialistes/Psychotherapeute.jpg',
        'medecin_sport':     'specialistes/MedecinSport.jpg',
        'kinesitherapeute':  'specialistes/Kinesitherapeute.jpg',
        'osteopathe':        'specialistes/Osteopathe.jpg',
        'psychomotricien':   'specialistes/Psychomotricien.jpg',
        'ergotherapeute':    'specialistes/Ergotherapeute.jpg',
        'dieteticien':       'specialistes/Dieteticien.jpg',
        'coach_sportif':     'specialistes/CoachSportif.jpg',
    }
    return mapping.get(str(value).lower(), '')
