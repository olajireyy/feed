"""
URL configuration for feed app
"""
from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Feed
    path('feed/', views.feed_view, name='feed'),
    path('trending/', views.trending_view, name='trending'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('bookmarks/', views.bookmarks_view, name='bookmarks'),
    
    # Posts
    path('posts/create/', views.create_post_view, name='create_post'),
    path('posts/new/', views.create_post_page_view, name='create_post_page'),
    path('post/<int:post_id>/', views.post_detail_view, name='post_detail'),
    path('post/<int:post_id>/edit/', views.edit_post_view, name='edit_post'),
    path('post/<int:post_id>/delete/', views.delete_post_view, name='delete_post'),
    path('posts/<int:post_id>/like/', views.toggle_like_view, name='toggle_like'),
    path('posts/<int:post_id>/bookmark/', views.toggle_bookmark_view, name='toggle_bookmark'),
    path('posts/<int:post_id>/comments/', views.get_comments_view, name='get_comments'),
    path('posts/<int:post_id>/comment/', views.add_comment_view, name='add_comment'),
    path('comments/<int:comment_id>/delete/', views.delete_comment_view, name='delete_comment'),

    #Share
     path('posts/<int:post_id>/share-dm/', views.share_post_dm, name='share_post_dm'),
    path('posts/<int:post_id>/share/', views.get_share_link_view, name='get_share_link'),
    
    
    # Users
    path('user/<int:user_id>/follow/', views.toggle_follow_view, name='toggle_follow'),
    path('@<str:username>/', views.public_profile_view, name='public_profile'),
    
    # Profile
    path('profile/edit/', views.profile_view, name='edit_profile'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('profile/', views.profile_view, name='myprofile'),

    # Search
    path('search/', views.search, name='search'),

    #refresh
    path('api/posts/check-new/', views.check_new_posts, name='check_new_posts'),
    path('api/posts/load-new/', views.load_new_posts, name='load_new_posts'),
    path('api/posts/load-more/', views.load_more_posts, name='load_more_posts'),

# DM URLs
    path('messages/', views.messages_inbox, name='messages_inbox'),
    path('messages/unread-count/', views.get_unread_count, name='dm_unread_count'),
    path('messages/search-users/', views.search_users_dm, name='search_users_dm'),
    path('messages/<str:username>/', views.conversation_view, name='conversation'),
    path('messages/<str:username>/send/', views.send_message, name='send_message'),
    path('messages/<str:username>/new/', views.get_new_messages, name='get_new_messages'),
    path('messages/<str:username>/mark-read/', views.mark_conversation_read, name='mark_conversation_read'),
    path('messages/message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('posts/<int:post_id>/share-dm/', views.share_post_dm, name='share_post_dm'),
    path('start-conversation/<str:username>/', views.start_conversation, name='start_conversation'),
]