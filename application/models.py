from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils.text import slugify

class CustomUser(AbstractUser):
    pseudonyme = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True, verbose_name="Photo de profil")
    bio = models.TextField(blank=True, max_length=300, verbose_name="Bio")

    # Pour l'authentification par email
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'pseudonyme']

    def __str__(self):
        return self.pseudonyme

    def nb_abonnes(self):
        return self.followers.count()

    def nb_abonnements(self):
        return self.following.count()

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'


class Follow(models.Model):
    """Abonnement entre utilisateurs"""
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following'
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['follower', 'following']
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"

    def __str__(self):
        return f"{self.follower.pseudonyme} → {self.following.pseudonyme}"


# ============= MODÈLES DU FORUM =============

class ForumGroup(models.Model):
    """Modèle pour les groupes de discussion"""
    CATEGORY_CHOICES = [
        ('anxiete', '💭 Anxiété'),
        ('depression', '💙 Dépression'),
        ('meditation', '🧘 Méditation'),
        ('famille', '👨‍👩‍👧‍👦 Famille'),
        ('developpement', '🌱 Développement personnel'),
        ('stress', '⚡ Stress & Burn-out'),
        ('trauma', '🛡️ Trauma & PTSD'),
        ('sommeil', '🌙 Troubles du sommeil'),
        ('relations', '💞 Relations & Amour'),
        ('deuil', '🕊️ Deuil & Perte'),
        ('confiance', '⭐ Confiance en soi'),
        ('addiction', '🔗 Addictions'),
        ('colere', '🔥 Gestion de la colère'),
        ('solitude', '🫂 Solitude & Isolement'),
        ('identite', '🌍 Identité & Culture'),
        ('jeunes', '🎓 Santé mentale des jeunes'),
        ('spiritualite', '✨ Spiritualité & Foi'),
        ('alimentation', '🥗 Alimentation & Image du corps'),
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
        ('article', 'Article'),
        ('guide', 'Guide pratique'),
        ('video', 'Vidéo'),
        ('podcast', 'Podcast'),
        ('formation', 'Formation'),
        ('atelier', 'Atelier'),
        ('conference', 'Conférence'),
    ]
    
    NIVEAU_CHOICES = [
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance', 'Avancé'),
    ]

    ACCES_CHOICES = [
        ('gratuit', 'Gratuit'),
        ('premium', 'Premium'),
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
    fichier_video = models.FileField(
        upload_to='videos/',
        blank=True,
        null=True,
        help_text="Fichier vidéo uploadé directement (MP4, MOV…)"
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
    acces = models.CharField(
        max_length=10,
        choices=ACCES_CHOICES,
        default='gratuit',
        verbose_name="Accès",
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
    photo = models.ImageField(
        upload_to='psychologues/',
        blank=True,
        null=True,
        verbose_name="Photo de profil"
    )
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
    TYPE_SEANCE_CHOICES = [
        ('presentiel', 'Présentiel'),
        ('visio', 'Visioconférence'),
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
    type_seance = models.CharField(
        max_length=15, choices=TYPE_SEANCE_CHOICES, default='presentiel',
        verbose_name="Type de séance"
    )
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


# ============= MODÈLES DES POSTS (STYLE INSTAGRAM) =============

class Post(models.Model):
    """Post publié par un utilisateur ou un psychologue"""
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    contenu = models.TextField(
        blank=True,
        verbose_name="Texte du post"
    )
    image = models.ImageField(
        upload_to='posts/',
        blank=True,
        null=True,
        verbose_name="Image"
    )
    video = models.FileField(
        upload_to='posts/videos/',
        blank=True,
        null=True,
        verbose_name="Vidéo"
    )
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='posts_aimes',
        blank=True
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Post"
        verbose_name_plural = "Posts"

    def __str__(self):
        return f"Post de {self.auteur.pseudonyme} - {self.date_creation.strftime('%d/%m/%Y')}"

    def nb_likes(self):
        return self.likes.count()

    def nb_commentaires(self):
        return self.commentaires_post.count()


class CommentairePost(models.Model):
    """Commentaire sur un post"""
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='commentaires_post'
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    contenu = models.TextField(max_length=500)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date_creation']
        verbose_name = "Commentaire de post"
        verbose_name_plural = "Commentaires de posts"

    def __str__(self):
        return f"Commentaire de {self.auteur.pseudonyme} sur post #{self.post.id}"


# ============= PARCOURS BIEN-ÊTRE =============

class JournalEntry(models.Model):
    HUMEUR_CHOICES = [
        ('5', 'Excellent'),
        ('4', 'Bien'),
        ('3', 'Moyen'),
        ('2', 'Difficile'),
        ('1', 'Terrible'),
    ]
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='journal_entries')
    titre = models.CharField(max_length=200, blank=True)
    contenu = models.TextField()
    humeur = models.CharField(max_length=2, choices=HUMEUR_CHOICES, default='3')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Entrée de journal"
        verbose_name_plural = "Entrées de journal"

    def __str__(self):
        return f"Journal de {self.utilisateur.pseudonyme} — {self.date_creation.strftime('%d/%m/%Y')}"


class QuoteInspirante(models.Model):
    texte = models.TextField()
    auteur = models.CharField(max_length=150, blank=True, default='Anonyme')
    categorie = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Citation inspirante"
        verbose_name_plural = "Citations inspirantes"

    def __str__(self):
        return f"{self.texte[:60]}… — {self.auteur}"


class ProfilSante(models.Model):
    SEXE_CHOICES = [('homme', 'Homme'), ('femme', 'Femme')]
    ACTIVITE_CHOICES = [
        ('sedentaire', 'Sédentaire'),
        ('leger', 'Légèrement actif (1-3j/sem)'),
        ('modere', 'Modérément actif (3-5j/sem)'),
        ('actif', 'Très actif (6-7j/sem)'),
        ('tres_actif', 'Extrêmement actif'),
    ]
    OBJECTIF_CHOICES = [
        ('perdre', 'Perdre du poids'),
        ('maintenir', 'Maintenir le poids'),
        ('prendre', 'Prendre du poids / Musculation'),
    ]
    utilisateur = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profil_sante')
    age = models.IntegerField()
    taille = models.IntegerField(help_text="Taille en cm")
    poids = models.FloatField(help_text="Poids en kg")
    sexe = models.CharField(max_length=10, choices=SEXE_CHOICES)
    niveau_activite = models.CharField(max_length=20, choices=ACTIVITE_CHOICES, default='modere')
    objectif = models.CharField(max_length=20, choices=OBJECTIF_CHOICES, default='maintenir')
    date_modification = models.DateTimeField(auto_now=True)

    def imc(self):
        h = self.taille / 100
        return round(self.poids / (h * h), 1)

    def imc_label(self):
        v = self.imc()
        if v < 18.5: return 'Insuffisance pondérale'
        if v < 25:   return 'Poids normal'
        if v < 30:   return 'Surpoids'
        return 'Obésité'

    def calories_jour(self):
        if self.sexe == 'homme':
            bmr = 88.362 + (13.397 * self.poids) + (4.799 * self.taille) - (5.677 * self.age)
        else:
            bmr = 447.593 + (9.247 * self.poids) + (3.098 * self.taille) - (4.330 * self.age)
        facteurs = {'sedentaire': 1.2, 'leger': 1.375, 'modere': 1.55, 'actif': 1.725, 'tres_actif': 1.9}
        tdee = bmr * facteurs.get(self.niveau_activite, 1.55)
        if self.objectif == 'perdre':   return int(tdee - 500)
        if self.objectif == 'prendre':  return int(tdee + 300)
        return int(tdee)

    class Meta:
        verbose_name = "Profil santé"
        verbose_name_plural = "Profils santé"

    def __str__(self):
        return f"Profil santé de {self.utilisateur.pseudonyme}"


class BlogBienEtre(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blogs_bien_etre')
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    image = models.ImageField(upload_to='blogs/', blank=True, null=True)
    tags = models.CharField(max_length=200, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    est_publie = models.BooleanField(default=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='blogs_aimes', blank=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Blog bien-être"
        verbose_name_plural = "Blogs bien-être"

    def nb_likes(self):
        return self.likes.count()

    def __str__(self):
        return self.titre


# ═══════════════════════════════════════════════════════════
#  CHATBOT IA — Wanaag
# ═══════════════════════════════════════════════════════════

class ChatSession(models.Model):
    MOOD_CHOICES = [
        ('unknown',  'Inconnu'),
        ('positif',  'Positif'),
        ('neutre',   'Neutre'),
        ('anxieux',  'Anxieux'),
        ('triste',   'Triste'),
        ('crisis',   'En crise'),
    ]

    utilisateur   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions'
    )
    session_key   = models.CharField(max_length=40, unique=True)
    mood_detected = models.CharField(max_length=20, choices=MOOD_CHOICES, default='unknown')
    crisis_flag   = models.BooleanField(default=False)
    started_at    = models.DateTimeField(auto_now_add=True)
    last_active   = models.DateTimeField(auto_now=True)
    is_active     = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_active']
        verbose_name = "Session de chat IA"
        verbose_name_plural = "Sessions de chat IA"

    def __str__(self):
        return f"Session {self.session_key[:8]}… — {self.utilisateur.pseudonyme}"

    def get_history_for_api(self, limit=20):
        msgs = self.messages.order_by('-sent_at')[:limit]
        return [{"role": m.role, "content": m.content} for m in reversed(list(msgs))]


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user',      'Utilisateur'),
        ('assistant', 'Assistant'),
    ]

    session     = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role        = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content     = models.TextField()
    sent_at     = models.DateTimeField(auto_now_add=True)
    crisis_flag = models.BooleanField(default=False)

    class Meta:
        ordering = ['sent_at']
        verbose_name = "Message chatbot IA"
        verbose_name_plural = "Messages chatbot IA"

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"