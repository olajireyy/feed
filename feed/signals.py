from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile, Like, Comment

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile when a new User is created
    """
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the UserProfile when User is saved
    """
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=Like)
def update_post_likes_on_create(sender, instance, created, **kwargs):
    """
    Update post likes count when a like is created
    """
    if created:
        instance.post.update_likes_count()


@receiver(post_delete, sender=Like)
def update_post_likes_on_delete(sender, instance, **kwargs):
    """
    Update post likes count when a like is deleted
    """
    instance.post.update_likes_count()


@receiver(post_save, sender=Comment)
def update_post_comments_on_create(sender, instance, created, **kwargs):
    """
    Update post comments count when a comment is created
    """
    if created:
        instance.post.update_comments_count()


@receiver(post_delete, sender=Comment)
def update_post_comments_on_delete(sender, instance, **kwargs):
    """
    Update post comments count when a comment is deleted
    """
    instance.post.update_comments_count()