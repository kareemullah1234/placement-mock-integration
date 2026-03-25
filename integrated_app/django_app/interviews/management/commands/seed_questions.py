import csv
import os
from django.core.management.base import BaseCommand
from interviews.models import Question
from django.conf import settings

class Command(BaseCommand):
    help = 'Seed questions from data_science_questions.csv'

    def handle(self, *args, **options):
        csv_path = os.path.join(settings.BASE_DIR, 'data_science_questions.csv')
        
        self.stdout.write(f"Reading CSV from: {csv_path}")
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'CSV file not found at {csv_path}'))
            return

        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                question_text = row.get('question', '').strip()
                category = row.get('category', 'General').strip()
                difficulty = row.get('difficulty', 'Medium').strip()

                if not question_text:
                    continue

                Question.objects.get_or_create(
                    question_text=question_text,
                    defaults={
                        'category': category,
                        'difficulty': difficulty
                    }
                )
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {count} questions'))
