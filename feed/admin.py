from django.contrib import admin
from .models import UserProfile, Post, Like, Comment, Bookmark, PostImage, DirectMessage, PostShare, Follow

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'department', 'level', 'created_at']
    list_filter = ['department', 'level', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_author_display', 'category', 'is_anonymous', 'likes_count', 'comments_count', 'created_at']
    list_filter = ['category', 'is_anonymous', 'created_at']
    search_fields = ['content', 'author__username']
    readonly_fields = ['created_at', 'updated_at', 'likes_count', 'comments_count']
    date_hierarchy = 'created_at'
    
    def get_author_display(self, obj):
        return obj.get_author_display()
    get_author_display.short_description = 'Author'
    
    actions = ['delete_selected_posts']
    
    def delete_selected_posts(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} post(s) successfully deleted.')
    delete_selected_posts.short_description = 'Delete selected posts'


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'post__content']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['get_author_display', 'post', 'content_preview', 'is_anonymous', 'created_at']
    list_filter = ['is_anonymous', 'created_at']
    search_fields = ['content', 'author__username', 'post__content']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def get_author_display(self, obj):
        return obj.get_author_display()
    get_author_display.short_description = 'Author'
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'post__content']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ['post', 'order', 'uploaded_at']
    list_filter = ['uploaded_at']
    readonly_fields = ['uploaded_at']


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__username', 'recipient__username', 'content']
    readonly_fields = ['created_at']


@admin.register(PostShare)
class PostShareAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'shared_via', 'created_at']
    list_filter = ['shared_via', 'created_at']
    readonly_fields = ['created_at']