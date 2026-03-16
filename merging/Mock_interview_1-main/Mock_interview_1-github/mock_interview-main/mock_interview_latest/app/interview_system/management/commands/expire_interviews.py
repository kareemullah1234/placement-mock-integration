expire_interviews.py


from django.core.management.base import BaseCommand
from django.utils import timezone
from interview_system.models import Interview

class Command(BaseCommand):
    help = 'Expire approved interviews that have exceeded 10-minute timeout'

    def handle(self, *args, **options):
        # Find approved interviews that have expired
        expired_interviews = Interview.objects.filter(
            status='approved',
            approval_expires_at__lt=timezone.now()
        )
        
        count = expired_interviews.count()
        
        # Update status to expired
        expired_interviews.update(
            status='expired',
            admin_notes='Interview expired - not started within 10 minutes of approval'
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully expired {count} interviews')
        )
