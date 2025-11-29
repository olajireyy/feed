from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import re

class UserProfile(models.Model):
    """
    Extended user profile with campus-specific information
    """
    DEPARTMENT_CHOICES = [
        ('CS', 'Computer Science'),
        ('ENG', 'Engineering'),
        ('MED', 'Medicine'),
        ('LAW', 'Law'),
        ('BUS', 'Business Administration'),
        ('ART', 'Arts'),
        ('SCI', 'Sciences'),
        ('EDU', 'Education'),
        ('OTHER', 'Other'),
    ]
    
    LEVEL_CHOICES = [
        ('100', '100 Level'),
        ('200', '200 Level'),
        ('300', '300 Level'),
        ('400', '400 Level'),
        ('500', '500 Level'),
        ('GRAD', 'Graduate'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, blank=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, blank=True)
    bio = models.TextField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_profile_picture_url(self):
        """Return profile picture URL or default avatar"""
        if self.profile_picture:
            return self.profile_picture.url
        return None
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'


class Post(models.Model):
    """
    Main post model for CampusFeed
    """
    CATEGORY_CHOICES = [
        ('GENERAL', 'General'),
        ('FUNNY', 'Funny/Memes'),
        ('EVENT', 'Events'),
        ('CONFESSION', 'Confession'),
        ('LOST_FOUND', 'Lost & Found'),
        ('ACADEMIC', 'Academic'),
        ('SPORTS', 'Sports'),
        ('NEWS', 'Campus News'),
        ('QUESTION', 'Question'),
    ]
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    content = models.TextField()
    image = models.ImageField(upload_to='posts/', blank=True, null=True)  # Keep for backward compatibility
    video = models.FileField(upload_to='videos/', blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='GENERAL')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    shares_count = models.IntegerField(default=0)
    
    def __str__(self):
        author_name = "Anonymous" if self.is_anonymous else self.author.username
        return f"{author_name} - {self.content[:50]}"
    
    class Meta:
        ordering = ['-created_at']  # Latest posts first
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
    
    def update_likes_count(self):
        """Update the cached likes count"""
        self.likes_count = self.likes.count()
        self.save(update_fields=['likes_count'])
    
    def update_comments_count(self):
        """Update the cached comments count"""
        self.comments_count = self.comments.count()
        self.save(update_fields=['comments_count'])
    
    def get_author_display(self):
        """Return author name or Anonymous"""
        if self.is_anonymous:
            return "Anonymous"
        return self.author.username if self.author else "Unknown"
    
    def extract_hashtags(self):
        """Extract hashtags from content"""
        return re.findall(r'#(\w+)', self.content)
    
    def get_content_with_hashtag_links(self):
        """Return content with clickable hashtag links"""
        content = self.content
        hashtags = self.extract_hashtags()
        for tag in hashtags:
            content = content.replace(
                f'#{tag}',
                f'<a href="/feed/?q=%23{tag}" class="text-primary text-decoration-none">#{tag}</a>'
            )
        return content
    
    def get_author_info(self):
        """Return author info for display"""
        if self.is_anonymous or not self.author:
            return {
                'username': 'Anonymous',
                'department': '',
                'level': '',
                'profile_picture': None
            }
        try:
            profile = self.author.profile
            return {
                'username': self.author.username,
                'department': profile.get_department_display() if profile.department else '',
                'level': profile.get_level_display() if profile.level else '',
                'profile_picture': profile.get_profile_picture_url()
            }
        except UserProfile.DoesNotExist:
            return {
                'username': self.author.username,
                'department': '',
                'level': '',
                'profile_picture': None
            }

    # Add these methods to your Post model class

    def has_media(self):
        """Check if post has any media attached"""
        return self.images.exists() or bool(self.video) or bool(self.image)

    def get_image_count(self):
        """Get count of images (including old single image field)"""
        count = self.images.count()
        if self.image and not self.images.exists():
            count += 1
        return count

    def get_all_images(self):
        """Get all images including the old single image field if it exists"""
        images_list = list(self.images.all())
        # If old image field has content and no new images, include it
        if self.image and not images_list:
            # Return a list-like structure for template consistency
            return [{'image': self.image, 'is_old_format': True}]
        return images_list

    def get_first_image(self):
        """Get first image for thumbnail/preview"""
        if self.images.exists():
            return self.images.first().image
        elif self.image:
            return self.image
        return None


class Like(models.Model):
    """
    Like model for posts
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'post')  # User can only like a post once
        verbose_name = 'Like'
        verbose_name_plural = 'Likes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} likes post {self.post.id}"


class Comment(models.Model):
    """
    Comment model for posts
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    content = models.TextField()
    image = models.ImageField(upload_to='comment_images/', blank=True, null=True)
    video = models.FileField(upload_to='comment_videos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']  # Oldest comments first
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'
    
    def __str__(self):
        author_name = "Anonymous" if self.is_anonymous else (self.author.username if self.author else "Unknown")
        return f"{author_name} commented on post {self.post.id}"
    
    def get_author_display(self):
        """Return author name or Anonymous"""
        if self.is_anonymous:
            return "Anonymous"
        return self.author.username if self.author else "Unknown"


class Bookmark(models.Model):
    """
    Bookmark model for saving posts
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'post')
        verbose_name = 'Bookmark'
        verbose_name_plural = 'Bookmarks'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} bookmarked post {self.post.id}"


class PostImage(models.Model):
    """
    Model for storing multiple images per post
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='post_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name = 'Post Image'
        verbose_name_plural = 'Post Images'
    
    def __str__(self):
        return f"Image for post {self.post.id}"


class Conversation(models.Model):
    """
    Conversation thread between two users
    """
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def get_other_participant(self, user):
        """Get the other user in the conversation"""
        return self.participants.exclude(id=user.id).first()
    
    def get_last_message(self):
        """Get the most recent message"""
        return self.messages.first()
    
    def get_unread_count(self, user):
        """Get unread message count for a user"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()
    
    def __str__(self):
        users = self.participants.all()
        return f"Conversation: {', '.join([u.username for u in users])}"


class DirectMessage(models.Model):
    """
    Direct messaging between users
    """
    MESSAGE_TYPE_CHOICES = [
        ('TEXT', 'Text'),
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
        ('VOICE', 'Voice Note'),
        ('POST', 'Shared Post'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default='TEXT')
    content = models.TextField(blank=True)
    
    # Media attachments
    image = models.ImageField(upload_to='dm_images/', blank=True, null=True)
    video = models.FileField(upload_to='dm_videos/', blank=True, null=True)
    voice_note = models.FileField(upload_to='dm_voice/', blank=True, null=True)
    voice_duration = models.IntegerField(null=True, blank=True)  # Duration in seconds
    
    # Shared post
    post = models.ForeignKey('Post', on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_dms')
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']  # Oldest first for chat display
        verbose_name = 'Direct Message'
        verbose_name_plural = 'Direct Messages'
    
    def save(self, *args, **kwargs):
        # Auto-detect message type
        if self.voice_note:
            self.message_type = 'VOICE'
        elif self.video:
            self.message_type = 'VIDEO'
        elif self.image:
            self.message_type = 'IMAGE'
        elif self.post:
            self.message_type = 'POST'
        else:
            self.message_type = 'TEXT'
        
        super().save(*args, **kwargs)
        
        # Update conversation timestamp
        if self.conversation:
            self.conversation.save()  # Triggers updated_at
    
    def __str__(self):
        return f"{self.sender.username} to {self.recipient.username}: {self.message_type}"


class PostShare(models.Model):
    """
    Track post shares
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shares')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='share_records')
    shared_via = models.CharField(max_length=20, choices=[
        ('LINK', 'Link'),
        ('DM', 'Direct Message'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Post Share'
        verbose_name_plural = 'Post Shares'
    
    def __str__(self):
        return f"{self.user.username} shared post {self.post.id}"


class Follow(models.Model):
    """
    Follow relationship between users
    """
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']
        verbose_name = 'Follow'
        verbose_name_plural = 'Follows'
    
    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"