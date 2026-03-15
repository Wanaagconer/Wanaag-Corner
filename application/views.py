from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import (
    ForumGroup, GroupMessage, GroupMemberStatus,
    CategorieRessource, Ressource, CommentaireRessource, ProgressionUtilisateur
)

def home(request):
    """Page d'accueil"""
    return render(request, 'application/home.html')

def register(request):
    """Page d'inscription"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data['email']
            user.save()
            login(request, user)
            messages.success(request, f'Bienvenue {user.pseudonyme} ! Votre compte a été créé avec succès.')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'application/register.html', {'form': form})

def user_login(request):
    """Page de connexion"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bon retour parmi nous, {user.pseudonyme} !')
                return redirect('dashboard')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'application/login.html', {'form': form})

@login_required
def dashboard(request):
    """Page après connexion"""
    return render(request, 'application/dashboard.html')

def about(request):
    """Page à propos de nous"""
    return render(request, 'application/about.html')

# ============= VUES DU FORUM =============

@login_required
def forum_home(request):
    """Page d'accueil du forum avec tous les groupes"""
    my_groups = []
    for group in request.user.joined_groups.all():
        unread_count = group.unread_count(request.user)
        last_msg = group.messages.last()
        my_groups.append({
            'group': group,
            'unread': unread_count,
            'last_message': last_msg
        })
    
    discover_groups = ForumGroup.objects.exclude(
        members=request.user
    ).annotate(
        member_count=Count('members')
    )[:6]
    
    context = {
        'my_groups': my_groups,
        'discover_groups': discover_groups,
    }
    return render(request, 'application/forum.html', context)


@login_required
def create_group(request):
    """Créer un nouveau groupe"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category = request.POST.get('category')
        
        group = ForumGroup.objects.create(
            name=name,
            description=description,
            category=category,
            creator=request.user
        )
        
        # Le créateur rejoint automatiquement le groupe
        group.members.add(request.user)
        GroupMemberStatus.objects.create(group=group, user=request.user)
        
        return JsonResponse({
            'success': True,
            'group_id': group.id,
            'message': 'Groupe créé avec succès!'
        })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


@login_required
def join_group(request, group_id):
    """Rejoindre un groupe"""
    group = get_object_or_404(ForumGroup, id=group_id)
    
    if request.user not in group.members.all():
        group.members.add(request.user)
        GroupMemberStatus.objects.create(group=group, user=request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'Vous avez rejoint {group.name}!'
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Vous êtes déjà membre de ce groupe'
    })


@login_required
def leave_group(request, group_id):
    """Quitter un groupe"""
    group = get_object_or_404(ForumGroup, id=group_id)
    
    if request.user in group.members.all():
        group.members.remove(request.user)
        GroupMemberStatus.objects.filter(group=group, user=request.user).delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Vous avez quitté {group.name}'
        })
    
    return JsonResponse({'success': False, 'message': 'Erreur'})


@login_required
def group_chat(request, group_id):
    """Page de chat d'un groupe"""
    group = get_object_or_404(ForumGroup, id=group_id)
    
    # Vérifier que l'utilisateur est membre
    if request.user not in group.members.all():
        return redirect('forum_home')
    
    # Récupérer tous les messages
    messages_list = group.messages.filter(is_deleted=False).select_related('sender')
    
    # Marquer comme lu
    status, created = GroupMemberStatus.objects.get_or_create(
        group=group, 
        user=request.user
    )
    status.last_read_at = timezone.now()
    status.save()
    
    context = {
        'group': group,
        'messages': messages_list,
        'members': group.members.all(),
    }
    return render(request, 'application/group_chat.html', context)


@login_required
def send_message(request, group_id):
    """Envoyer un message dans un groupe"""
    if request.method == 'POST':
        group = get_object_or_404(ForumGroup, id=group_id)
        
        # Vérifier que l'utilisateur est membre
        if request.user not in group.members.all():
            return JsonResponse({'success': False, 'message': 'Non autorisé'})
        
        content = request.POST.get('content', '').strip()
        if not content:
            return JsonResponse({'success': False, 'message': 'Message vide'})
        
        message = GroupMessage.objects.create(
            group=group,
            sender=request.user,
            content=content
        )
        
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'sender': request.user.pseudonyme,
            'content': content,
            'created_at': message.created_at.strftime('%H:%M')
        })
    
    return JsonResponse({'success': False})


@login_required
def get_messages(request, group_id):
    """Récupérer les nouveaux messages (pour le rafraîchissement automatique)"""
    group = get_object_or_404(ForumGroup, id=group_id)
    
    # Vérifier que l'utilisateur est membre
    if request.user not in group.members.all():
        return JsonResponse({'success': False})
    
    last_message_id = request.GET.get('last_message_id', 0)
    
    messages_list = group.messages.filter(
        id__gt=last_message_id,
        is_deleted=False
    ).select_related('sender').values(
        'id', 'content', 'sender__pseudonyme', 'created_at'
    )
    
    return JsonResponse({
        'success': True,
        'messages': list(messages_list)
    })


# ============= VUES DES RESSOURCES ÉDUCATIVES =============

@login_required
def ressources_home(request):
    """Page d'accueil des ressources éducatives"""
    # Récupérer les paramètres de recherche et filtrage
    search_query = request.GET.get('search', '')
    categorie_filter = request.GET.get('categorie', '')
    type_filter = request.GET.get('type', '')
    niveau_filter = request.GET.get('niveau', '')
    
    # Ressources publiées
    ressources = Ressource.objects.filter(est_publie=True)
    
    # Appliquer les filtres
    if search_query:
        ressources = ressources.filter(
            Q(titre__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(tags__icontains=search_query)
        )
    
    if categorie_filter:
        ressources = ressources.filter(categorie__slug=categorie_filter)
    
    if type_filter:
        ressources = ressources.filter(type_ressource=type_filter)
    
    if niveau_filter:
        ressources = ressources.filter(niveau=niveau_filter)
    
    # Récupérer les catégories
    categories = CategorieRessource.objects.all()
    
    # Ressources populaires
    ressources_populaires = Ressource.objects.filter(est_publie=True).order_by('-vues')[:6]
    
    # Ressources favorites de l'utilisateur
    mes_favoris = request.user.ressources_favorites.all()[:6]
    
    context = {
        'ressources': ressources,
        'categories': categories,
        'ressources_populaires': ressources_populaires,
        'mes_favoris': mes_favoris,
        'search_query': search_query,
        'categorie_filter': categorie_filter,
        'type_filter': type_filter,
        'niveau_filter': niveau_filter,
    }
    return render(request, 'application/ressources.html', context)


@login_required
def ressource_detail(request, slug):
    """Page de détail d'une ressource"""
    ressource = get_object_or_404(Ressource, slug=slug, est_publie=True)
    
    # Incrémenter les vues
    ressource.incrementer_vues()
    
    # Vérifier si l'utilisateur a ajouté en favori
    est_favori = request.user in ressource.favoris.all()
    
    # Vérifier la progression
    progression = ProgressionUtilisateur.objects.filter(
        utilisateur=request.user,
        ressource=ressource
    ).first()
    
    # Commentaires
    commentaires = ressource.commentaires.select_related('auteur').all()
    
    # Ressources similaires
    ressources_similaires = Ressource.objects.filter(
        categorie=ressource.categorie,
        est_publie=True
    ).exclude(id=ressource.id)[:4]
    
    context = {
        'ressource': ressource,
        'est_favori': est_favori,
        'progression': progression,
        'commentaires': commentaires,
        'ressources_similaires': ressources_similaires,
    }
    return render(request, 'application/ressource_detail.html', context)


@login_required
def toggle_favori(request, ressource_id):
    """Ajouter/retirer une ressource des favoris"""
    ressource = get_object_or_404(Ressource, id=ressource_id)
    
    if request.user in ressource.favoris.all():
        ressource.favoris.remove(request.user)
        est_favori = False
        message = 'Retiré des favoris'
    else:
        ressource.favoris.add(request.user)
        est_favori = True
        message = 'Ajouté aux favoris'
    
    return JsonResponse({
        'success': True,
        'est_favori': est_favori,
        'message': message
    })


@login_required
def marquer_complete(request, ressource_id):
    """Marquer une ressource comme complétée"""
    ressource = get_object_or_404(Ressource, id=ressource_id)
    
    progression, created = ProgressionUtilisateur.objects.get_or_create(
        utilisateur=request.user,
        ressource=ressource
    )
    
    progression.est_complete = not progression.est_complete
    if progression.est_complete:
        progression.date_completion = timezone.now()
    else:
        progression.date_completion = None
    progression.save()
    
    return JsonResponse({
        'success': True,
        'est_complete': progression.est_complete,
        'message': 'Ressource marquée comme complétée !' if progression.est_complete else 'Marqué comme non complété'
    })


@login_required
def ajouter_commentaire(request, ressource_id):
    """Ajouter un commentaire sur une ressource"""
    if request.method == 'POST':
        ressource = get_object_or_404(Ressource, id=ressource_id)
        contenu = request.POST.get('contenu', '').strip()
        
        if not contenu:
            return JsonResponse({'success': False, 'message': 'Commentaire vide'})
        
        commentaire = CommentaireRessource.objects.create(
            ressource=ressource,
            auteur=request.user,
            contenu=contenu
        )
        
        return JsonResponse({
            'success': True,
            'commentaire_id': commentaire.id,
            'auteur': request.user.pseudonyme,
            'contenu': contenu,
            'date': commentaire.date_creation.strftime('%d/%m/%Y à %H:%M')
        })
    
    return JsonResponse({'success': False})


@login_required
def mes_ressources(request):
    """Page des ressources de l'utilisateur (favoris et complétées)"""
    mes_favoris = request.user.ressources_favorites.filter(est_publie=True)
    
    mes_completions = ProgressionUtilisateur.objects.filter(
        utilisateur=request.user,
        est_complete=True
    ).select_related('ressource')
    
    mes_en_cours = ProgressionUtilisateur.objects.filter(
        utilisateur=request.user,
        est_complete=False
    ).select_related('ressource')
    
    context = {
        'mes_favoris': mes_favoris,
        'mes_completions': mes_completions,
        'mes_en_cours': mes_en_cours,
    }
    return render(request, 'application/mes_ressources.html', context)





# ============= AJOUTER CES VUES À VOTRE views.py =============

from .models import Psychologue, ConsultationRequest, MessageConsultation
from django.utils import timezone

# ============= VUES UTILISATEUR =============

@login_required
def psychologues_list(request):
    """Liste de tous les psychologues disponibles"""
    psychologues = Psychologue.objects.filter(est_actif=True).select_related('user')
    context = {
        'psychologues': psychologues,
    }
    return render(request, 'application/psychologues_list.html', context)


@login_required
def consultation_request_form(request, psychologue_id):
    """Formulaire pour demander une consultation"""
    psychologue = get_object_or_404(Psychologue, id=psychologue_id, est_actif=True)
    
    if request.method == 'POST':
        sujet = request.POST.get('sujet', '').strip()
        message = request.POST.get('message', '').strip()
        
        if not sujet or not message:
            messages.error(request, 'Le sujet et le message sont obligatoires')
            return redirect('consultation_request_form', psychologue_id=psychologue_id)
        
        # Vérifier qu'il n'y a pas déjà une demande en attente
        existing = ConsultationRequest.objects.filter(
            utilisateur=request.user,
            psychologue=psychologue,
            statut__in=['en_attente', 'confirmee']
        ).first()
        
        if existing:
            messages.warning(request, 'Vous avez déjà une demande en cours avec ce psychologue')
            return redirect('mes_consultations')
        
        consultation = ConsultationRequest.objects.create(
            utilisateur=request.user,
            psychologue=psychologue,
            sujet=sujet,
            message=message
        )
        
        messages.success(request, f'Votre demande a été envoyée à {psychologue.user.pseudonyme}!')
        return redirect('mes_consultations')
    
    context = {
        'psychologue': psychologue,
    }
    return render(request, 'application/consultation_request_form.html', context)


@login_required
def mes_consultations(request):
    """Page des consultations de l'utilisateur"""
    consultations = ConsultationRequest.objects.filter(
        utilisateur=request.user
    ).select_related('psychologue__user')
    
    context = {
        'consultations': consultations,
    }
    return render(request, 'application/mes_consultations.html', context)


@login_required
def consultation_detail(request, consultation_id):
    """Détail d'une consultation avec messages"""
    consultation = get_object_or_404(ConsultationRequest, id=consultation_id)
    
    # Vérifier que l'utilisateur est autorisé
    if request.user != consultation.utilisateur and request.user != consultation.psychologue.user:
        return redirect('home')
    
    if request.method == 'POST' and consultation.statut in ['confirmee', 'en_attente']:
        contenu = request.POST.get('contenu', '').strip()
        
        if contenu:
            MessageConsultation.objects.create(
                consultation=consultation,
                auteur=request.user,
                contenu=contenu
            )
            return redirect('consultation_detail', consultation_id=consultation_id)
    
    messages_list = consultation.messages.all()
    
    context = {
        'consultation': consultation,
        'messages': messages_list,
    }
    return render(request, 'application/consultation_detail.html', context)


# ============= VUES PSYCHOLOGUE =============

@login_required
def psychologue_dashboard(request):
    """Dashboard du psychologue"""
    # Vérifier que l'utilisateur est un psychologue
    psychologue = getattr(request.user, 'psychologue_profile', None)
    if not psychologue:
        return redirect('dashboard')
    
    # Consultations en attente
    en_attente = ConsultationRequest.objects.filter(
        psychologue=psychologue,
        statut='en_attente'
    ).count()
    
    # Consultations confirmées
    confirmees = ConsultationRequest.objects.filter(
        psychologue=psychologue,
        statut='confirmee'
    ).count()
    
    # Toutes les consultations
    consultations = ConsultationRequest.objects.filter(
        psychologue=psychologue
    ).order_by('-date_demande')[:10]
    
    context = {
        'psychologue': psychologue,
        'consultations_en_attente': en_attente,
        'consultations_confirmees': confirmees,
        'consultations': consultations,
    }
    return render(request, 'application/psychologue_dashboard.html', context)


@login_required
def consultation_requests_list(request):
    """Liste des demandes de consultation pour le psychologue"""
    psychologue = getattr(request.user, 'psychologue_profile', None)
    if not psychologue:
        return redirect('dashboard')
    
    status_filter = request.GET.get('status', '')
    consultations = ConsultationRequest.objects.filter(
        psychologue=psychologue
    )
    
    if status_filter:
        consultations = consultations.filter(statut=status_filter)
    
    context = {
        'consultations': consultations,
        'status_filter': status_filter,
    }
    return render(request, 'application/consultation_requests_list.html', context)


@login_required
def consultation_respond(request, consultation_id):
    """Répondre à une demande de consultation"""
    consultation = get_object_or_404(ConsultationRequest, id=consultation_id)
    
    # Vérifier que c'est le psychologue assigné
    if request.user != consultation.psychologue.user:
        return redirect('home')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirmer':
            consultation.statut = 'confirmee'
            consultation.date_reponse = timezone.now()
            consultation.save()
            messages.success(request, 'Consultation confirmée!')
        
        elif action == 'rejeter':
            raison = request.POST.get('raison', '').strip()
            consultation.statut = 'rejetee'
            consultation.date_reponse = timezone.now()
            consultation.reponse_psychologue = raison
            consultation.save()
            messages.success(request, 'Demande rejetée')
        
        elif action == 'programmer':
            date_session = request.POST.get('date_session')
            consultation.statut = 'confirmee'
            consultation.date_prochaine_session = date_session
            consultation.save()
            messages.success(request, f'Session programmée pour {date_session}')
        
        return redirect('consultation_requests_list')
    
    context = {
        'consultation': consultation,
    }
    return render(request, 'application/consultation_respond.html', context)


