"""Nettoyage du HTML produit par l'éditeur d'articles/blogs.

Tout ce qui arrive du navigateur est traité comme non fiable : on ne garde
qu'une liste blanche de balises de mise en forme, et les médias ne peuvent
pointer que vers nos propres uploads.
"""
import html as _html
import re

import nh3
from django.conf import settings

ALLOWED_TAGS = {
    'p', 'div', 'br', 'h2', 'h3', 'blockquote', 'ul', 'ol', 'li',
    'strong', 'b', 'em', 'i', 'u', 'a', 'hr', 'figure', 'img', 'video',
}
ALLOWED_ATTRIBUTES = {
    'a': {'href'},
    'img': {'src', 'alt'},
    'video': {'src', 'controls', 'poster'},
}
ALLOWED_SCHEMES = {'http', 'https', 'mailto'}

_EMPTY_BLOCK = re.compile(r'<(p|div)>\s*(?:<br\s*/?>\s*)*</\1>', re.I)
_SRCLESS_MEDIA = re.compile(r'<img(?![^>]*\bsrc=)[^>]*>|<video(?![^>]*\bsrc=)[^>]*></video>', re.I)
_BLOCK_END = re.compile(r'</(?:p|div|h[1-6]|li|blockquote|figure)>|<br\s*/?>|<hr\s*/?>', re.I)


def _keep_attribute(tag, attribute, value):
    if attribute in ('src', 'poster'):
        if value.startswith(settings.MEDIA_URL) and '..' not in value:
            return value
        return None
    return value


def sanitize_html(raw):
    cleaned = nh3.clean(
        raw or '',
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_SCHEMES,
        link_rel='noopener noreferrer nofollow',
        attribute_filter=_keep_attribute,
        strip_comments=True,
    )
    cleaned = _SRCLESS_MEDIA.sub('', cleaned)
    return _EMPTY_BLOCK.sub('', cleaned).strip()


def html_to_text(clean_html):
    spaced = _BLOCK_END.sub('\n', clean_html or '')
    text = _html.unescape(nh3.clean(spaced, tags=set()))
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def text_to_html(plain):
    """Texte brut (anciens blogs) -> paragraphes HTML échappés."""
    paragraphs = [p for p in re.split(r'\n\s*\n', (plain or '').strip()) if p.strip()]
    return ''.join(
        '<p>' + _html.escape(p.strip()).replace('\n', '<br>') + '</p>' for p in paragraphs
    )
