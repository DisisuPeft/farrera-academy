from django.core.management.base import BaseCommand
from user.models import Role
import uuid

class Command(BaseCommand):
    help = 'Pobla UUIDs para registros existentes sin UUID'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la operacion sin'
        )
    
    def handle(self, *args, **options):
        
        dry_run = options['dry_run']
        
        sin_uuid = Role.objects.filter(uuid__isnull=True)
        total = sin_uuid.count()
        print(total)
        counter = 0
        for obj in sin_uuid:
            obj.uuid = uuid.uuid4()
            
            if not dry_run:
                obj.save(update_fields=['uuid'])
            counter += 1
        print(counter)   
            