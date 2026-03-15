from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils.text import slugify

class CustomUser(AbstractUser):
    pseudonyme = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    
    # Pour l'authentification par email
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'pseudonyme']
    
    def __str__(self):
        return self.pseudonyme

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'


# ============= MODÈLES DU FORUM =============

class ForumGroup(models.Model):
    """Modèle pour les groupes de discussion"""
    CATEGORY_CHOICES = [
        ('anxiete', '💭 Anxiété'),
        ('depression', '💙 Dépression'),
        ('meditation', '🧘 Méditation'),
        ('famille', '👨‍👩‍👧‍👦 Famille'),
        ('developpement', '🌱 Développement'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Nom du groupe")
    description = models.TextField(verbose_name="Description")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='joined_groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Groupe de discussion"
        verbose_name_plural = "Groupes de discussion"
    
    def __str__(self):
        return self.name
    
    def member_count(self):
        return self.members.count()
    
    def unread_count(self, user):
        """Nombre de messages non lus pour un utilisateur"""
        last_read = GroupMemberStatus.objects.filter(
            group=self, user=user
        ).first()
        
        if not last_read:
            return self.messages.count()
        
        return self.messages.filter(
            created_at__gt=last_read.last_read_at
        ).count()


class GroupMessage(models.Model):
    """Modèle pour les messages dans les groupes"""
    group = models.ForeignKey(ForumGroup, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(verbose_name="Message")
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = "Message"
        verbose_name_plural = "Messages"
    
    def __str__(self):
        return f"{self.sender.pseudonyme}: {self.content[:50]}"


class GroupMemberStatus(models.Model):
    """Suivi du statut de lecture pour chaque membre"""
    group = models.ForeignKey(ForumGroup, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    last_read_at = models.DateTimeField(auto_now=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['group', 'user']
        verbose_name = "Statut membre"
        verbose_name_plural = "Statuts membres"


# ============= MODÈLES DES RESSOURCES ÉDUCATIVES =============

class CategorieRessource(models.Model):
    """Catégories pour les ressources éducatives"""
    nom = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    icone = models.CharField(max_length=10, default='📚', help_text="Emoji pour la catégorie")
    ordre = models.IntegerField(default=0, help_text="Ordre d'affichage")
    
    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = "Catégorie de ressource"
        verbose_name_plural = "Catégories de ressources"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.icone} {self.nom}"


class Ressource(models.Model):
    """Ressources éducatives (articles, guides, vidéos, etc.)"""
    TYPE_CHOICES = [
        ('article', '📝 Article'),
        ('guide', '📖 Guide pratique'),
        ('video', '🎥 Vidéo'),
        ('podcast', '🎧 Podcast'),
        ('formation', '🎓 Formation'),
        ('atelier', '🛠️ Atelier'),
        ('conference', '🎤 Conférence'),
    ]
    
    NIVEAU_CHOICES = [
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance', 'Avancé'),
    ]
    
    titre = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    type_ressource = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES, 
        default='article',
        verbose_name="Type de ressource"
    )
    categorie = models.ForeignKey(
        CategorieRessource, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='ressources'
    )
    description = models.TextField(
        verbose_name="Description courte", 
        max_length=300
    )
    
    # Champs conditionnels selon le type
    contenu = models.TextField(
        verbose_name="Contenu complet", 
        blank=True,
        help_text="Pour les articles, guides et supports de conférence"
    )
    lien_externe = models.URLField(
        blank=True, 
        null=True, 
        help_text="Lien YouTube pour vidéos, Spotify pour podcasts, Zoom pour ateliers"
    )
    fichier_audio = models.FileField(
        upload_to='podcasts/', 
        blank=True, 
        null=True,
        help_text="Fichier audio MP3 pour les podcasts (optionnel si lien externe)"
    )
    image_couverture = models.ImageField(
        upload_to='ressources/', 
        blank=True, 
        null=True
    )
    
    # Champs spécifiques pour formations/ateliers/conférences
    date_debut = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Date et heure de début",
        help_text="Pour formations, ateliers et conférences"
    )
    date_fin = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Date et heure de fin",
        help_text="Optionnel"
    )
    lieu = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name="Lieu",
        help_text="Adresse physique, 'En ligne', ou lien de visioconférence"
    )
    places_disponibles = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Nombre de places",
        help_text="Nombre de places disponibles (laisser vide pour illimité)"
    )
    intervenant = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Intervenant/Formateur",
        help_text="Nom de l'intervenant pour conférences, formations et ateliers"
    )
    
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='ressources_creees'
    )
    niveau = models.CharField(
        max_length=20, 
        choices=NIVEAU_CHOICES, 
        default='debutant'
    )
    duree_lecture = models.IntegerField(
        default=5, 
        verbose_name="Durée (minutes)",
        help_text="Durée estimée en minutes"
    )
    
    tags = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Tags séparés par des virgules"
    )
    
    vues = models.IntegerField(default=0)
    favoris = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='ressources_favorites', 
        blank=True
    )
    
    est_publie = models.BooleanField(default=True, verbose_name="Publié")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Ressource"
        verbose_name_plural = "Ressources"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.titre
    
    def incrementer_vues(self):
        self.vues += 1
        self.save(update_fields=['vues'])
    
    def is_evenement(self):
        """Vérifie si c'est un événement avec date"""
        return self.type_ressource in ['formation', 'atelier', 'conference']
    
    def places_restantes(self):
        """Calcule les places restantes pour les événements"""
        if self.places_disponibles and self.places_disponibles > 0 and self.is_evenement():
            inscrits = self.progressions.filter(est_complete=True).count()
            return max(0, self.places_disponibles - inscrits)
        return None
    
    def is_complet(self):
        """Vérifie si l'événement est complet"""
        places = self.places_restantes()
        return places is not None and places == 0


class CommentaireRessource(models.Model):
    """Commentaires sur les ressources"""
    ressource = models.ForeignKey(Ressource, on_delete=models.CASCADE, related_name='commentaires')
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contenu = models.TextField(max_length=1000)
    date_creation = models.DateTimeField(auto_now_add=True)
    est_modifie = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"
    
    def __str__(self):
        return f"Commentaire de {self.auteur.pseudonyme} sur {self.ressource.titre}"


class ProgressionUtilisateur(models.Model):
    """Suivi de la progression de l'utilisateur dans les ressources"""
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progressions')
    ressource = models.ForeignKey(Ressource, on_delete=models.CASCADE, related_name='progressions')
    est_complete = models.BooleanField(default=False)
    date_debut = models.DateTimeField(auto_now_add=True)
    date_completion = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        unique_together = ['utilisateur', 'ressource']
        verbose_name = "Progression"
        verbose_name_plural = "Progressions"
    
    def __str__(self):
        status = "✅ Complété" if self.est_complete else "⏳ En cours"
        return f"{self.utilisateur.pseudonyme} - {self.ressource.titre} ({status})"


# ============= MODÈLES PSYCHOLOGUES ET CONSULTATIONS =============

class Psychologue(models.Model):
    """Profil psychologue créé par l'admin"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='psychologue_profile'
    )
    specialites = models.CharField(
        max_length=200, 
        help_text="Ex: Anxiété, Dépression, Stress - séparées par des virgules"
    )
    biographie = models.TextField(blank=True)
    experience_ans = models.IntegerField(default=0)
    est_actif = models.BooleanField(default=True)
    taux_reponse_moyen = models.FloatField(default=0.0)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Psychologue"
        verbose_name_plural = "Psychologues"
    
    def __str__(self):
        return f"Dr. {self.user.pseudonyme}"


class ConsultationRequest(models.Model):
    """Demande de consultation d'un utilisateur"""
    STATUS_CHOICES = [
        ('en_attente', '⏳ En attente'),
        ('confirmee', '✅ Confirmée'),
        ('rejetee', '❌ Rejetée'),
        ('completee', '🏁 Complétée'),
        ('annulee', '🚫 Annulée'),
    ]
    
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='consultation_requests'
    )
    psychologue = models.ForeignKey(
        Psychologue, 
        on_delete=models.CASCADE, 
        related_name='consultation_requests'
    )
    
    sujet = models.CharField(max_length=200)
    message = models.TextField(max_length=2000)
    statut = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='en_attente'
    )
    
    date_demande = models.DateTimeField(auto_now_add=True)
    date_reponse = models.DateTimeField(blank=True, null=True)
    
    reponse_psychologue = models.TextField(blank=True)
    date_prochaine_session = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date_demande']
        verbose_name = "Demande de consultation"
        verbose_name_plural = "Demandes de consultation"
    
    def __str__(self):
        return f"{self.utilisateur.pseudonyme} → {self.psychologue.user.pseudonyme} ({self.statut})"


class MessageConsultation(models.Model):
    """Messages échangés lors d'une consultation"""
    consultation = models.ForeignKey(
        ConsultationRequest, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contenu = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)
    est_lu = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['date_envoi']
        verbose_name = "Message de consultation"
        verbose_name_plural = "Messages de consultation"
    
    def __str__(self):
        return f"Message de {self.auteur.pseudonyme}"