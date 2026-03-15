# Créez ce fichier : application/management/commands/migrate_ressources.py

from django.core.management.base import BaseCommand
from application.models import Ressource

class Command(BaseCommand):
    help = 'Migre les anciens types de ressources vers les nouveaux types'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('\n🔄 Début de la migration des ressources...\n'))
        
        # Mapping des anciens types vers les nouveaux
        mapping = {
            'audio': 'podcast',
            'infographie': 'article',
            'exercice': 'atelier',
        }
        
        total_migrated = 0
        
        for old_type, new_type in mapping.items():
            # Compter les ressources à migrer
            count = Ressource.objects.filter(type_ressource=old_type).count()
            
            if count > 0:
                self.stdout.write(f'\n📊 Trouvé {count} ressource(s) de type "{old_type}"')
                
                # Lister les ressources concernées
                ressources = Ressource.objects.filter(type_ressource=old_type)
                for ressource in ressources:
                    self.stdout.write(f'   - {ressource.titre}')
                
                # Demander confirmation
                confirm = input(f'\n❓ Migrer ces ressources vers "{new_type}" ? (o/n): ')
                
                if confirm.lower() in ['o', 'oui', 'y', 'yes']:
                    updated = Ressource.objects.filter(type_ressource=old_type).update(
                        type_ressource=new_type
                    )
                    total_migrated += updated
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ {updated} ressource(s) migrée(s) de "{old_type}" vers "{new_type}"\n'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⏭️  Migration de "{old_type}" ignorée\n')
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Aucune ressource de type "{old_type}" trouvée\n')
                )
        
        # Résumé final
        self.stdout.write('\n' + '='*60)
        if total_migrated > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n🎉 Migration terminée avec succès !\n'
                    f'   Total: {total_migrated} ressource(s) migrée(s)\n'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '\n✅ Aucune migration nécessaire. Toutes vos ressources sont à jour !\n'
                )
            )
        self.stdout.write('='*60 + '\n')