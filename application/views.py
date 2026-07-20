from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Sum
from django.utils import timezone
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import (
    ForumGroup, GroupMessage, GroupMemberStatus,
    CategorieRessource, Ressource, CommentaireRessource, ProgressionUtilisateur,
    Post, CommentairePost, Follow,
    ChatSession, ChatMessage,
)
import uuid, json


def admin_required(view_func):
    """Decorator: requires is_staff or is_superuser"""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

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
        'chat_messages': messages_list,
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
    search_query = request.GET.get('search', '')
    type_filter  = request.GET.get('type', '')
    acces_filter = request.GET.get('acces', 'gratuit')   # par défaut : gratuit

    ressources = Ressource.objects.filter(est_publie=True, acces=acces_filter)

    if search_query:
        ressources = ressources.filter(
            Q(titre__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(tags__icontains=search_query)
        )

    if type_filter:
        ressources = ressources.filter(type_ressource=type_filter)

    ressources_populaires = Ressource.objects.filter(
        est_publie=True, acces=acces_filter
    ).order_by('-vues')[:6]

    mes_favoris = request.user.ressources_favorites.all()[:6]

    context = {
        'ressources': ressources,
        'ressources_populaires': ressources_populaires,
        'mes_favoris': mes_favoris,
        'search_query': search_query,
        'type_filter': type_filter,
        'acces_filter': acces_filter,
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
        
        type_seance = request.POST.get('type_seance', 'presentiel')
        if type_seance not in ['presentiel', 'visio']:
            type_seance = 'presentiel'

        # Date souhaitée par le patient
        from django.utils.dateparse import parse_datetime
        date_souhaitee_str = request.POST.get('date_souhaitee', '').strip()
        date_souhaitee = None
        if date_souhaitee_str:
            date_souhaitee = parse_datetime(date_souhaitee_str)
            if date_souhaitee and timezone.is_naive(date_souhaitee):
                date_souhaitee = timezone.make_aware(date_souhaitee)

        consultation = ConsultationRequest.objects.create(
            utilisateur=request.user,
            psychologue=psychologue,
            sujet=sujet,
            message=message,
            type_seance=type_seance,
            date_prochaine_session=date_souhaitee,
        )
        
        messages.success(request, f'Votre demande a été envoyée à {psychologue.user.pseudonyme}!')
        return redirect('mes_consultations')
    
    context = {
        'psychologue': psychologue,
    }
    return render(request, 'application/consultation_request_form.html', context)


@login_required
def mes_consultations(request):
    """Page des consultations de l'utilisateur — psychologues interdits"""
    if hasattr(request.user, 'psychologue_profile') and request.user.psychologue_profile:
        return redirect('psychologue_dashboard')
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

    # Bouton visio : visible 30 min avant → 2h après l'heure de la séance
    can_join_visio = False
    if consultation.type_seance == 'visio' and consultation.statut == 'confirmee':
        if consultation.date_prochaine_session:
            from datetime import timedelta
            now = timezone.now()
            window_start = consultation.date_prochaine_session - timedelta(minutes=30)
            window_end   = consultation.date_prochaine_session + timedelta(hours=2)
            can_join_visio = window_start <= now <= window_end
        else:
            # Pas de date fixée → bouton toujours visible
            can_join_visio = True

    context = {
        'consultation': consultation,
        'chat_messages': messages_list,
        'can_join_visio': can_join_visio,
    }
    return render(request, 'application/consultation_detail.html', context)


# ============= VUES PSYCHOLOGUE =============

@login_required
def update_psy_photo(request):
    """Psychologue uploads/updates their profile photo"""
    from .models import Psychologue
    psychologue = getattr(request.user, 'psychologue_profile', None)
    if not psychologue:
        return JsonResponse({'success': False})
    if request.method == 'POST' and request.FILES.get('photo'):
        psychologue.photo = request.FILES['photo']
        psychologue.save()
        return JsonResponse({'success': True, 'url': psychologue.photo.url})
    return JsonResponse({'success': False})


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


# ============= VUES DES POSTS =============

@login_required
def posts_feed(request):
    """Feed principal - tous les posts de tous les utilisateurs"""
    posts = Post.objects.select_related('auteur').prefetch_related('likes', 'commentaires_post__auteur').all()

    # IDs des posts aimés par l'utilisateur courant
    liked_ids = set(request.user.posts_aimes.values_list('id', flat=True))
    following_ids = set(Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))

    context = {
        'posts': posts,
        'liked_ids': liked_ids,
        'following_ids': following_ids,
    }
    return render(request, 'application/posts.html', context)


@login_required
def create_post(request):
    """Créer un nouveau post"""
    if request.method == 'POST':
        contenu = request.POST.get('contenu', '').strip()
        image = request.FILES.get('image')

        video = request.FILES.get('video')
        if not contenu and not image and not video:
            return JsonResponse({'success': False, 'message': 'Le post doit contenir du texte, une image ou une vidéo.'})

        post = Post.objects.create(
            auteur=request.user,
            contenu=contenu,
            image=image,
            video=video,
        )

        return JsonResponse({
            'success': True,
            'post_id': post.id,
            'message': 'Post publié avec succès!'
        })

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


@login_required
def delete_post(request, post_id):
    """Supprimer son propre post"""
    post = get_object_or_404(Post, id=post_id, auteur=request.user)
    post.delete()
    return JsonResponse({'success': True, 'message': 'Post supprimé.'})


@login_required
def edit_post(request, post_id):
    """Modifier le contenu d'un post"""
    post = get_object_or_404(Post, id=post_id, auteur=request.user)
    if request.method == 'POST':
        data = json.loads(request.body)
        contenu = data.get('contenu', '').strip()
        post.contenu = contenu
        post.save()
        return JsonResponse({'success': True, 'contenu': post.contenu})
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée.'})


@login_required
def like_post(request, post_id):
    """Liker ou unliker un post"""
    post = get_object_or_404(Post, id=post_id)

    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True

    return JsonResponse({
        'success': True,
        'liked': liked,
        'nb_likes': post.nb_likes()
    })


@login_required
def commenter_post(request, post_id):
    """Ajouter un commentaire sur un post"""
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        contenu = request.POST.get('contenu', '').strip()

        if not contenu:
            return JsonResponse({'success': False, 'message': 'Commentaire vide'})

        commentaire = CommentairePost.objects.create(
            post=post,
            auteur=request.user,
            contenu=contenu
        )

        return JsonResponse({
            'success': True,
            'commentaire_id': commentaire.id,
            'auteur': request.user.pseudonyme,
            'contenu': contenu,
            'date': commentaire.date_creation.strftime('%d/%m/%Y à %H:%M'),
            'nb_commentaires': post.nb_commentaires()
        })

    return JsonResponse({'success': False})


@login_required
def visio_room(request, consultation_id):
    """Salle de visioconférence pour une consultation confirmée"""
    consultation = get_object_or_404(ConsultationRequest, id=consultation_id)
    # Only the patient or the psychologist can access
    is_patient = consultation.utilisateur == request.user
    is_psy = hasattr(request.user, 'psychologue_profile') and consultation.psychologue == request.user.psychologue_profile
    if not (is_patient or is_psy):
        return redirect('dashboard')
    if consultation.type_seance != 'visio' or consultation.statut != 'confirmee':
        return redirect('consultation_detail', consultation_id=consultation_id)
    return render(request, 'application/visio_room.html', {
        'consultation': consultation,
        'is_patient': is_patient,
        'room_name': f'wanaag-corner-{consultation_id}',
        'display_name': request.user.pseudonyme,
    })


# ============= PROFIL UTILISATEUR =============

_User = get_user_model()

@login_required
def profile(request):
    user = request.user
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_info':
            pseudo = request.POST.get('pseudonyme', '').strip()
            email = request.POST.get('email', '').strip()
            bio = request.POST.get('bio', '').strip()
            if pseudo and pseudo != user.pseudonyme:
                if _User.objects.filter(pseudonyme=pseudo).exclude(pk=user.pk).exists():
                    return JsonResponse({'success': False, 'message': 'Ce pseudonyme est déjà utilisé.'})
                user.pseudonyme = pseudo
            if email and email != user.email:
                if _User.objects.filter(email=email).exclude(pk=user.pk).exists():
                    return JsonResponse({'success': False, 'message': 'Cet email est déjà utilisé.'})
                user.email = email
                user.username = email
            user.bio = bio
            if request.FILES.get('photo'):
                user.photo = request.FILES['photo']
            user.save()
            return JsonResponse({'success': True, 'message': 'Profil mis à jour !'})
        elif action == 'change_password':
            old = request.POST.get('old_password', '')
            new1 = request.POST.get('new_password1', '')
            new2 = request.POST.get('new_password2', '')
            if not user.check_password(old):
                return JsonResponse({'success': False, 'message': 'Mot de passe actuel incorrect.'})
            if new1 != new2:
                return JsonResponse({'success': False, 'message': 'Les mots de passe ne correspondent pas.'})
            if len(new1) < 8:
                return JsonResponse({'success': False, 'message': 'Minimum 8 caractères.'})
            user.set_password(new1)
            user.save()
            update_session_auth_hash(request, user)
            return JsonResponse({'success': True, 'message': 'Mot de passe modifié !'})
    posts = user.posts.all()
    return render(request, 'application/profile.html', {
        'profile_user': user,
        'posts': posts,
        'is_own_profile': True,
        'nb_abonnes': user.nb_abonnes(),
        'nb_abonnements': user.nb_abonnements(),
    })


@login_required
def user_profile(request, user_id):
    profile_user = get_object_or_404(_User, pk=user_id)
    is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    posts = profile_user.posts.all()
    return render(request, 'application/profile.html', {
        'profile_user': profile_user,
        'posts': posts,
        'is_own_profile': profile_user == request.user,
        'is_following': is_following,
        'nb_abonnes': profile_user.nb_abonnes(),
        'nb_abonnements': profile_user.nb_abonnements(),
    })


@login_required
def follow_toggle(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    target = get_object_or_404(_User, pk=user_id)
    if target == request.user:
        return JsonResponse({'success': False, 'message': 'Impossible de vous abonner à vous-même.'})
    follow_obj, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        follow_obj.delete()
        following = False
    else:
        following = True
    return JsonResponse({'success': True, 'following': following, 'nb_abonnes': target.nb_abonnes()})


# ============= ADMIN PANEL VIEWS =============

@admin_required
def admin_panel(request):
    """Main admin dashboard with all data"""
    from .models import Psychologue, ConsultationRequest
    User = get_user_model()

    stats = {
        'total_users': User.objects.count(),
        'total_posts': Post.objects.count(),
        'total_groups': ForumGroup.objects.count(),
        'total_messages': GroupMessage.objects.count(),
        'total_ressources': Ressource.objects.count(),
        'total_consultations': ConsultationRequest.objects.count(),
        'consultations_en_attente': ConsultationRequest.objects.filter(statut='en_attente').count(),
        'total_psychologues': Psychologue.objects.count(),
        'total_categories': CategorieRessource.objects.count(),
        'total_vues': Ressource.objects.aggregate(t=Sum('vues'))['t'] or 0,
    }

    ressources = Ressource.objects.select_related('categorie', 'auteur').order_by('-date_creation')
    categories = CategorieRessource.objects.all()
    users = User.objects.order_by('-date_joined')
    psychologues = Psychologue.objects.select_related('user').all()
    consultations = ConsultationRequest.objects.select_related(
        'utilisateur', 'psychologue__user'
    ).order_by('-date_demande')
    posts = Post.objects.select_related('auteur').annotate(
        nb_likes_count=Count('likes', distinct=True),
        nb_com=Count('commentaires_post', distinct=True)
    ).order_by('-date_creation')
    groups = ForumGroup.objects.annotate(
        msg_count=Count('messages', distinct=True),
        member_count_ann=Count('members', distinct=True)
    ).order_by('-created_at')

    context = {
        'stats': stats,
        'ressources': ressources,
        'categories': categories,
        'users': users,
        'psychologues': psychologues,
        'consultations': consultations,
        'posts': posts,
        'groups': groups,
        'type_choices': Ressource.TYPE_CHOICES,
        'niveau_choices': Ressource.NIVEAU_CHOICES,
    }
    return render(request, 'application/admin_dashboard.html', context)


@admin_required
def admin_create_ressource(request):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    titre = request.POST.get('titre', '').strip()
    if not titre:
        return JsonResponse({'success': False, 'message': 'Titre requis'})
    categorie_id = request.POST.get('categorie_id')
    categorie = CategorieRessource.objects.filter(id=categorie_id).first() if categorie_id else None
    ressource = Ressource.objects.create(
        titre=titre,
        description=request.POST.get('description', '').strip(),
        type_ressource=request.POST.get('type_ressource', 'article'),
        acces=request.POST.get('acces', 'gratuit'),
        duree_lecture=int(request.POST.get('duree_lecture', 5) or 5),
        categorie=categorie,
        lien_externe=request.POST.get('lien_externe', '').strip() or None,
        contenu=request.POST.get('contenu', '').strip(),
        est_publie=request.POST.get('est_publie') == 'true',
        tags=request.POST.get('tags', '').strip(),
        image_couverture=request.FILES.get('image_couverture'),
        auteur=request.user,
    )
    return JsonResponse({
        'success': True, 'id': ressource.id, 'titre': ressource.titre,
        'type': ressource.get_type_ressource_display(),
        'categorie': str(ressource.categorie) if ressource.categorie else '—',
        'publie': ressource.est_publie,
    })


@admin_required
def admin_get_ressource(request, ressource_id):
    r = get_object_or_404(Ressource, id=ressource_id)
    return JsonResponse({
        'success': True,
        'id': r.id, 'titre': r.titre, 'description': r.description,
        'type_ressource': r.type_ressource, 'acces': r.acces,
        'duree_lecture': r.duree_lecture,
        'categorie_id': r.categorie.id if r.categorie else '',
        'lien_externe': r.lien_externe or '',
        'contenu': r.contenu, 'est_publie': r.est_publie, 'tags': r.tags,
    })


@admin_required
def admin_update_ressource(request, ressource_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    r = get_object_or_404(Ressource, id=ressource_id)
    r.titre = request.POST.get('titre', r.titre).strip()
    r.description = request.POST.get('description', r.description).strip()
    r.type_ressource = request.POST.get('type_ressource', r.type_ressource)
    r.niveau = request.POST.get('niveau', r.niveau)
    r.duree_lecture = int(request.POST.get('duree_lecture', r.duree_lecture) or r.duree_lecture)
    r.lien_externe = request.POST.get('lien_externe', '').strip() or None
    r.contenu = request.POST.get('contenu', r.contenu).strip()
    r.est_publie = request.POST.get('est_publie') == 'true'
    r.tags = request.POST.get('tags', r.tags).strip()
    categorie_id = request.POST.get('categorie_id')
    r.categorie = CategorieRessource.objects.filter(id=categorie_id).first() if categorie_id else None
    if request.FILES.get('image_couverture'):
        r.image_couverture = request.FILES['image_couverture']
    r.save()
    return JsonResponse({'success': True, 'titre': r.titre, 'publie': r.est_publie})


@admin_required
def admin_delete_ressource(request, ressource_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    get_object_or_404(Ressource, id=ressource_id).delete()
    return JsonResponse({'success': True})


@admin_required
def admin_create_categorie(request):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    nom = request.POST.get('nom', '').strip()
    if not nom:
        return JsonResponse({'success': False, 'message': 'Nom requis'})
    cat = CategorieRessource.objects.create(
        nom=nom,
        description=request.POST.get('description', '').strip(),
        icone=request.POST.get('icone', '📚').strip(),
        ordre=int(request.POST.get('ordre', 0) or 0),
    )
    return JsonResponse({'success': True, 'id': cat.id, 'nom': cat.nom, 'icone': cat.icone})


@admin_required
def admin_update_categorie(request, categorie_id):
    cat = get_object_or_404(CategorieRessource, id=categorie_id)
    if request.method == 'GET':
        return JsonResponse({
            'success': True, 'id': cat.id, 'nom': cat.nom,
            'description': cat.description, 'icone': cat.icone, 'ordre': cat.ordre,
        })
    cat.nom = request.POST.get('nom', cat.nom).strip()
    cat.description = request.POST.get('description', cat.description).strip()
    cat.icone = request.POST.get('icone', cat.icone).strip()
    cat.ordre = int(request.POST.get('ordre', cat.ordre) or cat.ordre)
    cat.save()
    return JsonResponse({'success': True, 'nom': cat.nom, 'icone': cat.icone})


@admin_required
def admin_delete_categorie(request, categorie_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    get_object_or_404(CategorieRessource, id=categorie_id).delete()
    return JsonResponse({'success': True})


@admin_required
def admin_update_user(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    User = get_user_model()
    user = get_object_or_404(User, id=user_id)
    action = request.POST.get('action')
    if action == 'toggle_active':
        if user == request.user:
            return JsonResponse({'success': False, 'message': 'Impossible'})
        user.is_active = not user.is_active
        user.save()
        return JsonResponse({'success': True, 'is_active': user.is_active})
    if action == 'toggle_staff':
        if user == request.user:
            return JsonResponse({'success': False, 'message': 'Impossible'})
        user.is_staff = not user.is_staff
        user.save()
        return JsonResponse({'success': True, 'is_staff': user.is_staff})
    return JsonResponse({'success': False})


@admin_required
def admin_delete_user(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    User = get_user_model()
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        return JsonResponse({'success': False, 'message': 'Impossible de se supprimer soi-même'})
    user.delete()
    return JsonResponse({'success': True})


@admin_required
def admin_create_psychologue(request):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    from .models import Psychologue
    User = get_user_model()
    user_id = request.POST.get('user_id')
    user = get_object_or_404(User, id=user_id)
    if hasattr(user, 'psychologue_profile'):
        return JsonResponse({'success': False, 'message': 'Déjà psychologue'})
    psychologue = Psychologue.objects.create(
        user=user,
        specialites=request.POST.get('specialites', ''),
        biographie=request.POST.get('biographie', ''),
        experience_ans=int(request.POST.get('experience_ans', 0) or 0),
    )
    return JsonResponse({
        'success': True, 'id': psychologue.id,
        'nom': user.pseudonyme, 'specialites': psychologue.specialites
    })


@admin_required
def admin_update_psychologue(request, psychologue_id):
    from .models import Psychologue
    psychologue = get_object_or_404(Psychologue, id=psychologue_id)
    if request.method == 'GET':
        return JsonResponse({
            'success': True, 'id': psychologue.id,
            'user_id': psychologue.user.id, 'nom': psychologue.user.pseudonyme,
            'specialites': psychologue.specialites, 'biographie': psychologue.biographie,
            'experience_ans': psychologue.experience_ans, 'est_actif': psychologue.est_actif,
        })
    psychologue.specialites = request.POST.get('specialites', psychologue.specialites)
    psychologue.biographie = request.POST.get('biographie', psychologue.biographie)
    psychologue.experience_ans = int(request.POST.get('experience_ans', psychologue.experience_ans) or 0)
    psychologue.est_actif = request.POST.get('est_actif') == 'true'
    if request.FILES.get('photo'):
        psychologue.photo = request.FILES['photo']
    psychologue.save()
    return JsonResponse({'success': True})


@admin_required
def admin_delete_psychologue(request, psychologue_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    from .models import Psychologue
    get_object_or_404(Psychologue, id=psychologue_id).delete()
    return JsonResponse({'success': True})


@admin_required
def admin_delete_post_action(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    get_object_or_404(Post, id=post_id).delete()
    return JsonResponse({'success': True})


@admin_required
def admin_delete_group_action(request, group_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    get_object_or_404(ForumGroup, id=group_id).delete()
    return JsonResponse({'success': True})


@admin_required
def admin_update_consultation(request, consultation_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    from .models import ConsultationRequest
    consultation = get_object_or_404(ConsultationRequest, id=consultation_id)
    statut = request.POST.get('statut')
    valid = ['en_attente', 'confirmee', 'rejetee', 'completee', 'annulee']
    if statut in valid:
        consultation.statut = statut
        consultation.save()
        return JsonResponse({'success': True, 'statut': consultation.get_statut_display()})
    return JsonResponse({'success': False})


# ============= PARCOURS BIEN-ÊTRE =============

from .models import JournalEntry, QuoteInspirante, ProfilSante, BlogBienEtre
import random
from datetime import timedelta, date

# 50 inspirational quotes about mental health / wellness
QUOTES_DATA = [
    ("La santé mentale est une richesse, prenez-en soin.", "Wanaag Corner", "bien-être"),
    ("Chaque jour est une nouvelle chance de recommencer.", "Anonyme", "résilience"),
    ("Prendre soin de soi n'est pas un luxe, c'est une nécessité.", "Anonyme", "bien-être"),
    ("La guérison n'est pas linéaire. C'est normal d'avoir des hauts et des bas.", "Anonyme", "guérison"),
    ("Tu n'as pas à être parfait pour être précieux.", "Anonyme", "confiance"),
    ("Respire. Tu es plus fort que tu ne le crois.", "Anonyme", "résilience"),
    ("Le courage ne signifie pas l'absence de peur, mais avancer malgré elle.", "Nelson Mandela", "motivation"),
    ("Vous méritez la paix intérieure que vous offrez aux autres.", "Anonyme", "bien-être"),
    ("Votre santé mentale compte plus que votre productivité.", "Anonyme", "bien-être"),
    ("Un pas à la fois. Vous y arriverez.", "Anonyme", "motivation"),
    ("La gentillesse envers soi-même est la base de tout progrès.", "Anonyme", "confiance"),
    ("Il est courageux de demander de l'aide.", "Anonyme", "guérison"),
    ("Vous n'êtes pas vos pensées. Vous les observez.", "Anonyme", "paix"),
    ("Chaque coucher de soleil est une invitation à recommencer.", "Anonyme", "espoir"),
    ("La douleur d'aujourd'hui est la force de demain.", "Anonyme", "résilience"),
    ("Soyez patient avec vous-même. La transformation prend du temps.", "Anonyme", "guérison"),
    ("Votre valeur ne dépend pas de votre performance.", "Anonyme", "confiance"),
    ("Ce que vous ressentez est valide.", "Anonyme", "bien-être"),
    ("La méditation est un voyage vers soi-même.", "Anonyme", "paix"),
    ("Nourrir son corps, c'est nourrir son esprit.", "Anonyme", "santé"),
    ("Le repos est productif.", "Anonyme", "bien-être"),
    ("Vous avez survécu à 100% de vos mauvais jours.", "Anonyme", "résilience"),
    ("L'amour de soi est le début de toute autre forme d'amour.", "Oscar Wilde", "amour"),
    ("Votre présence dans ce monde a de la valeur.", "Anonyme", "confiance"),
    ("La vulnérabilité est une force, pas une faiblesse.", "Brené Brown", "confiance"),
    ("Prenez le temps de vous reconnecter à vous-même.", "Anonyme", "bien-être"),
    ("Chaque émotion a sa raison d'être. Écoutez-la.", "Anonyme", "santé"),
    ("La joie se cultive, elle ne tombe pas du ciel.", "Anonyme", "bonheur"),
    ("Soyez doux avec votre âme.", "Anonyme", "bien-être"),
    ("Le changement commence par un petit pas courageux.", "Anonyme", "motivation"),
    ("Vous n'avez pas à tout régler aujourd'hui.", "Anonyme", "paix"),
    ("La gratitude transforme ce que vous avez en suffisance.", "Anonyme", "bonheur"),
    ("Prendre de l'espace pour soi n'est pas égoïste.", "Anonyme", "bien-être"),
    ("Votre histoire n'est pas terminée.", "Anonyme", "espoir"),
    ("L'exercice est une célébration de ce que votre corps peut faire.", "Anonyme", "santé"),
    ("Dormir est un acte de soin envers soi-même.", "Anonyme", "santé"),
    ("Chaque respiration consciente vous ramène au présent.", "Anonyme", "paix"),
    ("Vous êtes assez tel que vous êtes.", "Anonyme", "confiance"),
    ("La santé mentale est la base de toute autre santé.", "OMS", "bien-être"),
    ("Chercher de l'aide est un signe de sagesse.", "Anonyme", "guérison"),
    ("Le silence intérieur est une forme de pouvoir.", "Anonyme", "paix"),
    ("Votre bonheur mérite d'être prioritaire.", "Anonyme", "bonheur"),
    ("La régularité vaut mieux que l'intensité.", "Anonyme", "motivation"),
    ("Chaque repas sain est un cadeau que vous vous offrez.", "Anonyme", "santé"),
    ("Les liens humains nourrissent l'âme.", "Anonyme", "relations"),
    ("Parler de sa santé mentale brise les chaînes du silence.", "Anonyme", "guérison"),
    ("Vous avez le droit de vous sentir bien.", "Anonyme", "bien-être"),
    ("L'équilibre n'est pas une destination, c'est une pratique.", "Anonyme", "bien-être"),
    ("Se connaître soi-même est le début de la sagesse.", "Socrate", "confiance"),
    ("Un journal intime est une conversation avec soi-même.", "Anonyme", "bien-être"),
]


def _seed_quotes():
    """Populate quotes if DB is empty"""
    if QuoteInspirante.objects.count() < 10:
        QuoteInspirante.objects.bulk_create([
            QuoteInspirante(texte=t, auteur=a, categorie=c)
            for t, a, c in QUOTES_DATA
        ])


def _generate_meal_plan(profil, day_idx=0):
    """Generate rotating daily meal plan — 7 variations per objective"""
    cal = profil.calories_jour()
    obj = profil.objectif
    b  = int(cal * 0.25)   # breakfast
    l  = int(cal * 0.35)   # lunch
    d  = int(cal * 0.30)   # dinner
    cs = int(cal * 0.05)   # snack x2

    JOURS  = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    THEMES = {
        'perdre':    ['Fibres & Légèreté', 'Protéines & Détox', 'Méditerranéen', 'Force & Récup',
                      'Végétal & Vitalité', 'Plaisir Sain', 'Reset & Bilan'],
        'prendre':   ['Puissance Matinale', 'Construction Musculaire', 'Énergie Maximale',
                      'Récupération Active', 'Hypertrophie', 'Week-end Chargé', 'Supercompensation'],
        'maintenir': ['Équilibre Parfait', 'Diversité Nutritive', 'Vitalité Méditerranéenne',
                      'Sport & Nutrition', 'Légèreté & Plaisir', 'Saveurs du Monde', 'Reset Hebdomadaire'],
    }

    petits_dej = {
        'perdre': [
            {'items': ["Flocons d'avoine 60g au lait végétal", "Myrtilles 80g", "Thé vert"],             'conseil': 'Fibres + antioxydants = satiété longue durée'},
            {'items': ["Smoothie épinards-banane-lait d'amande 300ml", "2 galettes de riz"],              'conseil': 'Chlorophylle matinale = boost naturel'},
            {'items': ["Yaourt grec 0% 150g + granola 20g", "Framboises 80g", "Café sans sucre"],         'conseil': 'Probiotiques pour le microbiote'},
            {'items': ["Pancakes avoine-banane (100g farine+1 oeuf)", "Sirop d'érable 1cc", "Thé vert"], 'conseil': "Glucides complexes avant l'effort"},
            {'items': ["Chia pudding 30g + lait amande", "Mangue fraîche 80g", "Thé blanc"],              'conseil': 'Oméga-3 végétaux du chia'},
            {'items': ["2 oeufs brouillés sur pain complet grillé", "Tomates cerises + avocat ¼"],        'conseil': 'Protéines solides dès le matin'},
            {'items': ["Porridge pomme-cannelle 60g", "Yaourt 0% 100g", "Noix 10g", "Thé vert"],          'conseil': 'Douceur & récupération nutritionnelle'},
        ],
        'prendre': [
            {'items': ["Canjeero 2p + miel + beurre cacahuète", "3 oeufs brouillés", "Lait entier 250ml", "Dattes 5p"],  'conseil': 'Calories denses pour démarrer fort'},
            {'items': ["Porridge banane-avoine + whey 1 scoop", "Noix mélangées 30g", "Lait entier"],                    'conseil': 'Protéines + glucides = anabolisme matinal'},
            {'items': ["Pain complet 3 tranches + beurre d'amande", "2 oeufs pochés", "Jus d'orange 200ml"],             'conseil': 'Énergie dense pour séances intenses'},
            {'items': ["Smoothie mass : banane, avoine, lait, cacao", "Toast complet + avocat", "2 oeufs"],              'conseil': '800+ kcal pour soutenir la masse'},
            {'items': ["Omelette 3 oeufs + jambon + fromage", "Pain complet 2 tranches", "Jus de fruit 200ml"],          'conseil': 'Protéines complètes dès le matin'},
            {'items': ["Pancakes protéinés (avoine+whey+banane)", "Miel + fruits secs", "Lait entier"],                  'conseil': 'Week-end = recharge glycogène'},
            {'items': ["Gaufres avoine-banane", "Sirop d'érable + noix", "Lait entier 300ml", "2 oeufs brouillés"],     'conseil': 'Supercompensation : recharger les réserves'},
        ],
        'maintenir': [
            {'items': ["Canjeero 1-2p avec miel", "Oeuf à la coque 2", "Shaah (thé somali)", "1 fruit frais"],  'conseil': 'Équilibre protéines et glucides'},
            {'items': ["Yaourt grec + granola + fruits de saison", "Café ou thé léger"],                         'conseil': 'Diversité nutritive dès le réveil'},
            {'items': ["Pain complet 2 tranches + houmous", "Tomates + concombre", "Café"],                      'conseil': 'Végétal et équilibré'},
            {'items': ["Flocons d'avoine + fruits secs 20g", "Oeuf dur 1", "Thé ou café"],                       'conseil': 'Carburant avant la séance du jour'},
            {'items': ["Chia pudding + fruits rouges", "Toast + beurre d'amande 1cc", "Thé vert"],               'conseil': 'Légèreté et vitalité'},
            {'items': ["2 oeufs brouillés + toast complet", "Salade de fruits frais", "Café"],                   'conseil': 'Plaisir du week-end sans excès'},
            {'items': ["Porridge aux noix et fruits secs", "Yaourt nature", "Thé relaxant"],                     'conseil': 'Douceur dominicale et récupération'},
        ],
    }

    dejeuners = {
        'perdre': [
            {'items': ['Riz complet 100g', 'Poulet grillé 150g', 'Courgettes sautées', 'Salade verte'],                        'conseil': 'Assiette 50% légumes, 25% protéines'},
            {'items': ['Quinoa 100g', 'Saumon grillé 130g', 'Brocolis vapeur', 'Citron'],                                       'conseil': 'Oméga-3 + protéines complètes'},
            {'items': ['Salade niçoise (thon, oeuf, haricots verts, tomates)', 'Pain complet 2 tranches'],                      'conseil': 'Complet et faible en calories vides'},
            {'items': ['Poulet rôti aux herbes 160g', 'Patate douce rôtie 150g', 'Épinards sautés'],                            'conseil': 'Patate douce = IG bas, énergie stable'},
            {'items': ['Bowl Buddha : quinoa, pois chiches, avocat ½, légumes rôtis', 'Sauce tahini 1cs'],                      'conseil': 'Protéines végétales + bons lipides'},
            {'items': ['Pavé de saumon 130g', 'Riz basmati 100g', 'Salade verte + vinaigrette légère'],                         'conseil': 'Repas plaisir dans les objectifs'},
            {'items': ['Poulet fermier rôti 160g', 'Légumes du jardin rôtis (poivrons, courgettes)', 'Pain complet'],           'conseil': 'Clôture de semaine saine et savoureuse'},
        ],
        'prendre': [
            {'items': ['Skoudehkaris grande portion (riz 180g + viande 200g)', 'Salade avocat-huile olive', 'Jus fruits 250ml'], 'conseil': 'Glucides + protéines = prise de masse'},
            {'items': ['Pâtes complètes 150g + bolognaise boeuf 180g', 'Parmesan 20g', 'Salade verte'],                         'conseil': 'Carburant pour la croissance musculaire'},
            {'items': ['Riz blanc 150g + poulet mariné 200g', 'Légumes sautés', 'Yaourt entier'],                                'conseil': 'Volume calorique élevé, protéines max'},
            {'items': ['Pain complet 4 tranches + thon 160g + avocat', 'Soupe lentilles 250ml'],                                 'conseil': 'Récupération : glucides + protéines'},
            {'items': ['Steak boeuf 200g + pommes de terre rôties 200g', 'Épinards sautés', 'Pain'],                             'conseil': "Protéines nobles pour l'hypertrophie"},
            {'items': ['Burger maison : steak + pain complet + avocat + oeuf', 'Frites patate douce'],                           'conseil': 'Repas plaisir calorique du week-end'},
            {'items': ['Riz basmati 150g + curry de poulet aux légumes', 'Yaourt entier + miel', 'Pain'],                        'conseil': 'Supercompensation glycogène'},
        ],
        'maintenir': [
            {'items': ['Riz basmati 120g + sauce tomate maison', 'Poisson ou viande 150g', 'Légumes variés'],      'conseil': '½ légumes, ¼ glucides, ¼ protéines'},
            {'items': ['Quinoa 100g + crevettes 130g + avocat', 'Citron et herbes fraîches'],                       'conseil': 'Diversité nutritive et gourmande'},
            {'items': ['Pasta complète 120g + sauce végétarienne', 'Salade grecque (feta, olives, tomates)'],       'conseil': 'Méditerranéen = santé cardiovasculaire'},
            {'items': ['Poulet rôti 160g + riz complet 120g', 'Légumes vapeur', 'Citron'],                          'conseil': "Carburant adapté à l'entraînement"},
            {'items': ['Wrap complet : poulet + crudités + avocat', 'Soupe légère maison'],                         'conseil': 'Léger, rapide et satisfaisant'},
            {'items': ['Couscous de semoule 120g + merguez 2', 'Légumes grillés', 'Harissa légère'],                'conseil': 'Saveurs du monde en équilibre'},
            {'items': ['Riz sauvage + poisson blanc vapeur 150g', 'Légumes rôtis', 'Salade verte'],                 'conseil': 'Bilan de semaine nutritif et léger'},
        ],
    }

    diners = {
        'perdre': [
            {'items': ['Soupe légumes maison', 'Pain complet 1 tranche', '2 oeufs pochés'],                    'conseil': 'Repas léger avant 20h pour la digestion'},
            {'items': ['Salade de lentilles corail', 'Concombre + tomates cerises', 'Pain seigle'],            'conseil': 'Protéines végétales = bonne satiété'},
            {'items': ['Wok légumes (poivrons, champignons, épinards)', 'Tofu 100g', 'Riz complet 60g'],       'conseil': 'Cuisson rapide qui préserve les vitamines'},
            {'items': ['Velouté courgettes lait de coco léger', '2 oeufs à la coque', 'Pain seigle'],          'conseil': 'Protéines du soir pour la reconstruction'},
            {'items': ['Gaspacho maison (tomates, concombre, poivron)', 'Tartine pain complet + cream cheese'], 'conseil': 'Soupe froide = hydratation + vitamines'},
            {'items': ['Soupe miso légère', 'Tofu grillé 100g', 'Légumes marinés', 'Riz complet 50g'],         'conseil': 'Asiatique = faible en calories, riche en goût'},
            {'items': ['Velouté de potiron', 'Poisson vapeur 120g', 'Pain complet 1 tranche'],                 'conseil': 'Fermer la semaine avec légèreté'},
        ],
        'prendre': [
            {'items': ['Poulet rôti 200g + pommes de terre', 'Légumineuses 100g', 'Riz blanc ou pain'],         'conseil': 'Glucides + protéines = récupération musculaire'},
            {'items': ['Steak haché 200g + quinoa 120g', 'Épinards sautés', 'Yaourt entier'],                   'conseil': 'Synthèse protéique nocturne optimale'},
            {'items': ['Saumon grillé 180g + riz complet 130g', 'Légumes rôtis', 'Fromage blanc'],              'conseil': 'Oméga-3 + protéines pour la nuit'},
            {'items': ['Omelette 4 oeufs + fromage + légumes', 'Pain complet 2 tranches', 'Lait entier'],       'conseil': 'Caséine = récupération nocturne lente'},
            {'items': ['Curry de poulet 200g + riz basmati 150g', 'Légumes du curry', 'Yaourt raïta'],          'conseil': 'Dîner calorique = croissance nocturne'},
            {'items': ['Pizza maison : pâte complète + mozzarella + légumes + jambon', 'Salade verte'],         'conseil': 'Plaisir week-end = moral + calories'},
            {'items': ['Pâtes complètes 150g + sauce bolognaise maison', 'Parmesan 30g', 'Salade'],             'conseil': 'Supercompensation glycogène nocturne'},
        ],
        'maintenir': [
            {'items': ['Soupe légumes + légumineuses', 'Pain somali ou riz léger', 'Tisane camomille'],  'conseil': 'Modéré pour une bonne nuit de sommeil'},
            {'items': ['Poisson blanc vapeur 150g + quinoa 100g', 'Légumes vapeur', 'Citron'],           'conseil': 'Protéines légères pour bien dormir'},
            {'items': ['Salade méditerranéenne + pain pita complet', 'Olives + feta'],                    'conseil': 'Légèreté méditerranéenne du soir'},
            {'items': ['Soupe lentilles 300ml', 'Oeuf dur 1', 'Pain complet', 'Tisane'],                 'conseil': 'Récupération post-entraînement'},
            {'items': ['Riz complet 100g + wok légumes + crevettes 120g', 'Sauce soja légère'],          'conseil': 'Vendredi léger = bonne récupération'},
            {'items': ['Tajine de légumes maison + semoule 100g', 'Yaourt nature'],                       'conseil': 'Saveurs du monde, équilibre garanti'},
            {'items': ['Soupe détox (gingembre, citron, légumes)', 'Toast complet + avocat', 'Tisane'],  'conseil': 'Reset du dimanche pour repartir lundi'},
        ],
    }

    collations_matin = {
        'perdre':    [["Amandes 15g", "Eau citronnée"],
                      ["Orange ou pamplemousse", "Yaourt 0% 100g"],
                      ["Noix 15g", "1 kiwi"],
                      ["Amandes + noix du Brésil 20g", "1 mandarine"],
                      ["1 pomme + 5 amandes"],
                      ["Smoothie fruits rouges + yaourt", "1 galette de riz"],
                      ["Smoothie vert (épinards, kiwi, concombre)", "1 toast complet"]],
        'prendre':   [["Smoothie banane-arachide-lait entier", "1 barre de céréales"],
                      ["Shake protéiné 30g + banane", "Toast beurre de cacahuète"],
                      ["Banane + noix mélangées 30g", "Lait entier 200ml"],
                      ["Fromage blanc + miel + noix", "Jus d'orange 200ml"],
                      ["Barre protéinée maison + dattes 5p"],
                      ["Smoothie mass : banane, avoine, lait entier 300ml"],
                      ["Fromage blanc entier + fruits secs 30g", "Jus 150ml"]],
        'maintenir': [["Fruits secs 20g", "Eau"],
                      ["Yaourt + fruits frais de saison"],
                      ["Poignée noix mélangées 20g", "Eau citronnée"],
                      ["1 banane + café léger"],
                      ["1 kiwi + noix 15g"],
                      ["Smoothie léger + granola 20g"],
                      ["Tisane + galette riz + confiture légère"]],
    }

    collations_soir = {
        'perdre':    [["Yaourt nature 0% 150g", "1 pomme verte"],
                      ["Carotte bâtonnets + houmous 1cs"],
                      ["Fromage blanc 0% + cannelle", "1 poire"],
                      ["Shake protéiné léger 150ml", "1 banane"],
                      ["Yaourt nature 0%", "Myrtilles 50g"],
                      ["2 carrés chocolat noir 70%", "1 poire"],
                      ["Fromage blanc + miel + noix", "1 kiwi"]],
        'prendre':   [["Fromage blanc entier + miel", "Noix 30g", "Lait chaud"],
                      ["Barre protéinée + verre de lait entier"],
                      ["Yaourt grec entier + granola + miel"],
                      ["Smoothie récup : banane, lait, cacao"],
                      ["Fromage + pain complet + noix 20g"],
                      ["Crêpe avoine + beurre cacahuète"],
                      ["Lait entier chaud + miel + amandes 20g"]],
        'maintenir': [["Yaourt nature", "Noix ou dattes"],
                      ["1 fruit de saison frais"],
                      ["Fromage blanc + 1cc de miel"],
                      ["1 banane ou 1 pomme"],
                      ["Yaourt grec + fruits rouges"],
                      ["1 carré chocolat noir + thé"],
                      ["Tisane douce + galette de riz"]],
    }

    idx = day_idx % 7
    plan = {
        'jour_nom': JOURS[idx],
        'numero':   idx + 1,
        'theme':    THEMES[obj][idx],
        'petit_dejeuner':  {**petits_dej[obj][idx],  'cal': b},
        'collation_matin': {'items': collations_matin[obj][idx], 'cal': cs},
        'dejeuner':        {**dejeuners[obj][idx],    'cal': l},
        'collation_soir':  {'items': collations_soir[obj][idx],  'cal': cs},
        'diner':           {**diners[obj][idx],       'cal': d},
    }
    return plan, cal


def _generate_activities(profil):
    """Generate 7-day full body program adapted to level & goal"""
    niveau = profil.niveau_activite
    objectif = profil.objectif

    # ── DÉBUTANT (sédentaire / léger) ───────────────────────────────────────
    debutant = [
        {
            'jour': 'Jour 1', 'numero': 1, 'focus': 'Haut du corps — Débutant', 'emoji': '💪',
            'duree': '35 min', 'difficulte': 'Débutant', 'repos_jour': False,
            'exercices': [
                {'nom': 'Pompes genoux', 'series': 3, 'reps': '8-10', 'repos': '60 sec', 'muscle': 'Pectoraux', 'emoji': '🤸', 'conseil': 'Dos bien droit, regarder le sol'},
                {'nom': 'Dips sur chaise', 'series': 3, 'reps': '8-10', 'repos': '60 sec', 'muscle': 'Triceps', 'emoji': '💺', 'conseil': 'Coudes vers l\'arrière'},
                {'nom': 'Rowing avec bouteilles', 'series': 3, 'reps': '12', 'repos': '60 sec', 'muscle': 'Dos', 'emoji': '🏋️', 'conseil': 'Pincer les omoplates'},
                {'nom': 'Élévations latérales', 'series': 3, 'reps': '12', 'repos': '45 sec', 'muscle': 'Épaules', 'emoji': '🦅', 'conseil': 'Bras légèrement fléchis'},
            ]
        },
        {
            'jour': 'Jour 2', 'numero': 2, 'focus': 'Yoga & Étirements', 'emoji': '🧘',
            'duree': '30 min', 'difficulte': 'Doux', 'repos_jour': False,
            'exercices': [
                {'nom': 'Salutation au soleil', 'series': 3, 'reps': '5 cycles', 'repos': '30 sec', 'muscle': 'Corps entier', 'emoji': '☀️', 'conseil': 'Respirez à chaque mouvement'},
                {'nom': 'Posture de l\'enfant', 'series': 2, 'reps': '60 sec', 'repos': '0', 'muscle': 'Dos & Hanches', 'emoji': '🙇', 'conseil': 'Relâchez complètement'},
                {'nom': 'Étirement ischio-jambiers', 'series': 2, 'reps': '45 sec / jambe', 'repos': '0', 'muscle': 'Jambes', 'emoji': '🦵', 'conseil': 'Sans forcer, progressivement'},
                {'nom': 'Torsion vertébrale', 'series': 2, 'reps': '45 sec / côté', 'repos': '0', 'muscle': 'Dos', 'emoji': '🔄', 'conseil': 'Expirer en tournant'},
            ]
        },
        {
            'jour': 'Jour 3', 'numero': 3, 'focus': 'Bas du corps — Débutant', 'emoji': '🦵',
            'duree': '35 min', 'difficulte': 'Débutant', 'repos_jour': False,
            'exercices': [
                {'nom': 'Squats au poids du corps', 'series': 3, 'reps': '12-15', 'repos': '60 sec', 'muscle': 'Quadriceps & Fessiers', 'emoji': '🏋️', 'conseil': 'Genoux dans l\'axe des pieds'},
                {'nom': 'Fentes alternées', 'series': 3, 'reps': '10 / jambe', 'repos': '60 sec', 'muscle': 'Quadriceps', 'emoji': '🚶', 'conseil': 'Genou arrière proche du sol'},
                {'nom': 'Pont fessier', 'series': 3, 'reps': '15', 'repos': '45 sec', 'muscle': 'Fessiers', 'emoji': '🍑', 'conseil': 'Serrez fort en haut'},
                {'nom': 'Élévations de mollets', 'series': 3, 'reps': '20', 'repos': '30 sec', 'muscle': 'Mollets', 'emoji': '🦶', 'conseil': 'Montez sur la pointe des pieds'},
            ]
        },
        {
            'jour': 'Jour 4', 'numero': 4, 'focus': 'Repos actif — Marche', 'emoji': '🚶',
            'duree': '30 min', 'difficulte': 'Doux', 'repos_jour': True,
            'exercices': [
                {'nom': 'Marche rapide en extérieur', 'series': 1, 'reps': '30 min', 'repos': '0', 'muscle': 'Corps entier', 'emoji': '🌳', 'conseil': 'Bonne cadence, bras actifs'},
                {'nom': 'Respiration abdominale', 'series': 3, 'reps': '10 cycles', 'repos': '0', 'muscle': 'Core', 'emoji': '💨', 'conseil': 'Gonflez le ventre à l\'inspire'},
            ]
        },
        {
            'jour': 'Jour 5', 'numero': 5, 'focus': 'Full Body Circuit', 'emoji': '🔥',
            'duree': '40 min', 'difficulte': 'Modéré', 'repos_jour': False,
            'exercices': [
                {'nom': 'Jumping Jacks', 'series': 3, 'reps': '30 sec', 'repos': '30 sec', 'muscle': 'Corps entier', 'emoji': '⭐', 'conseil': 'Maintenir le rythme'},
                {'nom': 'Pompes genoux', 'series': 3, 'reps': '10', 'repos': '45 sec', 'muscle': 'Pectoraux', 'emoji': '🤸', 'conseil': ''},
                {'nom': 'Squats sautés (si possible)', 'series': 3, 'reps': '10', 'repos': '45 sec', 'muscle': 'Jambes', 'emoji': '🦘', 'conseil': 'Réception douce'},
                {'nom': 'Gainage avant', 'series': 3, 'reps': '30 sec', 'repos': '30 sec', 'muscle': 'Core', 'emoji': '⚡', 'conseil': 'Corps droit comme une planche'},
            ]
        },
        {
            'jour': 'Jour 6', 'numero': 6, 'focus': 'Yoga & Méditation', 'emoji': '🧘‍♀️',
            'duree': '25 min', 'difficulte': 'Doux', 'repos_jour': False,
            'exercices': [
                {'nom': 'Méditation guidée', 'series': 1, 'reps': '10 min', 'repos': '0', 'muscle': 'Mental', 'emoji': '🧠', 'conseil': 'Concentrez-vous sur votre souffle'},
                {'nom': 'Yoga restauratif', 'series': 1, 'reps': '15 min', 'repos': '0', 'muscle': 'Corps entier', 'emoji': '🌺', 'conseil': 'Postures passives, sans effort'},
            ]
        },
        {
            'jour': 'Jour 7', 'numero': 7, 'focus': 'Repos Complet', 'emoji': '😴',
            'duree': '—', 'difficulte': 'Repos', 'repos_jour': True,
            'exercices': [
                {'nom': 'Repos & Récupération', 'series': 1, 'reps': 'Toute la journée', 'repos': '0', 'muscle': 'Corps entier', 'emoji': '💤', 'conseil': 'Hydratation, sommeil 8h, alimentation saine'},
            ]
        },
    ]

    # ── INTERMÉDIAIRE (modéré) ───────────────────────────────────────────────
    intermediaire = [
        {
            'jour': 'Jour 1', 'numero': 1, 'focus': 'Pectoraux & Triceps', 'emoji': '💪',
            'duree': '45 min', 'difficulte': 'Intermédiaire', 'repos_jour': False,
            'exercices': [
                {'nom': 'Développé couché (haltères)', 'series': 4, 'reps': '10-12', 'repos': '75 sec', 'muscle': 'Pectoraux', 'emoji': '🏋️', 'conseil': 'Coudes à 45°, descente contrôlée'},
                {'nom': 'Pompes déclinées', 'series': 3, 'reps': '12-15', 'repos': '60 sec', 'muscle': 'Pectoraux bas', 'emoji': '📐', 'conseil': 'Pieds surélevés sur chaise'},
                {'nom': 'Écarté haltères', 'series': 3, 'reps': '12', 'repos': '60 sec', 'muscle': 'Pectoraux', 'emoji': '🦅', 'conseil': 'Bras légèrement fléchis, ouverture maximale'},
                {'nom': 'Extensions triceps haltère', 'series': 3, 'reps': '12-15', 'repos': '60 sec', 'muscle': 'Triceps', 'emoji': '💥', 'conseil': 'Coudes fixes, descente lente'},
                {'nom': 'Dips lestés sur chaise', 'series': 3, 'reps': '10-12', 'repos': '75 sec', 'muscle': 'Triceps', 'emoji': '💺', 'conseil': 'Corps proche de la chaise'},
            ]
        },
        {
            'jour': 'Jour 2', 'numero': 2, 'focus': 'Dos & Biceps', 'emoji': '🔙',
            'duree': '45 min', 'difficulte': 'Intermédiaire', 'repos_jour': False,
            'exercices': [
                {'nom': 'Tirage haltères un bras', 'series': 4, 'reps': '10-12', 'repos': '75 sec', 'muscle': 'Grand dorsal', 'emoji': '🏋️', 'conseil': 'Tirez le coude vers la hanche'},
                {'nom': 'Rowing barre (simulé)', 'series': 3, 'reps': '12', 'repos': '75 sec', 'muscle': 'Dos moyen', 'emoji': '🚣', 'conseil': 'Pincer les omoplates en fin de mouvement'},
                {'nom': 'Pull-overs haltère', 'series': 3, 'reps': '12', 'repos': '60 sec', 'muscle': 'Grand dorsal', 'emoji': '🏊', 'conseil': 'Bras légèrement fléchis'},
                {'nom': 'Curl biceps haltères', 'series': 3, 'reps': '12-15', 'repos': '60 sec', 'muscle': 'Biceps', 'emoji': '💪', 'conseil': 'Coudes fixes contre les côtes'},
                {'nom': 'Curl concentré', 'series': 3, 'reps': '10 / bras', 'repos': '45 sec', 'muscle': 'Biceps (pic)', 'emoji': '🎯', 'conseil': 'Contraction maximale en haut'},
            ]
        },
        {
            'jour': 'Jour 3', 'numero': 3, 'focus': 'Jambes & Fessiers', 'emoji': '🦵',
            'duree': '50 min', 'difficulte': 'Intermédiaire', 'repos_jour': False,
            'exercices': [
                {'nom': 'Squats haltères', 'series': 4, 'reps': '10-12', 'repos': '90 sec', 'muscle': 'Quadriceps & Fessiers', 'emoji': '🏋️', 'conseil': 'Descendre sous le parallèle'},
                {'nom': 'Fentes marchées', 'series': 3, 'reps': '12 / jambe', 'repos': '75 sec', 'muscle': 'Quadriceps & Fessiers', 'emoji': '🚶', 'conseil': 'Grand pas en avant, genou à 90°'},
                {'nom': 'Soulevé de terre jambes raidies', 'series': 3, 'reps': '12', 'repos': '75 sec', 'muscle': 'Ischios & Fessiers', 'emoji': '🔱', 'conseil': 'Dos droit, descente lente'},
                {'nom': 'Presse jambes (squats muraux)', 'series': 3, 'reps': '45 sec', 'repos': '60 sec', 'muscle': 'Quadriceps', 'emoji': '🧱', 'conseil': 'Dos plaqué au mur, cuisses parallèles'},
                {'nom': 'Élévations mollets debout', 'series': 4, 'reps': '20-25', 'repos': '45 sec', 'muscle': 'Mollets', 'emoji': '🦶', 'conseil': 'Amplitude maximale'},
            ]
        },
        {
            'jour': 'Jour 4', 'numero': 4, 'focus': 'Cardio & Core', 'emoji': '🏃',
            'duree': '40 min', 'difficulte': 'Modéré', 'repos_jour': False,
            'exercices': [
                {'nom': 'Jogging ou vélo', 'series': 1, 'reps': '20 min', 'repos': '0', 'muscle': 'Cardio', 'emoji': '🏃', 'conseil': 'Zone 2 : peut tenir une conversation'},
                {'nom': 'Gainage avant', 'series': 4, 'reps': '45 sec', 'repos': '30 sec', 'muscle': 'Core', 'emoji': '⚡', 'conseil': 'Contracter abdos et fessiers'},
                {'nom': 'Russian twists', 'series': 3, 'reps': '20', 'repos': '30 sec', 'muscle': 'Obliques', 'emoji': '🌀', 'conseil': 'Pieds décollés pour plus de difficulté'},
                {'nom': 'Crunchs bicycle', 'series': 3, 'reps': '20', 'repos': '30 sec', 'muscle': 'Abdominaux', 'emoji': '🚴', 'conseil': 'Rotation complète coude ↔ genou'},
            ]
        },
        {
            'jour': 'Jour 5', 'numero': 5, 'focus': 'Épaules & Bras', 'emoji': '🏅',
            'duree': '45 min', 'difficulte': 'Intermédiaire', 'repos_jour': False,
            'exercices': [
                {'nom': 'Développé militaire haltères', 'series': 4, 'reps': '10-12', 'repos': '75 sec', 'muscle': 'Épaules', 'emoji': '🏋️', 'conseil': 'Pousser verticalement, coudes devant'},
                {'nom': 'Élévations latérales', 'series': 3, 'reps': '12-15', 'repos': '60 sec', 'muscle': 'Épaules latérales', 'emoji': '🦅', 'conseil': 'Légère rotation interne du poignet'},
                {'nom': 'Élévations frontales', 'series': 3, 'reps': '12', 'repos': '60 sec', 'muscle': 'Épaules avant', 'emoji': '⬆️', 'conseil': 'Hauteur des épaules maximum'},
                {'nom': 'Curl haltères alternés', 'series': 3, 'reps': '10 / bras', 'repos': '60 sec', 'muscle': 'Biceps', 'emoji': '💪', 'conseil': 'Supination en montant'},
                {'nom': 'Kickbacks triceps', 'series': 3, 'reps': '12 / bras', 'repos': '45 sec', 'muscle': 'Triceps', 'emoji': '🔙', 'conseil': 'Bras parallèle au sol, extension complète'},
            ]
        },
        {
            'jour': 'Jour 6', 'numero': 6, 'focus': 'Full Body + Cardio', 'emoji': '🔥',
            'duree': '50 min', 'difficulte': 'Intense', 'repos_jour': False,
            'exercices': [
                {'nom': 'Burpees', 'series': 4, 'reps': '10', 'repos': '60 sec', 'muscle': 'Corps entier', 'emoji': '💥', 'conseil': 'Saut explosif, réception douce'},
                {'nom': 'Man makers (pompe + row + press)', 'series': 3, 'reps': '8', 'repos': '90 sec', 'muscle': 'Corps entier', 'emoji': '🦸', 'conseil': 'Contrôle à chaque phase'},
                {'nom': 'Squats-Presses', 'series': 3, 'reps': '12', 'repos': '75 sec', 'muscle': 'Jambes & Épaules', 'emoji': '🏋️', 'conseil': 'Pousser en montant du squat'},
                {'nom': 'Gainage dynamique', 'series': 3, 'reps': '30 sec', 'repos': '30 sec', 'muscle': 'Core', 'emoji': '⚡', 'conseil': 'Mountain climbers ou planche avec toucher'},
            ]
        },
        {
            'jour': 'Jour 7', 'numero': 7, 'focus': 'Récupération Active', 'emoji': '🧘',
            'duree': '30 min', 'difficulte': 'Repos', 'repos_jour': True,
            'exercices': [
                {'nom': 'Marche légère', 'series': 1, 'reps': '15 min', 'repos': '0', 'muscle': 'Corps entier', 'emoji': '🚶', 'conseil': 'Rythme conversationnel'},
                {'nom': 'Étirements globaux', 'series': 1, 'reps': '15 min', 'repos': '0', 'muscle': 'Corps entier', 'emoji': '🤸', 'conseil': 'Maintenir chaque position 30-60 sec'},
            ]
        },
    ]

    # ── AVANCÉ (actif / très actif) ──────────────────────────────────────────
    avance = [
        {
            'jour': 'Jour 1', 'numero': 1, 'focus': 'Pectoraux & Triceps — Force', 'emoji': '💪',
            'duree': '60 min', 'difficulte': 'Avancé', 'repos_jour': False,
            'exercices': [
                {'nom': 'Développé couché barre', 'series': 5, 'reps': '5', 'repos': '120 sec', 'muscle': 'Pectoraux', 'emoji': '🏋️', 'conseil': '5×5 force — charges lourdes'},
                {'nom': 'Développé incliné haltères', 'series': 4, 'reps': '8-10', 'repos': '90 sec', 'muscle': 'Pectoraux haut', 'emoji': '📐', 'conseil': 'Inclinaison 30-45°'},
                {'nom': 'Pompes lestées', 'series': 3, 'reps': '12-15', 'repos': '60 sec', 'muscle': 'Pectoraux', 'emoji': '🤸', 'conseil': 'Sac à dos chargé si possible'},
                {'nom': 'Dips lestés', 'series': 4, 'reps': '8-10', 'repos': '90 sec', 'muscle': 'Triceps & Pectoraux bas', 'emoji': '⬇️', 'conseil': 'Légèrement penché en avant'},
                {'nom': 'Pushdown câble (corde)', 'series': 3, 'reps': '12-15', 'repos': '60 sec', 'muscle': 'Triceps', 'emoji': '🔱', 'conseil': 'Écarter la corde en bas'},
            ]
        },
        {
            'jour': 'Jour 2', 'numero': 2, 'focus': 'Dos & Biceps — Épaisseur', 'emoji': '🔙',
            'duree': '60 min', 'difficulte': 'Avancé', 'repos_jour': False,
            'exercices': [
                {'nom': 'Soulevé de terre conventionnel', 'series': 5, 'reps': '5', 'repos': '150 sec', 'muscle': 'Dos complet & Jambes', 'emoji': '🏋️', 'conseil': 'Barre au niveau des tibias, dos neutre'},
                {'nom': 'Tractions pronation', 'series': 4, 'reps': 'Max', 'repos': '90 sec', 'muscle': 'Grand dorsal', 'emoji': '⬆️', 'conseil': 'Amplitude complète, descente lente'},
                {'nom': 'Rowing barre', 'series': 4, 'reps': '8-10', 'repos': '90 sec', 'muscle': 'Dos moyen & Romboides', 'emoji': '🚣', 'conseil': 'Buste horizontal, tirer vers le nombril'},
                {'nom': 'Curl barre EZ', 'series': 4, 'reps': '8-10', 'repos': '75 sec', 'muscle': 'Biceps', 'emoji': '💪', 'conseil': 'Contre le mur pour isoler'},
                {'nom': 'Curl incliné haltères', 'series': 3, 'reps': '10-12', 'repos': '60 sec', 'muscle': 'Biceps (long chef)', 'emoji': '🎯', 'conseil': 'Banc à 45°, amplitude maximale'},
            ]
        },
        {
            'jour': 'Jour 3', 'numero': 3, 'focus': 'Jambes — Squat & Deadlift', 'emoji': '🦵',
            'duree': '65 min', 'difficulte': 'Intense', 'repos_jour': False,
            'exercices': [
                {'nom': 'Back Squat barre', 'series': 5, 'reps': '5', 'repos': '150 sec', 'muscle': 'Quadriceps & Fessiers', 'emoji': '🏋️', 'conseil': 'Genoux dans l\'axe, descendre sous parallèle'},
                {'nom': 'Leg press', 'series': 4, 'reps': '10-12', 'repos': '90 sec', 'muscle': 'Quadriceps', 'emoji': '🦿', 'conseil': 'Pieds hauts pour activer les fessiers'},
                {'nom': 'Fentes bulgares', 'series': 3, 'reps': '10 / jambe', 'repos': '75 sec', 'muscle': 'Fessiers & Quadriceps', 'emoji': '🚶', 'conseil': 'Pied arrière sur banc'},
                {'nom': 'Romanian Deadlift', 'series': 3, 'reps': '10-12', 'repos': '90 sec', 'muscle': 'Ischios & Fessiers', 'emoji': '🔱', 'conseil': 'Descente contrôlée, hanches en arrière'},
                {'nom': 'Mollets à la presse', 'series': 5, 'reps': '15-20', 'repos': '45 sec', 'muscle': 'Mollets', 'emoji': '🦶', 'conseil': 'Pause 2 sec en bas (étirement)'},
            ]
        },
        {
            'jour': 'Jour 4', 'numero': 4, 'focus': 'HIIT — Cardio Explosif', 'emoji': '⚡',
            'duree': '45 min', 'difficulte': 'Intense', 'repos_jour': False,
            'exercices': [
                {'nom': 'Warm-up cardio', 'series': 1, 'reps': '5 min', 'repos': '0', 'muscle': 'Corps entier', 'emoji': '🔥', 'conseil': 'Montée en température progressive'},
                {'nom': 'Sprint 30-20-10', 'series': 6, 'reps': '30s sprint / 30s repos', 'repos': '2 min entre séries', 'muscle': 'Cardio', 'emoji': '🏃', 'conseil': '100% effort sur les sprints'},
                {'nom': 'Burpees avec saut', 'series': 4, 'reps': '12', 'repos': '60 sec', 'muscle': 'Corps entier', 'emoji': '💥', 'conseil': 'Maximiser la hauteur du saut'},
                {'nom': 'Box jumps (ou squats sautés)', 'series': 4, 'reps': '10', 'repos': '60 sec', 'muscle': 'Jambes', 'emoji': '🦘', 'conseil': 'Réception silencieuse'},
                {'nom': 'Cool-down & étirements', 'series': 1, 'reps': '10 min', 'repos': '0', 'muscle': 'Corps entier', 'emoji': '🧊', 'conseil': 'Rythme cardiaque < 100 bpm'},
            ]
        },
        {
            'jour': 'Jour 5', 'numero': 5, 'focus': 'Épaules — Volume', 'emoji': '🏅',
            'duree': '55 min', 'difficulte': 'Avancé', 'repos_jour': False,
            'exercices': [
                {'nom': 'Développé militaire barre', 'series': 5, 'reps': '5', 'repos': '120 sec', 'muscle': 'Épaules', 'emoji': '🏋️', 'conseil': '5×5 force, barre devant'},
                {'nom': 'Arnold Press', 'series': 3, 'reps': '10-12', 'repos': '75 sec', 'muscle': 'Épaules (3 faisceaux)', 'emoji': '🌀', 'conseil': 'Rotation du poignet pendant la pression'},
                {'nom': 'Élévations latérales droite-drop', 'series': 4, 'reps': '12 + drop', 'repos': '60 sec', 'muscle': 'Épaules latérales', 'emoji': '🦅', 'conseil': 'Drop set sur la dernière série'},
                {'nom': 'Face pulls', 'series': 3, 'reps': '15', 'repos': '60 sec', 'muscle': 'Épaules arrière & Romboides', 'emoji': '🎯', 'conseil': 'Tirer vers le visage, coudes hauts'},
                {'nom': 'Shrugs haltères', 'series': 3, 'reps': '15-20', 'repos': '45 sec', 'muscle': 'Trapèzes', 'emoji': '💆', 'conseil': 'Pause 2 sec en haut'},
            ]
        },
        {
            'jour': 'Jour 6', 'numero': 6, 'focus': 'Full Body + Core Intensif', 'emoji': '🔥',
            'duree': '60 min', 'difficulte': 'Intense', 'repos_jour': False,
            'exercices': [
                {'nom': 'Clean & Press (haltères)', 'series': 4, 'reps': '8', 'repos': '90 sec', 'muscle': 'Corps entier', 'emoji': '🏋️', 'conseil': 'Explosivité de la hanche'},
                {'nom': 'Thruster (squat + press)', 'series': 4, 'reps': '10', 'repos': '90 sec', 'muscle': 'Corps entier', 'emoji': '🚀', 'conseil': 'Enchainer squat et press sans pause'},
                {'nom': 'Gainage dynamique dragon flag', 'series': 3, 'reps': '8-10', 'repos': '90 sec', 'muscle': 'Core', 'emoji': '🐉', 'conseil': 'Descente lente, contrôlée'},
                {'nom': 'Ab wheel rollout', 'series': 3, 'reps': '10-12', 'repos': '60 sec', 'muscle': 'Core', 'emoji': '⚙️', 'conseil': 'Dos droit pendant l\'extension'},
                {'nom': 'Corde à sauter HIIT', 'series': 3, 'reps': '60 sec', 'repos': '30 sec', 'muscle': 'Cardio & Mollets', 'emoji': '🪢', 'conseil': 'Varier double sauts et normaux'},
            ]
        },
        {
            'jour': 'Jour 7', 'numero': 7, 'focus': 'Récupération & Mobilité', 'emoji': '🧘',
            'duree': '40 min', 'difficulte': 'Repos', 'repos_jour': True,
            'exercices': [
                {'nom': 'Foam roller — corps entier', 'series': 1, 'reps': '15 min', 'repos': '0', 'muscle': 'Corps entier', 'emoji': '🛞', 'conseil': 'Insister sur les zones de tension'},
                {'nom': 'Stretching statique global', 'series': 1, 'reps': '15 min', 'repos': '0', 'muscle': 'Corps entier', 'emoji': '🤸', 'conseil': '30-45 sec par groupe musculaire'},
                {'nom': 'Bain froid ou douche froide', 'series': 1, 'reps': '5-10 min', 'repos': '0', 'muscle': 'Récupération', 'emoji': '🧊', 'conseil': 'Réduit l\'inflammation musculaire'},
            ]
        },
    ]

    # Choose program based on level
    if niveau in ('sedentaire', 'leger'):
        programme = debutant
    elif niveau == 'modere':
        programme = intermediaire
    else:
        programme = avance

    # Adjust for goal: if "perdre", add cardio notes; if "prendre", add volume notes
    for jour in programme:
        for ex in jour['exercices']:
            if objectif == 'perdre' and not ex.get('_tagged'):
                if jour.get('repos_jour'): continue
            if objectif == 'prendre':
                ex['conseil'] = (ex['conseil'] + ' — Mangez 30g protéines post-séance' if ex['conseil'] else 'Mangez 30g protéines post-séance') if ex == jour['exercices'][-1] else ex['conseil']

    return programme


@login_required
def parcours_home(request):
    """Main Parcours Bien-être dashboard"""
    _seed_quotes()
    user = request.user

    # Today's quote (seeded by day of year)
    quotes = list(QuoteInspirante.objects.all())
    today_idx = date.today().timetuple().tm_yday % max(len(quotes), 1) if quotes else 0
    quote_du_jour = quotes[today_idx] if quotes else None

    # Recent journal entries
    journal_recent = JournalEntry.objects.filter(utilisateur=user)[:3]

    # Recent blogs
    blogs_recent = BlogBienEtre.objects.filter(est_publie=True)[:3]

    # Health profile
    profil_sante = getattr(user, 'profil_sante', None)

    # Wellness score (0-100) — difficile à atteindre 100
    score = 0
    week_ago = timezone.now() - timedelta(days=7)
    month_ago = timezone.now() - timedelta(days=30)

    # Journal : +2 par entrée cette semaine, max 10 pts (besoin de 5 entrées/semaine)
    score += min(JournalEntry.objects.filter(utilisateur=user, date_creation__gte=week_ago).count() * 2, 10)

    # Journal régularité : +1 par entrée ce mois, max 10 pts (besoin de 10 entrées/mois)
    score += min(JournalEntry.objects.filter(utilisateur=user, date_creation__gte=month_ago).count() * 1, 10)

    # Ressources complétées : +2 par ressource, max 20 pts (besoin de 10 ressources)
    score += min(ProgressionUtilisateur.objects.filter(utilisateur=user, est_complete=True).count() * 2, 20)

    # Consultations confirmées : +5 par consultation, max 20 pts (besoin de 4 consultations)
    score += min(ConsultationRequest.objects.filter(utilisateur=user, statut='confirmee').count() * 5, 20)

    # Profil santé rempli : +10 pts
    score += 10 if profil_sante else 0

    # Blog bien-être : +3 par article publié, max 15 pts (besoin de 5 articles)
    score += min(BlogBienEtre.objects.filter(utilisateur=user, est_publie=True).count() * 3, 15)

    # Sessions Wana (chatbot) : +3 par session, max 15 pts (besoin de 5 sessions)
    score += min(ChatSession.objects.filter(utilisateur=user).count() * 3, 15)

    # Stats
    stats = {
        'journal_count': JournalEntry.objects.filter(utilisateur=user).count(),
        'blog_count': BlogBienEtre.objects.filter(utilisateur=user).count(),
        'ressources_count': ProgressionUtilisateur.objects.filter(utilisateur=user, est_complete=True).count(),
        'consultations_count': ConsultationRequest.objects.filter(utilisateur=user).count(),
    }

    return render(request, 'application/parcours_home.html', {
        'quote_du_jour': quote_du_jour,
        'journal_recent': journal_recent,
        'blogs_recent': blogs_recent,
        'profil_sante': profil_sante,
        'wellness_score': score,
        'stats': stats,
    })


@login_required
def parcours_journal(request):
    """Journal intime"""
    user = request.user
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            titre = request.POST.get('titre', '').strip()
            contenu = request.POST.get('contenu', '').strip()
            humeur = request.POST.get('humeur', '3')
            if contenu:
                JournalEntry.objects.create(
                    utilisateur=user, titre=titre, contenu=contenu, humeur=humeur
                )
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'message': 'Contenu vide'})
        elif action == 'delete':
            entry_id = request.POST.get('entry_id')
            JournalEntry.objects.filter(id=entry_id, utilisateur=user).delete()
            return JsonResponse({'success': True})

    entries = JournalEntry.objects.filter(utilisateur=user)
    mood_stats = {}
    for e in entries:
        mood_stats[e.humeur] = mood_stats.get(e.humeur, 0) + 1

    return render(request, 'application/parcours_journal.html', {
        'entries': entries,
        'mood_stats': mood_stats,
    })


@login_required
def parcours_inspiration(request):
    """Inspiration quotes page"""
    _seed_quotes()
    cat_filter = request.GET.get('cat', '')
    quotes = QuoteInspirante.objects.all()
    if cat_filter:
        quotes = quotes.filter(categorie=cat_filter)

    # Today's quote
    all_quotes = list(QuoteInspirante.objects.all())
    today_idx = date.today().timetuple().tm_yday % max(len(all_quotes), 1) if all_quotes else 0
    quote_du_jour = all_quotes[today_idx] if all_quotes else None

    categories = QuoteInspirante.objects.values_list('categorie', flat=True).distinct()

    return render(request, 'application/parcours_inspiration.html', {
        'quotes': quotes,
        'quote_du_jour': quote_du_jour,
        'categories': categories,
        'cat_filter': cat_filter,
    })


@login_required
def parcours_sante(request):
    """Health profile + meal plan + activities"""
    user = request.user
    profil = getattr(user, 'profil_sante', None)

    if request.method == 'POST':
        data = {
            'age': int(request.POST.get('age', 25)),
            'taille': int(request.POST.get('taille', 170)),
            'poids': float(request.POST.get('poids', 70)),
            'sexe': request.POST.get('sexe', 'homme'),
            'niveau_activite': request.POST.get('niveau_activite', 'modere'),
            'objectif': request.POST.get('objectif', 'maintenir'),
        }
        if profil:
            for k, v in data.items():
                setattr(profil, k, v)
            profil.save()
        else:
            profil = ProfilSante.objects.create(utilisateur=user, **data)
        return redirect('parcours_sante')

    meal_plan = None
    programme_7_jours = None
    total_cal = None
    today_day_idx = date.today().timetuple().tm_yday % 7
    today_workout = None
    if profil:
        meal_plan, total_cal = _generate_meal_plan(profil, today_day_idx)
        programme_7_jours = _generate_activities(profil)
        today_workout = programme_7_jours[today_day_idx]

    return render(request, 'application/parcours_sante.html', {
        'profil': profil,
        'meal_plan': meal_plan,
        'programme_7_jours': programme_7_jours,
        'today_day_idx': today_day_idx,
        'today_workout': today_workout,
        'total_cal': total_cal,
    })


@login_required
def parcours_blog(request):
    """Blog bien-être list"""
    blogs = BlogBienEtre.objects.filter(est_publie=True).select_related('utilisateur')
    liked_ids = set(request.user.blogs_aimes.values_list('id', flat=True))
    return render(request, 'application/parcours_blog.html', {
        'blogs': blogs,
        'liked_ids': liked_ids,
    })


@login_required
def parcours_blog_create(request):
    """Create a blog post"""
    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        contenu = request.POST.get('contenu', '').strip()
        tags = request.POST.get('tags', '').strip()
        image = request.FILES.get('image')
        if titre and contenu:
            blog = BlogBienEtre.objects.create(
                utilisateur=request.user,
                titre=titre, contenu=contenu,
                tags=tags, image=image,
            )
            return redirect('parcours_blog_detail', blog_id=blog.id)
    return render(request, 'application/parcours_blog_create.html', {})


@login_required
def parcours_blog_detail(request, blog_id):
    """Blog post detail"""
    blog = get_object_or_404(BlogBienEtre, id=blog_id, est_publie=True)
    is_liked = request.user in blog.likes.all()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'like':
            if is_liked:
                blog.likes.remove(request.user)
                is_liked = False
            else:
                blog.likes.add(request.user)
                is_liked = True
            return JsonResponse({'success': True, 'is_liked': is_liked, 'nb_likes': blog.nb_likes()})
        elif action == 'delete' and blog.utilisateur == request.user:
            blog.delete()
            return redirect('parcours_blog')

    related = BlogBienEtre.objects.filter(est_publie=True).exclude(id=blog.id)[:3]
    return render(request, 'application/parcours_blog_detail.html', {
        'blog': blog,
        'is_liked': is_liked,
        'related': related,
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  CHATBOT IA — Wanaag d'écoute
# ═══════════════════════════════════════════════════════════════════════════════

CHATBOT_SYSTEM_PROMPT = """
Tu es Wanaag, un assistant d'écoute bienveillant et empathique de la plateforme Wanaag Corner,
dédiée à la santé mentale à Djibouti. Tu parles exclusivement en français.

Ton rôle principal est d'ÉCOUTER, de VALIDER les émotions et d'ACCOMPAGNER l'utilisateur
sans jamais minimiser sa douleur ni se substituer à un professionnel de santé.

Règles fondamentales :
- Réponds TOUJOURS avec chaleur, douceur et un profond respect.
- Ne donne JAMAIS de diagnostic médical ni de prescription médicamenteuse.
- Si tu détectes des pensées suicidaires, d'automutilation ou une détresse sévère,
  intègre IMMÉDIATEMENT dans ta réponse : "Je vous encourage vivement à contacter
  un professionnel maintenant : appelez le 15 (SAMU) ou consultez un psychologue
  de notre plateforme via /psychologues/."
- Utilise des techniques d'écoute active : reformulation, reflet des émotions,
  questions ouvertes douces.
- Mémorise les éléments clés partagés et fais-y référence avec sensibilité.
- Ne juge JAMAIS. Sois neutre et bienveillant face à toute situation.
- Si l'utilisateur semble anxieux ou stressé, propose un exercice de respiration
  ou de pleine conscience simple (ex: respiration 4-7-8).
- Termine souvent par une question ouverte douce pour encourager l'expression.
- Rappelle régulièrement que des psychologues professionnels sont disponibles
  sur la plateforme pour un accompagnement approfondi.

Format de réponse :
- Paragraphes courts et aérés (max 4 paragraphes).
- Évite le jargon médical ou psychiatrique.
- Utilise occasionnellement des émojis doux (🌿 💛 🌸) pour humaniser l'échange.
- Commence toujours par valider l'émotion exprimée avant de répondre.
"""

CRISIS_KEYWORDS = [
    'suicide', 'me tuer', 'mourir', 'en finir', 'plus envie de vivre',
    'automutilation', 'me blesser', 'me faire du mal', 'disparaître',
    'plus rien', 'inutile', 'fardeau', 'plus de raison', 'je veux mourir',
    'mettre fin', 'fin de ma vie', 'me supprimer',
]


def _detect_crisis(text):
    t = text.lower()
    return any(kw in t for kw in CRISIS_KEYWORDS)


def _get_or_create_chat_session(request):
    session_key = request.session.get('chatbot_session_key')
    if session_key:
        try:
            return ChatSession.objects.get(
                session_key=session_key,
                utilisateur=request.user,
                is_active=True
            )
        except ChatSession.DoesNotExist:
            pass
    new_key = uuid.uuid4().hex
    session = ChatSession.objects.create(utilisateur=request.user, session_key=new_key)
    request.session['chatbot_session_key'] = new_key
    return session


@login_required
def chatbot_page(request):
    session = _get_or_create_chat_session(request)
    messages_history = session.messages.order_by('sent_at')
    past_sessions = ChatSession.objects.filter(
        utilisateur=request.user, is_active=False
    ).order_by('-last_active')[:5]
    return render(request, 'application/chatbot.html', {
        'chat_session': session,
        'messages_history': messages_history,
        'past_sessions': past_sessions,
    })


@login_required
def chatbot_send(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    try:
        data = json.loads(request.body)
        user_text = data.get('message', '').strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Données invalides'}, status=400)
    if not user_text or len(user_text) > 2000:
        return JsonResponse({'error': 'Message invalide'}, status=400)

    session = _get_or_create_chat_session(request)
    crisis = _detect_crisis(user_text)

    ChatMessage.objects.create(session=session, role='user', content=user_text, crisis_flag=crisis)

    if crisis:
        session.crisis_flag = True
        session.mood_detected = 'crisis'
        session.save(update_fields=['crisis_flag', 'mood_detected'])

    history = session.get_history_for_api(
        limit=getattr(__import__('django.conf', fromlist=['settings']).settings, 'CHATBOT_MAX_HISTORY', 20)
    )

    try:
        import anthropic as _anthropic
        from django.conf import settings as _settings
        client = _anthropic.Anthropic(api_key=_settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1024,
            system=CHATBOT_SYSTEM_PROMPT,
            messages=history,
        )
        assistant_text = response.content[0].text
    except Exception as e:
        return JsonResponse({
            'error': 'Service temporairement indisponible. Réessayez dans quelques instants.',
            'detail': str(e)
        }, status=503)

    ChatMessage.objects.create(session=session, role='assistant', content=assistant_text)

    return JsonResponse({
        'reply': assistant_text,
        'crisis': crisis,
        'msg_count': session.messages.count(),
    })


@login_required
def chatbot_new_session(request):
    if request.method == 'POST':
        old_key = request.session.get('chatbot_session_key')
        if old_key:
            ChatSession.objects.filter(
                session_key=old_key, utilisateur=request.user
            ).update(is_active=False)
            del request.session['chatbot_session_key']
    return JsonResponse({'ok': True})
