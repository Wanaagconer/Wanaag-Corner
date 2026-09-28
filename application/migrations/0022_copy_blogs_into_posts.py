import html
import re

from django.db import migrations


def _paragraphs(plain):
    parts = [p for p in re.split(r'\n\s*\n', (plain or '').strip()) if p.strip()]
    return ''.join('<p>' + html.escape(p.strip()).replace('\n', '<br>') + '</p>' for p in parts)


def copy_blogs(apps, schema_editor):
    Blog = apps.get_model('application', 'BlogBienEtre')
    Post = apps.get_model('application', 'Post')
    for blog in Blog.objects.filter(est_publie=True).order_by('date_creation'):
        post = Post.objects.create(
            auteur=blog.utilisateur,
            type='blog',
            titre=blog.titre,
            contenu=blog.contenu,
            corps=_paragraphs(blog.contenu),
            tags=blog.tags,
            image=blog.image.name if blog.image else None,
        )
        post.likes.set(blog.likes.all())
        # auto_now_add / auto_now ont daté la copie à aujourd'hui : on restaure l'original.
        Post.objects.filter(pk=post.pk).update(
            date_creation=blog.date_creation, date_modification=blog.date_creation
        )


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0021_post_long_format_fields'),
    ]

    operations = [
        migrations.RunPython(copy_blogs, migrations.RunPython.noop),
    ]
