"""Filtres d'affichage de Wanaag Corner."""
import re

from django import template

register = template.Library()

_PICTO = re.compile(
    "[\U0001F000-\U0001FAFF←-⇿⌀-⏿☀-➿⬀-⯿️‍⃣]+",
    flags=re.UNICODE,
)


@register.filter
def sobre(value):
    """Retire les pictogrammes d'un libellé (« 💙 Dépression » devient « Dépression »)."""
    if value is None:
        return ""
    return re.sub(r"\s{2,}", " ", _PICTO.sub("", str(value))).strip()


@register.filter
def initiale(value):
    """Première lettre en capitale, pour les avatars."""
    text = sobre(value)
    return text[:1].upper() if text else "·"


@register.filter
def texte_riche(value):
    """Affiche un contenu rédigé en HTML (nettoyé) ou en texte simple (mis en paragraphes)."""
    from django.utils.safestring import mark_safe

    from application.richtext import sanitize_html, text_to_html

    if not value:
        return ""
    text = str(value)
    if re.search(r"<(p|h[1-6]|br|ul|ol|li|div|blockquote|strong|em|a|img|figure)\b", text, re.I):
        return mark_safe(sanitize_html(text))
    return mark_safe(sanitize_html(text_to_html(text)))


@register.filter
def decoupe(value, sep=","):
    """Découpe une liste écrite en texte (« a, b, c ») et retire les espaces."""
    return [part.strip() for part in str(value or "").split(sep) if part.strip()]
