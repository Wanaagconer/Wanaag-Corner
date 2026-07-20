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

    # 5. Salle de visioconférence
    path('consultation/<int:consultation_id>/visio/',
         views.visio_room, name='visio_room'),
    
    # ============= ROUTES PSYCHOLOGUE =============
    
    # 5. Dashboard du psychologue
    path('psychologue/dashboard/',
         views.psychologue_dashboard, name='psychologue_dashboard'),
    path('psychologue/photo/', views.update_psy_photo, name='update_psy_photo'),
    
    # 6. Liste des demandes de consultation (pour le psychologue)
    path('psychologue/demandes/', 
         views.consultation_requests_list, name='consultation_requests_list'),
    
    # 7. Répondre à une demande de consultation
    path('psychologue/consultation/<int:consultation_id>/repondre/',
         views.consultation_respond, name='consultation_respond'),

    # ============= PROFIL =============
    path('profil/', views.profile, name='profile'),
    path('profil/<int:user_id>/', views.user_profile, name='user_profile'),
    path('follow/<int:user_id>/', views.follow_toggle, name='follow_toggle'),

    # ============= ROUTES POSTS =============
    path('posts/', views.posts_feed, name='posts_feed'),
    path('posts/create/', views.create_post, name='create_post'),
    path('posts/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('posts/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('posts/<int:post_id>/like/', views.like_post, name='like_post'),
    path('posts/<int:post_id>/commenter/', views.commenter_post, name='commenter_post'),

    # ============= ADMIN PANEL =============
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    # Ressources CRUD
    path('admin-panel/ressources/create/', views.admin_create_ressource, name='admin_create_ressource'),
    path('admin-panel/ressources/<int:ressource_id>/', views.admin_get_ressource, name='admin_get_ressource'),
    path('admin-panel/ressources/<int:ressource_id>/update/', views.admin_update_ressource, name='admin_update_ressource'),
    path('admin-panel/ressources/<int:ressource_id>/delete/', views.admin_delete_ressource, name='admin_delete_ressource'),
    # Categories CRUD
    path('admin-panel/categories/create/', views.admin_create_categorie, name='admin_create_categorie'),
    path('admin-panel/categories/<int:categorie_id>/', views.admin_update_categorie, name='admin_update_categorie'),
    path('admin-panel/categories/<int:categorie_id>/delete/', views.admin_delete_categorie, name='admin_delete_categorie'),
    # Users
    path('admin-panel/users/<int:user_id>/update/', views.admin_update_user, name='admin_update_user'),
    path('admin-panel/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    # Psychologues
    path('admin-panel/psychologues/create/', views.admin_create_psychologue, name='admin_create_psychologue'),
    path('admin-panel/psychologues/<int:psychologue_id>/', views.admin_update_psychologue, name='admin_update_psychologue'),
    path('admin-panel/psychologues/<int:psychologue_id>/delete/', views.admin_delete_psychologue, name='admin_delete_psychologue'),
    # Posts moderation
    path('admin-panel/posts/<int:post_id>/delete/', views.admin_delete_post_action, name='admin_delete_post_action'),
    # Forum groups moderation
    path('admin-panel/groups/<int:group_id>/delete/', views.admin_delete_group_action, name='admin_delete_group_action'),
    # Consultations
    path('admin-panel/consultations/<int:consultation_id>/update/', views.admin_update_consultation, name='admin_update_consultation'),

    # ============= CHATBOT IA =============
    path('chatbot/', views.chatbot_page, name='chatbot'),
    path('chatbot/send/', views.chatbot_send, name='chatbot_send'),
    path('chatbot/new-session/', views.chatbot_new_session, name='chatbot_new_session'),

    # ============= PARCOURS BIEN-ÊTRE =============
    path('parcours/', views.parcours_home, name='parcours_home'),
    path('parcours/journal/', views.parcours_journal, name='parcours_journal'),
    path('parcours/inspiration/', views.parcours_inspiration, name='parcours_inspiration'),
    path('parcours/sante/', views.parcours_sante, name='parcours_sante'),
    path('parcours/blog/', views.parcours_blog, name='parcours_blog'),
    path('parcours/blog/create/', views.parcours_blog_create, name='parcours_blog_create'),
    path('parcours/blog/<int:blog_id>/', views.parcours_blog_detail, name='parcours_blog_detail'),
]