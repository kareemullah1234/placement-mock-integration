from django.core.management.base import BaseCommand
from interview_system.models import Question
from django.conf import settings
import csv
import os


class Command(BaseCommand):
    help = "Load questions from CSV into Question model"

    def handle(self, *args, **kwargs):
        file_path = os.path.join(settings.BASE_DIR, 'data_science_questions.csv')

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found at {file_path}"))
            return

        with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)

            self.stdout.write(f"CSV Headers detected: {reader.fieldnames}")

            count = 0

            for row in reader:
                question_text = row.get('question') or row.get('questions')

                if question_text:
                    Question.objects.create(
                        question_text=question_text,
                        category=row.get('category', 'General'),
                        difficulty=row.get('difficulty', 'Medium')
                    )
                    count += 1

        self.stdout.write(self.style.SUCCESS(f"{count} questions imported successfully."))
