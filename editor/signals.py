import random

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, ParticipantProfile


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, **kwargs):
    Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_participant_profile(sender, instance, created, **kwargs):
    if created:
        # assign C or E at random (or your own logic)
        # group = random.choice([
        #     # ParticipantProfile.CONTROL,
        #     # ParticipantProfile.EXPERIMENTAL
        # ])
        ParticipantProfile.objects.create(user=instance)
