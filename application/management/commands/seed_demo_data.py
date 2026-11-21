"""Peuple l'application avec des données de démonstration réalistes :
10 utilisateurs, quelques spécialistes, des groupes de parole actifs
(avec de vrais échanges) et une quinzaine de publications (posts, blogs,
articles). Pensé pour visualiser l'application dans un état "vivant".

Usage : python manage.py seed_demo_data
Peut être relancé sans dupliquer les utilisateurs (identifiés par email).
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from application.models import (
    CustomUser, ForumGroup, GroupMessage, GroupMemberStatus,
    Post, CommentairePost, Follow, Psychologue,
)

DEMO_PASSWORD = "Wanaag2026!"
EMAIL_DOMAIN = "seed.wanaagcorner.local"

USERS = [
    dict(username="amina_k", pseudonyme="Amina K.", bio="Ici pour apprendre à mieux gérer mon stress, jour après jour."),
    dict(username="hoda_m", pseudonyme="Hoda M.", bio="Maman de deux enfants, j'essaie de prendre soin de moi aussi."),
    dict(username="ismael_d", pseudonyme="Ismael D.", bio="Étudiant en dernière année, l'anxiété et moi on se connaît bien."),
    dict(username="warsame92", pseudonyme="Warsame", bio="Je partage ce qui m'aide, j'espère que ça peut servir à d'autres."),
    dict(username="nadifa_h", pseudonyme="Nadifa H.", bio="En reconstruction après une période difficile. Un jour à la fois."),
    dict(username="zainab_b", pseudonyme="Zainab B.", bio="Infirmière, je connais la fatigue d'aider les autres sans trop s'écouter."),
    dict(username="mo_farah", pseudonyme="Mo Farah", bio="Sport, sommeil, discipline : ce qui me garde debout."),
    dict(username="leyla_j", pseudonyme="Leyla J.", bio="J'écris pour comprendre ce que je ressens."),
    dict(username="abdi_rahman", pseudonyme="Abdi Rahman", bio="Nouveau ici, encore un peu timide mais curieux."),
    dict(username="samira_w", pseudonyme="Samira W.", bio="Je crois beaucoup à la force des groupes de parole."),
]

# (username du compte, catégorie de spécialiste, spécialités, expérience, bio)
SPECIALISTES = [
    ("zainab_b", Psychologue.SPEC_DIETETICIEN, "Nutrition, Troubles alimentaires, Rééquilibrage",
     7, "Diététicienne diplômée, j'accompagne une alimentation apaisée avec le corps, sans restriction ni culpabilité."),
    ("mo_farah", Psychologue.SPEC_COACH_SPORTIF, "Remise en forme, Gestion du stress par le sport, Endurance",
     5, "Coach sportif, je crois que bouger régulièrement change durablement l'humeur et le sommeil."),
    ("samira_w", Psychologue.SPEC_KINESITHERAPEUTE, "Douleurs chroniques, Rééducation, Relaxation musculaire",
     9, "Kinésithérapeute, je travaille le lien entre tensions physiques et charge émotionnelle."),
]

GROUPS = [
    dict(
        name="Anxiété au quotidien", category="anxiete",
        description="Un espace pour parler des petites et grandes angoisses du quotidien, sans jugement.",
        creator="amina_k", members=["amina_k", "ismael_d", "leyla_j", "abdi_rahman", "nadifa_h"],
        conversation=[
            ("amina_k", "Bonsoir tout le monde. Journée difficile, le cœur qui s'emballe pour un rien depuis ce matin."),
            ("ismael_d", "Je connais bien cette sensation avant les examens. Tu as pu respirer un peu depuis ?"),
            ("amina_k", "Un peu oui, j'ai fait l'exercice de respiration du site. Ça aide sur le moment."),
            ("leyla_j", "Pareil pour moi, surtout le soir. Écrire ce qui tourne dans ma tête m'aide à redescendre."),
            ("abdi_rahman", "Je viens d'arriver dans le groupe. Ça fait du bien de voir qu'on n'est pas seul·e avec ça."),
            ("nadifa_h", "Bienvenue Abdi. Ici personne ne te demandera d'aller bien, promis."),
            ("ismael_d", "Si jamais ça devient trop lourd, n'hésite pas à regarder du côté des spécialistes aussi."),
            ("amina_k", "Merci à vous, ça fait vraiment du bien de lire ça ce soir."),
        ],
    ),
    dict(
        name="Sommeil & nuits blanches", category="sommeil",
        description="Insomnies, pensées qui tournent en boucle, rituels du soir : on en parle ici.",
        creator="nadifa_h", members=["nadifa_h", "hoda_m", "warsame92", "samira_w"],
        conversation=[
            ("nadifa_h", "Troisième nuit cette semaine à ne dormir que 3 heures. Je sens que ça joue sur mon humeur."),
            ("hoda_m", "Avec les enfants je connais aussi, mais là ça a l'air plus profond. Depuis quand ça dure ?"),
            ("nadifa_h", "Environ trois semaines, depuis un changement au travail."),
            ("samira_w", "Le corps garde la tension de la journée. Un peu d'étirements doux avant de dormir peut aider."),
            ("warsame92", "Perso j'ai arrêté les écrans une heure avant de me coucher, ça a changé beaucoup de choses."),
            ("nadifa_h", "Je vais essayer ça cette semaine, merci pour vos retours."),
            ("hoda_m", "Tiens-nous au courant, on est là."),
        ],
    ),
    dict(
        name="Confiance en soi", category="confiance",
        description="Se reconstruire, oser prendre sa place, apprendre à s'écouter sans se juger.",
        creator="leyla_j", members=["leyla_j", "abdi_rahman", "zainab_b", "warsame92", "ismael_d"],
        conversation=[
            ("leyla_j", "J'ai enfin postulé pour ce poste dont je parlais. J'étais terrifiée mais je l'ai fait."),
            ("zainab_b", "Bravo Leyla, c'est énorme ce premier pas."),
            ("abdi_rahman", "Ça me motive à lire ça, j'ai moi aussi un entretien la semaine prochaine."),
            ("leyla_j", "Tu vas y arriver Abdi. Rappelle-toi juste que tu as le droit d'être là, comme n'importe qui."),
            ("warsame92", "Cette phrase, je me la note."),
            ("ismael_d", "Ce groupe me fait du bien, on avance ensemble au final."),
        ],
    ),
    dict(
        name="Deuil et perte", category="deuil",
        description="Un cercle doux pour celles et ceux qui traversent une perte, à leur rythme.",
        creator="samira_w", members=["samira_w", "hoda_m", "nadifa_h"],
        conversation=[
            ("samira_w", "Un an aujourd'hui depuis le décès de mon père. La journée est plus lourde que d'habitude."),
            ("hoda_m", "Je pense fort à toi aujourd'hui. Les dates anniversaires sont particulières, c'est normal."),
            ("nadifa_h", "Tu n'as pas à être forte aujourd'hui. Prends soin de toi, on est là si besoin."),
            ("samira_w", "Merci, ça compte beaucoup de lire vos mots ce soir."),
        ],
    ),
]

# (username auteur, type, titre, sous_titre, contenu, tags)
POSTS = [
    ("amina_k", "post", "", "",
     "Petite victoire du jour : j'ai réussi à dire non à une sollicitation qui m'épuisait, sans me justifier pendant 10 minutes. Ça se fête 🙂",
     "confiance,limites"),
    ("ismael_d", "post", "", "",
     "Les examens approchent et mon cœur bat la chamade rien qu'à l'idée d'ouvrir mes cours. Si vous avez des rituels anti-stress, je suis preneur.",
     "anxiété,études"),
    ("warsame92", "post", "", "",
     "Rappel du jour : demander de l'aide n'est pas un échec, c'est une preuve de lucidité. Belle semaine à tout le monde 🌿",
     "soutien"),
    ("hoda_m", "post", "", "",
     "Les enfants couchés, la maison enfin silencieuse. Ces dix minutes de calme avant de dormir, c'est mon luxe à moi.",
     "quotidien,parentalité"),
    ("leyla_j", "post", "", "",
     "J'ai recommencé mon journal intime cette semaine après des mois de pause. Première ligne : « je ne sais pas trop par où commencer, mais je commence. »",
     "journal,écriture"),
    ("zainab_b", "post", "", "",
     "Petit rappel de diététicienne : sauter un repas pour « gagner du temps » coûte souvent plus cher en énergie l'après-midi. Mangez, même vite, même simple.",
     "nutrition,conseil"),
    ("mo_farah", "post", "", "",
     "20 minutes de marche rapide ce matin avant le soleil. Rien ne change la tête comme un peu d'air et un cœur qui s'accélère pour les bonnes raisons.",
     "sport,routine"),
    ("abdi_rahman", "post", "", "",
     "Première fois que j'écris ici. Je ne sais pas encore comment ça marche vraiment mais je suis content d'avoir fait le pas de m'inscrire.",
     "nouveau"),
    ("nadifa_h", "post", "", "",
     "On ne le dit pas assez : se reconstruire, ce n'est pas une ligne droite. Il y a des bons jours, des moins bons, et c'est ok.",
     "résilience"),
    ("samira_w", "blog", "Ce que le deuil m'a appris sur la patience", "Un an après, quelques mots pour celles et ceux qui traversent la même épreuve",
     "On me dit souvent « le temps guérit tout ». Un an après le décès de mon père, je ne suis plus sûre que ce soit vrai — "
     "je crois plutôt que le temps nous apprend à porter la perte autrement, pas à la faire disparaître.\n\n"
     "Les premiers mois, j'attendais que la douleur s'arrête, comme une fièvre qui finirait par tomber. Elle ne s'est pas arrêtée, "
     "elle a juste changé de forme : moins de vagues qui submergent tout, plus de moments où le souvenir revient doucement, presque "
     "tendrement.\n\n"
     "Ce qui m'a aidée, concrètement : en parler sans me forcer à « aller mieux » pour rassurer les autres, accepter les mauvais jours "
     "sans les combattre, et surtout ne pas traverser ça seule. Le groupe de parole que j'ai rejoint ici m'a appris que je n'étais pas "
     "la seule à avancer à ce rythme irrégulier.\n\n"
     "Si vous traversez une perte en ce moment : prenez le temps qu'il vous faut. Il n'y a pas de bonne façon de faire son deuil, "
     "seulement la vôtre.",
     "deuil,témoignage"),
    ("leyla_j", "blog", "Mon retour au journal intime, trois mois après", "Pourquoi j'ai arrêté d'écrire, et pourquoi j'ai recommencé",
     "J'ai tenu un journal pendant deux ans, presque tous les soirs. Puis, sans vraiment m'en rendre compte, j'ai arrêté. "
     "Trop fatiguée, trop occupée, ou peut-être simplement pas envie de me regarder en face certains soirs.\n\n"
     "Ce qui m'a fait reprendre, c'est une phrase lue ici même : « vous pouvez arriver fatigué·e, en colère, perdu·e, ou simplement "
     "curieux·se ». Je me suis dit que je n'avais pas besoin d'écrire quelque chose de beau ou d'organisé, juste d'écrire vrai.\n\n"
     "Ma première ligne, après des mois de silence, a été maladroite : « je ne sais pas trop par où commencer, mais je commence. » "
     "Et c'est exactement ce dont j'avais besoin : commencer, sans pression.\n\n"
     "Si vous hésitez à reprendre une habitude que vous avez laissée tomber, mon conseil : ne cherchez pas la version parfaite de "
     "vous-même qui recommence. Prenez juste la version d'aujourd'hui, telle qu'elle est.",
     "journal,écriture,habitudes"),
    ("zainab_b", "article", "Manger pendant les périodes de stress : trois repères simples", "Quelques conseils concrets d'une diététicienne, sans régime ni culpabilité",
     "Quand le stress s'installe, l'alimentation est souvent la première chose qu'on néglige, ou à l'inverse celle vers laquelle on "
     "se réfugie. Ni l'un ni l'autre n'est un problème en soi — ce qui compte, c'est de garder quelques repères simples.\n\n"
     "1. Ne sautez pas de repas « pour gagner du temps ». Le corps compense souvent plus tard par des fringales ou une grosse "
     "fatigue en fin de journée.\n\n"
     "2. Gardez toujours une option simple sous la main : des fruits secs, un œuf, du pain et du fromage. L'objectif n'est pas "
     "de cuisiner un plat équilibré à chaque repas, juste de ne pas rester à jeun trop longtemps.\n\n"
     "3. Hydratez-vous régulièrement. La déshydratation légère est souvent confondue avec de la fatigue ou de l'irritabilité.\n\n"
     "Si manger est devenu une source d'angoisse plutôt qu'un besoin simple, n'hésitez pas à en parler à un professionnel — "
     "c'est exactement pour ça que ce service existe.",
     "nutrition,stress,guide"),
    ("mo_farah", "article", "Le sport, un allié contre l'anxiété (et pas seulement pour le physique)", "Pourquoi 20 minutes de marche valent parfois mieux qu'une heure de rumination",
     "On pense souvent au sport comme un outil pour la santé physique uniquement. Pourtant, l'activité physique régulière reste "
     "l'un des moyens les plus simples et accessibles de réduire l'anxiété au quotidien.\n\n"
     "Pas besoin de courir un marathon : une marche rapide de 20 minutes suffit à faire baisser le niveau de cortisol et à "
     "relancer la production d'endorphines. L'essentiel n'est pas l'intensité, mais la régularité.\n\n"
     "Mon conseil pour commencer sans se décourager : choisissez un horaire fixe, même court, et ne visez pas la performance. "
     "Le but n'est pas de « faire du sport » au sens compétitif, mais de donner à votre corps une sortie physique pour une "
     "tension qui, sinon, reste coincée dans la tête.\n\n"
     "Si l'idée de bouger seul·e vous pèse, les groupes de parole de l'application peuvent aussi être un bon point de départ "
     "pour trouver un rythme avec d'autres personnes.",
     "sport,anxiété,routine"),
]


class Command(BaseCommand):
    help = "Crée 10 utilisateurs de démonstration, quelques spécialistes, des groupes actifs et une quinzaine de publications."

    def handle(self, *args, **options):
        with transaction.atomic():
            users = self._create_users()
            self._create_specialistes(users)
            self._create_groups(users)
            self._create_posts(users)
            self._create_follows(users)

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé. {len(users)} comptes de démonstration créés.\n"
            f"Mot de passe commun : {DEMO_PASSWORD}\n"
        ))

    def _create_users(self):
        users = {}
        for u in USERS:
            email = f"{u['username']}@{EMAIL_DOMAIN}"
            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults=dict(username=u["username"], pseudonyme=u["pseudonyme"], bio=u["bio"]),
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])
                self.stdout.write(f"  + utilisateur créé : {user.pseudonyme}")
            else:
                self.stdout.write(f"  = utilisateur déjà présent : {user.pseudonyme}")
            users[u["username"]] = user
        return users

    def _create_specialistes(self, users):
        for username, type_specialiste, specialites, experience_ans, bio in SPECIALISTES:
            user = users[username]
            Psychologue.objects.get_or_create(
                user=user,
                defaults=dict(
                    type_specialiste=type_specialiste,
                    specialites=specialites,
                    biographie=bio,
                    experience_ans=experience_ans,
                    est_actif=True,
                ),
            )
        self.stdout.write(f"  + {len(SPECIALISTES)} profils spécialistes créés/vérifiés")

    def _create_groups(self, users):
        now = timezone.now()
        for g in GROUPS:
            group, created = ForumGroup.objects.get_or_create(
                name=g["name"],
                defaults=dict(
                    description=g["description"],
                    category=g["category"],
                    creator=users[g["creator"]],
                ),
            )
            if not created:
                self.stdout.write(f"  = groupe déjà présent : {group.name}")
                continue

            for username in g["members"]:
                group.members.add(users[username])
                GroupMemberStatus.objects.get_or_create(group=group, user=users[username])

            base_time = now - timedelta(days=random.randint(2, 6), hours=random.randint(0, 5))
            for i, (username, content) in enumerate(g["conversation"]):
                msg = GroupMessage.objects.create(
                    group=group, sender=users[username], content=content,
                )
                sent_at = base_time + timedelta(minutes=i * random.randint(4, 22))
                GroupMessage.objects.filter(pk=msg.pk).update(created_at=sent_at)
                # quelques likes pour les messages les plus "forts"
                if i >= 2 and random.random() < 0.5:
                    liker = random.choice(g["members"])
                    if liker != username:
                        msg.likes.add(users[liker])

            self.stdout.write(f"  + groupe créé : {group.name} ({len(g['members'])} membres, {len(g['conversation'])} messages)")

    def _create_posts(self, users):
        now = timezone.now()
        created_posts = []
        for i, (username, type_, titre, sous_titre, contenu, tags) in enumerate(POSTS):
            exists = Post.objects.filter(auteur=users[username], contenu=contenu).exists()
            if exists:
                continue
            post = Post.objects.create(
                auteur=users[username], type=type_, titre=titre, sous_titre=sous_titre,
                contenu=contenu, tags=tags,
            )
            posted_at = now - timedelta(days=random.randint(0, 9), hours=random.randint(0, 20))
            Post.objects.filter(pk=post.pk).update(date_creation=posted_at, date_modification=posted_at)
            created_posts.append(post)

        all_usernames = list(users.keys())
        comments_bank = [
            "Merci de l'avoir partagé, ça résonne beaucoup avec ce que je vis en ce moment.",
            "C'est exactement ce dont j'avais besoin de lire aujourd'hui.",
            "Courage à toi, tu n'es pas seul·e sur ce sujet.",
            "Très utile, je vais essayer ça dès cette semaine.",
            "Merci pour ta franchise, ça fait du bien de lire des mots vrais.",
        ]
        for post in created_posts:
            likers = random.sample(all_usernames, k=min(random.randint(1, 5), len(all_usernames)))
            for liker in likers:
                if users[liker] != post.auteur:
                    post.likes.add(users[liker])
            if random.random() < 0.6:
                commenter = random.choice([u for u in all_usernames if u != post.auteur.username] or all_usernames)
                CommentairePost.objects.create(
                    post=post, auteur=users[commenter], contenu=random.choice(comments_bank),
                )
        self.stdout.write(f"  + {len(created_posts)} publications créées")

    def _create_follows(self, users):
        pairs = [
            ("ismael_d", "amina_k"), ("abdi_rahman", "leyla_j"), ("hoda_m", "zainab_b"),
            ("warsame92", "mo_farah"), ("nadifa_h", "samira_w"), ("leyla_j", "nadifa_h"),
        ]
        created = 0
        for follower, following in pairs:
            _, was_created = Follow.objects.get_or_create(
                follower=users[follower], following=users[following],
            )
            created += int(was_created)
        self.stdout.write(f"  + {created} abonnements créés")
