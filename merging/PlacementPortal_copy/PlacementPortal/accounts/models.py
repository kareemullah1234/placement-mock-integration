import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('candidate', 'Candidate'),
        ('company', 'Company'),
        ('admin', 'Admin'),
    ]

    # ── Original PlacementPortal field ────────────────────────────────────
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, default='candidate')

    # ── Merged from Mock Interview CustomUser ─────────────────────────────
    # UUID to identify a candidate externally (used by Flask audio API too)
    candidate_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        null=True,
        blank=True,
        help_text="External UUID identifier (used by audio analysis API)"
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    # Convenience flag — True when user is a student in the mock interview system
    is_student = models.BooleanField(
        default=False,
        help_text="True if this user participates in mock interviews as a student"
    )

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return f"{self.get_full_name()} ({self.username}) [{self.role}]"