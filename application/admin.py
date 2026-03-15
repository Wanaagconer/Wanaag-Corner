from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, ForumGroup, GroupMessage, GroupMemberStatus,
    CategorieRessource, Ressource, CommentaireRessource, ProgressionUtilisateur,
    Psychologue, ConsultationRequest, MessageConsultation
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['pseudonyme', 'email', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_active']
    search_fields = ['pseudonyme', 'email']
    ordering = ['-date_joined']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informations supplémentaires', {'fields': ('pseudonyme',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {'fields': ('pseudonyme', 'email')}),
    )


@admin.register(ForumGroup)
class ForumGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'creator', 'member_count', 'created_at', 'is_private']
    list_filter = ['category', 'is_private', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {}
    readonly_fields = ['created_at']
    filter_horizontal = ['members']


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'group', 'content_preview', 'created_at', 'is_deleted']
    list_filter = ['is_deleted', 'created_at']
    search_fields = ['content', 'sender__pseudonyme', 'group__name']
    readonly_fields = ['created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Aperçu'


@admin.register(GroupMemberStatus)
class GroupMemberStatusAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'joined_at', 'last_read_at']
    list_filter = ['joined_at']
    search_fields = ['user__pseudonyme', 'group__name']


@admin.register(CategorieRessource)
class CategorieRessourceAdmin(admin.ModelAdmin):
    list_display = ['icone', 'nom', 'slug', 'ordre']
    list_editable = ['ordre']
    prepopulated_fields = {'slug': ('nom',)}
    search_fields = ['nom']
    ordering = ['ordre', 'nom']


@admin.register(Ressource)
class RessourceAdmin(admin.ModelAdmin):
    list_display = ['titre', 'get_type_display', 'categorie', 'niveau', 'vues', 'est_publie', 'date_creation']
    list_filter = ['type_ressource', 'categorie', 'niveau', 'est_publie', 'date_creation']
    search_fields = ['titre', 'description', 'tags', 'intervenant']
    prepopulated_fields = {'slug': ('titre',)}
    readonly_fields = ['vues', 'date_creation', 'date_modification', 'places_restantes_display']
    filter_horizontal = ['favoris']
    
    fieldsets = (
        ('🎯 Informations principales', {
            'fields': ('titre', 'slug', 'type_ressource', 'categorie', 'niveau', 'description'),
            'description': '⚠️ Choisissez d\'abord le TYPE pour adapter les champs ci-dessous'
        }),
        ('📝 Contenu - Pour Article, Guide, Conférence', {
            'fields': ('contenu', 'image_couverture'),
            'classes': ('collapse',),
        }),
        ('🎥 Média - Pour Vidéo et Podcast', {
            'fields': ('lien_externe', 'fichier_audio'),
            'classes': ('collapse',),
            'description': 'Vidéo: lien YouTube | Podcast: lien Spotify OU fichier audio MP3'
        }),
        ('📅 Événement - Pour Formation, Atelier, Conférence', {
            'fields': ('date_debut', 'date_fin', 'lieu', 'intervenant', 'places_disponibles', 'places_restantes_display'),
            'classes': ('collapse',),
            'description': 'Remplissez ces champs pour les événements avec inscription'
        }),
        ('⚙️ Métadonnées', {
            'fields': ('auteur', 'duree_lecture', 'tags', 'est_publie')
        }),
        ('📊 Statistiques', {
            'fields': ('vues', 'favoris', 'date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    def get_type_display(self, obj):
        icons = {
            'article': '📝',
            'guide': '📖',
            'video': '🎥',
            'podcast': '🎧',
            'formation': '🎓',
            'atelier': '🛠️',
            'conference': '🎤',
        }
        return f"{icons.get(obj.type_ressource, '')} {obj.get_type_ressource_display()}"
    get_type_display.short_description = 'Type'
    
    def places_restantes_display(self, obj):
        if obj.is_evenement() and obj.places_disponibles:
            restantes = obj.places_restantes()
            if restantes is not None:
                if restantes == 0:
                    return "🔴 COMPLET"
                elif restantes <= 5:
                    return f"🟠 {restantes} places restantes"
                else:
                    return f"🟢 {restantes} places restantes"
            return "♾️ Illimité"
        return "-"
    places_restantes_display.short_description = 'Places restantes'


@admin.register(CommentaireRessource)
class CommentaireRessourceAdmin(admin.ModelAdmin):
    list_display = ['auteur', 'ressource', 'contenu_preview', 'date_creation', 'est_modifie']
    list_filter = ['est_modifie', 'date_creation']
    search_fields = ['contenu', 'auteur__pseudonyme', 'ressource__titre']
    readonly_fields = ['date_creation']
    
    def contenu_preview(self, obj):
        return obj.contenu[:50] + '...' if len(obj.contenu) > 50 else obj.contenu
    contenu_preview.short_description = 'Aperçu'


@admin.register(ProgressionUtilisateur)
class ProgressionUtilisateurAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'ressource', 'est_complete', 'date_debut', 'date_completion']
    list_filter = ['est_complete', 'date_debut']
    search_fields = ['utilisateur__pseudonyme', 'ressource__titre']
    readonly_fields = ['date_debut']


@admin.register(Psychologue)
class PsychologueAdmin(admin.ModelAdmin):
    list_display = ['get_pseudonyme', 'specialites', 'experience_ans', 'est_actif', 'date_creation']
    list_filter = ['est_actif', 'date_creation']
    search_fields = ['user__pseudonyme', 'specialites']
    readonly_fields = ['date_creation', 'taux_reponse_moyen']
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Informations professionnelles', {
            'fields': ('specialites', 'biographie', 'experience_ans')
        }),
        ('Statut', {
            'fields': ('est_actif', 'taux_reponse_moyen')
        }),
        ('Métadonnées', {
            'fields': ('date_creation',),
            'classes': ('collapse',)
        }),
    )
    
    def get_pseudonyme(self, obj):
        return obj.user.pseudonyme
    get_pseudonyme.short_description = 'Pseudonyme'


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'psychologue_name', 'sujet', 'statut', 'date_demande']
    list_filter = ['statut', 'date_demande', 'psychologue']
    search_fields = ['utilisateur__pseudonyme', 'psychologue__user__pseudonyme', 'sujet']
    readonly_fields = ['date_demande', 'date_reponse']
    
    fieldsets = (
        ('Demande initiale', {
            'fields': ('utilisateur', 'psychologue', 'sujet', 'message', 'date_demande')
        }),
        ('Statut et réponse', {
            'fields': ('statut', 'date_reponse', 'reponse_psychologue')
        }),
        ('Suivi', {
            'fields': ('date_prochaine_session',),
            'classes': ('collapse',)
        }),
    )
    
    def psychologue_name(self, obj):
        return obj.psychologue.user.pseudonyme
    psychologue_name.short_description = 'Psychologue'


@admin.register(MessageConsultation)
class MessageConsultationAdmin(admin.ModelAdmin):
    list_display = ['auteur', 'consultation', 'contenu_preview', 'date_envoi', 'est_lu']
    list_filter = ['est_lu', 'date_envoi']
    search_fields = ['contenu', 'auteur__pseudonyme']
    readonly_fields = ['date_envoi']
    
    def contenu_preview(self, obj):
        return obj.contenu[:50] + '...' if len(obj.contenu) > 50 else obj.contenu
    contenu_preview.short_description = 'Contenu'