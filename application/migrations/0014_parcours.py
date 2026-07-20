from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('application', '0013_consultationrequest_type_seance'),
    ]

    operations = [
        migrations.CreateModel(
            name='JournalEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(blank=True, max_length=200)),
                ('contenu', models.TextField()),
                ('humeur', models.CharField(choices=[('5', 'Excellent'), ('4', 'Bien'), ('3', 'Moyen'), ('2', 'Difficile'), ('1', 'Terrible')], default='3', max_length=2)),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('date_modification', models.DateTimeField(auto_now=True)),
                ('utilisateur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='journal_entries', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Entrée de journal', 'verbose_name_plural': 'Entrées de journal', 'ordering': ['-date_creation']},
        ),
        migrations.CreateModel(
            name='QuoteInspirante',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texte', models.TextField()),
                ('auteur', models.CharField(blank=True, default='Anonyme', max_length=150)),
                ('categorie', models.CharField(blank=True, max_length=50)),
            ],
            options={'verbose_name': 'Citation inspirante', 'verbose_name_plural': 'Citations inspirantes'},
        ),
        migrations.CreateModel(
            name='ProfilSante',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('age', models.IntegerField()),
                ('taille', models.IntegerField()),
                ('poids', models.FloatField()),
                ('sexe', models.CharField(choices=[('homme', 'Homme'), ('femme', 'Femme')], max_length=10)),
                ('niveau_activite', models.CharField(choices=[('sedentaire', 'Sédentaire'), ('leger', 'Légèrement actif (1-3j/sem)'), ('modere', 'Modérément actif (3-5j/sem)'), ('actif', 'Très actif (6-7j/sem)'), ('tres_actif', 'Extrêmement actif')], default='modere', max_length=20)),
                ('objectif', models.CharField(choices=[('perdre', 'Perdre du poids'), ('maintenir', 'Maintenir le poids'), ('prendre', 'Prendre du poids / Musculation')], default='maintenir', max_length=20)),
                ('date_modification', models.DateTimeField(auto_now=True)),
                ('utilisateur', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profil_sante', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Profil santé', 'verbose_name_plural': 'Profils santé'},
        ),
        migrations.CreateModel(
            name='BlogBienEtre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=200)),
                ('contenu', models.TextField()),
                ('image', models.ImageField(blank=True, null=True, upload_to='blogs/')),
                ('tags', models.CharField(blank=True, max_length=200)),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('est_publie', models.BooleanField(default=True)),
                ('utilisateur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blogs_bien_etre', to=settings.AUTH_USER_MODEL)),
                ('likes', models.ManyToManyField(blank=True, related_name='blogs_aimes', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Blog bien-être', 'verbose_name_plural': 'Blogs bien-être', 'ordering': ['-date_creation']},
        ),
    ]
