
import os
import sys
import django
import traceback
import pymysql
pymysql.install_as_MySQLdb()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlacementPortal.settings')
django.setup()

from django.test import RequestFactory
from interviews.views import start_voice_interview
from django.contrib.auth import get_user_model
from interviews.models import Interview

User = get_user_model()
interviews = Interview.objects.all()
print(f"DEBUG: Found {interviews.count()} interviews")
i = interviews.first()
if not i:
    print("NO INTERVIEWS FOUND")
    sys.exit(1)
user = i.student
print(f"DEBUG: Using Interview ID {i.id} for user {user.username}")
i.status = 'in_progress'
i.save()

factory = RequestFactory()
request = factory.post('/interview/api/voice/start/')
request.user = user

try:
    response = start_voice_interview(request)
    print(f"STATUS: {response.status_code}")
    print(f"BODY: {response.content}")
except Exception:
    traceback.print_exc()
