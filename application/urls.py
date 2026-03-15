from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Pages principales
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('about/', views.about, name='about'),
    
    # Forum
    path('forum/', views.forum_home, name='forum_home'),
    path('forum/create-group/', views.create_group, name='create_group'),
    path('forum/join/<int:group_id>/', views.join_group, name='join_group'),
    path('forum/leave/<int:group_id>/', views.leave_group, name='leave_group'),
    path('forum/group/<int:group_id>/', views.group_chat, name='group_chat'),
    path('forum/group/<int:group_id>/send/', views.send_message, name='send_message'),
    path('forum/group/<int:group_id>/messages/', views.get_messages, name='get_messages'),
    
    # Ressources éducatives
    path('ressources/', views.ressources_home, name='ressources_home'),
    path('ressources/<slug:slug>/', views.ressource_detail, name='ressource_detail'),
    path('ressources/<int:ressource_id>/favori/', views.toggle_favori, name='toggle_favori'),
    path('ressources/<int:ressource_id>/complete/', views.marquer_complete, name='marquer_complete'),
    path('ressources/<int:ressource_id>/commenter/', views.ajouter_commentaire, name='ajouter_commentaire'),
    path('mes-ressources/', views.mes_ressources, name='mes_ressources'),
    
    
      
    # ============= ROUTES UTILISATEUR =============
    
    # 1. Liste des psychologues disponibles
    path('psychologues/', views.psychologues_list, name='psychologues_list'),
    
    # 2. Formulaire pour demander une consultation
    path('psychologues/<int:psychologue_id>/consultation/', 
         views.consultation_request_form, name='consultation_request_form'),
    
    # 3. Liste de mes consultations
    path('mes-consultations/', views.mes_consultations, name='mes_consultations'),
    
    # 4. Détail d'une consultation avec messages
    path('consultation/<int:consultation_id>/', 
         views.consultation_detail, name='consultation_detail'),
    
    # ============= ROUTES PSYCHOLOGUE =============
    
    # 5. Dashboard du psychologue
    path('psychologue/dashboard/', 
         views.psychologue_dashboard, name='psychologue_dashboard'),
    
    # 6. Liste des demandes de consultation (pour le psychologue)
    path('psychologue/demandes/', 
         views.consultation_requests_list, name='consultation_requests_list'),
    
    # 7. Répondre à une demande de consultation
    path('psychologue/consultation/<int:consultation_id>/repondre/', 
         views.consultation_respond, name='consultation_respond'),
]