from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile

@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        role = 'admin' if instance.is_superuser else 'patient'
        UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
    else:
        try:
            instance.profile.save()
        except UserProfile.DoesNotExist:
            role = 'admin' if instance.is_superuser else 'patient'
            UserProfile.objects.create(user=instance, role=role)
