from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .forms import UserRegistrationForm, UserLoginForm, ProfileUpdateForm, PostForm
from .models import Post, Like, Comment, Bookmark, PostImage, DirectMessage, PostShare, Follow
import json

def home(request):
    """
    Home page - redirects to feed if logged in, otherwise to login
    """
    if request.user.is_authenticated:
        return redirect('feed')
    return redirect('login')


def register_view(request):
    """
    User registration view
    """
    if request.user.is_authenticated:
        return redirect('feed')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log the user in after registration
            messages.success(request, f'Welcome to CampusFeed, {user.username}! 🎉')
            return redirect('feed')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'feed/register.html', {'form': form})


def login_view(request):
    """
    User login view
    """
    if request.user.is_authenticated:
        return redirect('feed')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}! 👋')
                
                # Redirect to next page if specified, otherwise to feed
                next_page = request.GET.get('next', 'feed')
                return redirect(next_page)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'feed/login.html', {'form': form})


@login_required
def logout_view(request):
    """
    User logout view
    """
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def feed_view(request):
    """
    Main feed view with post creation and display
    """
    # Get category filter from query params
    category = request.GET.get('category', 'all')
    search_query = request.GET.get('q', '').strip()
    
    # Get all posts or filter by category
    if category == 'all' or not category:
        posts = Post.objects.all()
    else:
        posts = Post.objects.filter(category=category)
    
    # Apply search filter if query exists
    if search_query:
        posts = posts.filter(content__icontains=search_query)
    
    # Get posts with related data to reduce queries
    posts = posts.select_related('author', 'author__profile').prefetch_related('likes', 'comments')
    
    # Pagination
    paginator = Paginator(posts, 10)  # 10 posts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get post IDs that current user has liked
    liked_post_ids = Like.objects.filter(user=request.user).values_list('post_id', flat=True)
    
    # Get post IDs that current user has bookmarked
    bookmarked_post_ids = Bookmark.objects.filter(user=request.user).values_list('post_id', flat=True)
    
    # Create post form
    form = PostForm()
    
    context = {
        'form': form,
        'posts': page_obj,
        'category': category,
        'categories': Post.CATEGORY_CHOICES,
        'liked_post_ids': list(liked_post_ids),
        'bookmarked_post_ids': list(bookmarked_post_ids),
        'search_query': search_query,
    }
    
    return render(request, 'feed/modern_feed.html', context)


@login_required
def profile_view(request):
    """
    User profile view and edit
    """
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated! ✅')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    
    # Get user statistics
    total_posts = Post.objects.filter(author=request.user).count()
    total_likes_received = Like.objects.filter(post__author=request.user).count()
    total_comments = Comment.objects.filter(author=request.user).count()
    
    # Get user's posts
    posts = Post.objects.filter(author=request.user).select_related(
        'author', 'author__profile'
    ).prefetch_related('likes', 'comments', 'images').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get post IDs that current user has liked and bookmarked
    liked_post_ids = Like.objects.filter(user=request.user).values_list('post_id', flat=True)
    bookmarked_post_ids = Bookmark.objects.filter(user=request.user).values_list('post_id', flat=True)
    
    context = {
        'form': form,
        'user': request.user,
        'total_posts': total_posts,
        'total_likes_received': total_likes_received,
        'total_comments': total_comments,
        'posts': page_obj,
        'liked_post_ids': list(liked_post_ids),
        'bookmarked_post_ids': list(bookmarked_post_ids),
    }
    
    return render(request, 'feed/profile.html', context)


@login_required
@require_POST
def create_post_view(request):
    """
    Create a new post via AJAX
    """
    form = PostForm(request.POST, request.FILES)
    
    if form.is_valid():
        post = form.save(commit=False)
        
        # Set author (even for anonymous posts, we track who posted)
        post.author = request.user
        post.save()
        
        # Get author info for response
        author_info = post.get_author_info()
        
        # Return post data as JSON
        return JsonResponse({
            'success': True,
            'post': {
                'id': post.id,
                'content': post.content,
                'image_url': post.image.url if post.image else None,
                'category': post.get_category_display(),
                'category_value': post.category,
                'is_anonymous': post.is_anonymous,
                'author': author_info,
                'created_at': post.created_at.strftime('%B %d, %Y %I:%M %p'),
                'likes_count': post.likes_count,
                'comments_count': post.comments_count,
            }
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)


@login_required
@require_POST
def toggle_like_view(request, post_id):
    """
    Toggle like on a post via AJAX
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Check if user already liked the post
    like = Like.objects.filter(user=request.user, post=post).first()
    
    if like:
        # Unlike the post
        like.delete()
        liked = False
    else:
        # Like the post
        Like.objects.create(user=request.user, post=post)
        liked = True
    
    # Get updated like count
    post.refresh_from_db()
    
    return JsonResponse({
        'success': True,
        'liked': liked,
        'likes_count': post.likes_count
    })


@login_required
def get_comments_view(request, post_id):
    """
    Get comments for a post via AJAX
    """
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.select_related('author', 'author__profile').all()
    
    comments_data = []
    for comment in comments:
        author_info = {
            'username': comment.get_author_display(),
            'is_anonymous': comment.is_anonymous
        }
        
        # Add department and level if not anonymous
        if not comment.is_anonymous and comment.author:
            try:
                profile = comment.author.profile
                author_info['department'] = profile.get_department_display() if profile.department else ''
                author_info['level'] = profile.get_level_display() if profile.level else ''
            except:
                pass
        
        comments_data.append({
            'id': comment.id,
            'content': comment.content,
            'author': author_info,
            'created_at': comment.created_at.strftime('%B %d, %Y %I:%M %p'),
            'is_own_comment': comment.author == request.user if comment.author else False
        })
    
    return JsonResponse({
        'success': True,
        'comments': comments_data
    })


@login_required
@require_POST
def add_comment_view(request, post_id):
    """
    Add a comment to a post via AJAX
    """
    post = get_object_or_404(Post, id=post_id)
    
    content = request.POST.get('content', '').strip()
    is_anonymous = request.POST.get('is_anonymous') == 'true'
    image = request.FILES.get('image')
    video = request.FILES.get('video')
    
    if not content and not image and not video:
        return JsonResponse({
            'success': False,
            'error': 'Comment must have content, image, or video'
        }, status=400)
    
    # Create comment
    comment = Comment.objects.create(
        post=post,
        author=request.user,
        content=content,
        is_anonymous=is_anonymous,
        image=image,
        video=video
    )
    
    # Get updated comment count
    post.refresh_from_db()
    
    # Prepare author info
    author_info = {
        'username': comment.get_author_display(),
        'is_anonymous': comment.is_anonymous
    }
    
    if not is_anonymous:
        try:
            profile = request.user.profile
            author_info['department'] = profile.get_department_display() if profile.department else ''
            author_info['level'] = profile.get_level_display() if profile.level else ''
        except:
            pass
    
    return JsonResponse({
        'success': True,
        'comment': {
            'id': comment.id,
            'content': comment.content,
            'author': author_info,
            'created_at': comment.created_at.strftime('%B %d, %Y %I:%M %p'),
            'is_own_comment': True,
            'image_url': comment.image.url if comment.image else None,
            'video_url': comment.video.url if comment.video else None,
        },
        'comments_count': post.comments_count
    })


@login_required
@require_POST
def delete_comment_view(request, comment_id):
    """
    Delete a comment via AJAX
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if user owns the comment
    if comment.author != request.user:
        return JsonResponse({
            'success': False,
            'error': 'You can only delete your own comments'
        }, status=403)
    
    post = comment.post
    comment.delete()
    
    # Get updated comment count
    post.refresh_from_db()
    
    return JsonResponse({
        'success': True,
        'comments_count': post.comments_count
    })


@login_required
def trending_view(request):
    """
    Show trending posts based on engagement in last 24 hours
    """
    # Get posts from last 24 hours
    last_24h = timezone.now() - timedelta(hours=24)
    
    # Calculate engagement score (likes * 2 + comments * 3)
    trending_posts = Post.objects.filter(
        created_at__gte=last_24h
    ).annotate(
        engagement_score=Count('likes') * 2 + Count('comments') * 3
    ).order_by('-engagement_score', '-created_at')[:20]
    
    # Get posts with related data
    trending_posts = trending_posts.select_related('author', 'author__profile').prefetch_related('likes', 'comments')
    
    # Pagination
    paginator = Paginator(trending_posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get post IDs that current user has liked
    liked_post_ids = Like.objects.filter(user=request.user).values_list('post_id', flat=True)
    
    context = {
        'posts': page_obj,
        'liked_post_ids': list(liked_post_ids),
        'is_trending': True,
    }
    
    return render(request, 'feed/trending.html', context)


@login_required
def notifications_view(request):
    """
    Show user notifications
    """
    # Get posts where user received likes
    user_posts = Post.objects.filter(author=request.user)
    recent_likes = Like.objects.filter(
        post__in=user_posts
    ).exclude(
        user=request.user
    ).select_related('user', 'post').order_by('-created_at')[:20]
    
    # Get comments on user's posts
    recent_comments = Comment.objects.filter(
        post__in=user_posts
    ).exclude(
        author=request.user
    ).select_related('author', 'post').order_by('-created_at')[:20]
    
    # Combine and sort by time
    notifications = []
    
    for like in recent_likes:
        notifications.append({
            'type': 'like',
            'user': like.user,
            'post': like.post,
            'created_at': like.created_at,
        })
    
    for comment in recent_comments:
        notifications.append({
            'type': 'comment',
            'user': comment.author,
            'post': comment.post,
            'content': comment.content,
            'created_at': comment.created_at,
        })
    
    # Sort by created_at
    notifications.sort(key=lambda x: x['created_at'], reverse=True)
    notifications = notifications[:30]
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'feed/notifications.html', context)


@login_required
@require_POST
def toggle_bookmark_view(request, post_id):
    """
    Toggle bookmark on a post via AJAX
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Check if user already bookmarked the post
    bookmark = Bookmark.objects.filter(user=request.user, post=post).first()
    
    if bookmark:
        # Remove bookmark
        bookmark.delete()
        bookmarked = False
    else:
        # Add bookmark
        Bookmark.objects.create(user=request.user, post=post)
        bookmarked = True
    
    return JsonResponse({
        'success': True,
        'bookmarked': bookmarked
    })


@login_required
def bookmarks_view(request):
    """
    Show user's bookmarked posts
    """
    bookmarks = Bookmark.objects.filter(user=request.user).select_related(
        'post', 'post__author', 'post__author__profile'
    ).prefetch_related('post__likes', 'post__comments')
    
    # Get just the posts
    posts = [bookmark.post for bookmark in bookmarks]
    
    # Pagination
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get post IDs that current user has liked
    liked_post_ids = Like.objects.filter(user=request.user).values_list('post_id', flat=True)
    
    # Get bookmarked post IDs
    bookmarked_post_ids = [post.id for post in posts]
    
    context = {
        'posts': page_obj,
        'liked_post_ids': list(liked_post_ids),
        'bookmarked_post_ids': bookmarked_post_ids,
        'is_bookmarks': True,
    }
    
    return render(request, 'feed/bookmarks.html', context)


@login_required
def create_post_page_view(request):
    """
    Separate page for creating posts with multiple images or video support
    """
    if request.method == 'POST':
        # Get uploaded media from request.FILES
        images = request.FILES.getlist('images')
        video = request.FILES.get('video')
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', '')
        is_anonymous = request.POST.get('is_anonymous') == 'on'
        
        # Validate that at least one of content, images, or video exists
        if not content and not images and not video:
            messages.error(request, 'Post must have content, images, or video.')
            form = PostForm(request.POST)
            return render(request, 'feed/create_post.html', {'form': form})
        
        # Validate max images
        if len(images) > 4:
            messages.error(request, 'Maximum 4 images allowed per post.')
            form = PostForm(request.POST)
            return render(request, 'feed/create_post.html', {'form': form})
        
        # Validate that both images and video are not uploaded together
        if images and video:
            messages.error(request, 'Cannot upload both images and video in the same post.')
            form = PostForm(request.POST)
            return render(request, 'feed/create_post.html', {'form': form})
        
        # Create the post manually to handle the validation properly
        post = Post(
            author=request.user,
            content=content if content else '',  # Empty string if no content
            category=category if category else 'GENERAL',
            is_anonymous=is_anonymous,
            video=video if video else None
        )
        post.save()
        
        # Save multiple images with order
        for idx, image in enumerate(images):
            PostImage.objects.create(post=post, image=image, order=idx)
        
        messages.success(request, 'Post created successfully! 🎉')
        return redirect('feed')
    else:
        form = PostForm()
    
    return render(request, 'feed/create_post.html', {'form': form})

@login_required
def get_share_link_view(request, post_id):
    """
    Generate shareable link for post
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Track share
    PostShare.objects.create(
        user=request.user,
        post=post,
        shared_via='LINK'
    )
    
    # Update share count
    post.shares_count = post.share_records.count()
    post.save(update_fields=['shares_count'])
    
    share_url = request.build_absolute_uri(f'/post/{post_id}/')
    
    return JsonResponse({
        'success': True,
        'url': share_url
    })


@login_required
@require_POST
def toggle_follow_view(request, user_id):
    """
    Follow/Unfollow a user
    """
    user_to_follow = get_object_or_404(User, id=user_id)
    
    if user_to_follow == request.user:
        return JsonResponse({
            'success': False,
            'error': 'You cannot follow yourself'
        }, status=400)
    
    follow = Follow.objects.filter(follower=request.user, following=user_to_follow).first()
    
    if follow:
        follow.delete()
        following = False
    else:
        Follow.objects.create(follower=request.user, following=user_to_follow)
        following = True
    
    followers_count = Follow.objects.filter(following=user_to_follow).count()
    
    return JsonResponse({
        'success': True,
        'following': following,
        'followers_count': followers_count
    })


@login_required
def public_profile_view(request, username):
    """
    View public profile of any user
    """
    profile_user = get_object_or_404(User, username=username)
    
    # Get user's posts
    posts = Post.objects.filter(author=profile_user).select_related(
        'author', 'author__profile'
    ).prefetch_related('likes', 'comments', 'images')
    
    # Pagination
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get stats
    total_posts = posts.count()
    followers_count = Follow.objects.filter(following=profile_user).count()
    following_count = Follow.objects.filter(follower=profile_user).count()
    
    # Check if current user follows this user
    is_following = Follow.objects.filter(
        follower=request.user, 
        following=profile_user
    ).exists() if request.user.is_authenticated else False
    
    # Get post IDs that current user has liked
    liked_post_ids = []
    bookmarked_post_ids = []
    if request.user.is_authenticated:
        liked_post_ids = Like.objects.filter(user=request.user).values_list('post_id', flat=True)
        bookmarked_post_ids = Bookmark.objects.filter(user=request.user).values_list('post_id', flat=True)
    
    context = {
        'profile_user': profile_user,
        'posts': page_obj,
        'total_posts': total_posts,
        'followers_count': followers_count,
        'following_count': following_count,
        'is_following': is_following,
        'is_own_profile': request.user == profile_user,
        'liked_post_ids': list(liked_post_ids),
        'bookmarked_post_ids': list(bookmarked_post_ids),
    }
    
    return render(request, 'feed/public_profile.html', context)


@login_required
def post_detail_view(request, post_id):
    """
    View detailed post page
    """
    post = get_object_or_404(
        Post.objects.select_related('author', 'author__profile').prefetch_related(
            'likes', 'comments', 'comments__author', 'images'
        ),
        id=post_id
    )
    
    # Check if user liked/bookmarked
    user_liked = Like.objects.filter(user=request.user, post=post).exists()
    user_bookmarked = Bookmark.objects.filter(user=request.user, post=post).exists()
    
    # Get all comments
    comments = post.comments.select_related('author', 'author__profile').all()
    
    context = {
        'post': post,
        'user_liked': user_liked,
        'user_bookmarked': user_bookmarked,
        'comments': comments,
        'is_owner': request.user == post.author,
    }
    
    return render(request, 'feed/post_detail.html', context)


@login_required
def edit_post_view(request, post_id):
    """
    Edit a post
    """
    post = get_object_or_404(Post, id=post_id, author=request.user)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        category = request.POST.get('category')
        is_anonymous = request.POST.get('is_anonymous') == 'on'
        
        if content:
            post.content = content
            post.category = category
            post.is_anonymous = is_anonymous
            post.save()
            
            messages.success(request, 'Post updated successfully! ✏️')
            return redirect('post_detail', post_id=post.id)
    
    context = {
        'post': post,
        'categories': Post.CATEGORY_CHOICES,
    }
    
    return render(request, 'feed/edit_post.html', context)


@login_required
@require_POST
def delete_post_view(request, post_id):
    """
    Delete a post
    """
    post = get_object_or_404(Post, id=post_id, author=request.user)
    post.delete()
    
    messages.success(request, 'Post deleted successfully! 🗑️')
    return redirect('feed')

from django.contrib.auth.models import User
from django.db.models import Count, Q

@login_required
def search(request):
    """
    Search posts and users with tabs: Top, Latest, Users, Media
    """
    query = request.GET.get('q', '').strip()
    tab = request.GET.get('tab', 'top')
    
    posts = Post.objects.none()
    users = User.objects.none()
    following_users = []
    
    if query:
        if tab == 'users':
            # Search users by username, first_name, last_name, or bio
            users = User.objects.filter(
                Q(username__icontains=query) | 
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(profile__bio__icontains=query)
            ).select_related('profile').distinct()
            
            # Paginate users
            paginator = Paginator(users, 20)
            page_number = request.GET.get('page')
            users = paginator.get_page(page_number)
            
            # Get users that current user is following (adjust based on your Follow model)
            # following_users = request.user.profile.following.all()
            
        else:
            # Base query for posts
            posts = Post.objects.filter(
                content__icontains=query
            ).select_related('author', 'author__profile').prefetch_related('likes', 'comments')
            
            if tab == 'latest':
                posts = posts.order_by('-created_at')
            elif tab == 'media':
                posts = posts.exclude(image='').exclude(image__isnull=True).order_by('-created_at')
            else:  # 'top'
                posts = posts.annotate(
                    engagement=Count('likes') + Count('comments')
                ).order_by('-engagement', '-created_at')
            
            paginator = Paginator(posts, 10)
            page_number = request.GET.get('page')
            posts = paginator.get_page(page_number)
    
    liked_post_ids = Like.objects.filter(user=request.user).values_list('post_id', flat=True)
    
    context = {
        'posts': posts,
        'users': users,
        'liked_post_ids': list(liked_post_ids),
        'search_query': query,
        'current_tab': tab,
        'following_users': following_users,
    }
    
    return render(request, 'feed/search_results.html', context)




from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.dateparse import parse_datetime
from django.contrib.auth.decorators import login_required

@login_required
def check_new_posts(request):
    """Check if new posts exist since the given timestamp"""
    since = request.GET.get('since')
    category = request.GET.get('category', 'all')
    
    if not since:
        return JsonResponse({'new_count': 0})
    
    try:
        since_dt = parse_datetime(since)
        queryset = Post.objects.filter(created_at__gt=since_dt)
        
        # Exclude user's own posts from notification
        queryset = queryset.exclude(author=request.user)
        
        # Filter by category if not 'all'
        if category and category != 'all':
            queryset = queryset.filter(category=category)
        
        return JsonResponse({'new_count': queryset.count()})
    
    except Exception as e:
        return JsonResponse({'new_count': 0, 'error': str(e)})


@login_required
def load_new_posts(request):
    """Load new posts since timestamp and return rendered HTML"""
    since = request.GET.get('since')
    category = request.GET.get('category', 'all')
    
    if not since:
        return JsonResponse({'html': '', 'count': 0})
    
    try:
        since_dt = parse_datetime(since)
        queryset = Post.objects.filter(created_at__gt=since_dt)
        
        # Filter by category if not 'all'
        if category and category != 'all':
            queryset = queryset.filter(category=category)
        
        posts = queryset.select_related('author', 'author__profile').prefetch_related('likes', 'comments').order_by('-created_at')
        
        # Get liked/bookmarked status for current user
        liked_post_ids = list(Like.objects.filter(
            user=request.user, 
            post__in=posts
        ).values_list('post_id', flat=True))
        
        bookmarked_post_ids = list(Bookmark.objects.filter(
            user=request.user, 
            post__in=posts
        ).values_list('post_id', flat=True))
        
        # Render posts to HTML using a partial template
        html = render_to_string('feed/partials/post_list.html', {
            'posts': posts,
            'liked_post_ids': liked_post_ids,
            'bookmarked_post_ids': bookmarked_post_ids,
        }, request=request)
        
        # Get the latest post timestamp
        latest_timestamp = None
        if posts.exists():
            latest_timestamp = posts.first().created_at.isoformat()
        
        return JsonResponse({
            'html': html,
            'count': posts.count(),
            'latest_timestamp': latest_timestamp
        })
    
    except Exception as e:
        return JsonResponse({'html': '', 'count': 0, 'error': str(e)})


    
@login_required
def load_more_posts(request):
    """Load more posts for infinite scroll"""
    page = request.GET.get('page', 1)
    category = request.GET.get('category', 'all')
    search_query = request.GET.get('q', '').strip()
    
    try:
        # Get posts based on filters
        if category == 'all' or not category:
            posts = Post.objects.all()
        else:
            posts = Post.objects.filter(category=category)
        
        # Apply search filter
        if search_query:
            posts = posts.filter(content__icontains=search_query)
        
        posts = posts.select_related('author', 'author__profile').prefetch_related('likes', 'comments')
        
        # Paginate
        paginator = Paginator(posts, 10)
        page_obj = paginator.get_page(page)
        
        # Get liked/bookmarked status
        post_ids = [p.id for p in page_obj]
        liked_post_ids = list(Like.objects.filter(
            user=request.user,
            post_id__in=post_ids
        ).values_list('post_id', flat=True))
        
        bookmarked_post_ids = list(Bookmark.objects.filter(
            user=request.user,
            post_id__in=post_ids
        ).values_list('post_id', flat=True))
        
        # Render HTML
        html = render_to_string('feed/partials/post_list_infinite.html', {
            'posts': page_obj,
            'liked_post_ids': liked_post_ids,
            'bookmarked_post_ids': bookmarked_post_ids,
        }, request=request)
        
        return JsonResponse({
            'html': html,
            'has_next': page_obj.has_next(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
            'total_pages': paginator.num_pages,
        })
        
    except Exception as e:
        return JsonResponse({'html': '', 'has_next': False, 'error': str(e)})
    

from django.db.models import Q, Max, Count, OuterRef, Subquery
from .models import Conversation, DirectMessage

@login_required
def messages_inbox(request):
    """List all conversations for current user"""
    # Get conversations with latest message info
    conversations = Conversation.objects.filter(
        participants=request.user
    ).annotate(
        last_message_time=Max('messages__created_at'),
        unread_count=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
    ).order_by('-last_message_time')
    
    # Prefetch for efficiency
    conversations = conversations.prefetch_related('participants', 'participants__profile')
    
    # Attach other participant and last message to each conversation
    for conv in conversations:
        conv.other_user = conv.get_other_participant(request.user)
        # Get the actual last message (most recent)
        conv.last_message = conv.messages.order_by('-created_at').first()
    
    context = {
        'conversations': conversations,
    }
    return render(request, 'feed/messages/inbox.html', context)


@login_required
def conversation_view(request, username):
    """View/send messages in a conversation"""
    other_user = get_object_or_404(User, username=username)
    
    if other_user == request.user:
        messages.error(request, "You cannot message yourself")
        return redirect('messages_inbox')
    
    # Get or create conversation
    conversation = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=other_user
    ).first()
    
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other_user)
    
    # Mark messages as read
    conversation.messages.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True)
    
    # Get messages
    messages_list = conversation.messages.select_related(
        'sender', 'sender__profile', 'post', 'post__author'
    ).order_by('created_at')
    
    context = {
        'conversation': conversation,
        'other_user': other_user,
        'messages': messages_list,
    }
    return render(request, 'feed/messages/conversation.html', context)


@login_required
@require_POST
def send_message(request, username):
    """Send a message to a user"""
    recipient = get_object_or_404(User, username=username)
    
    if recipient == request.user:
        return JsonResponse({'success': False, 'error': 'Cannot message yourself'}, status=400)
    
    # Get or create conversation
    conversation = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=recipient
    ).first()
    
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, recipient)
    
    content = request.POST.get('content', '').strip()
    image = request.FILES.get('image')
    video = request.FILES.get('video')
    voice_note = request.FILES.get('voice_note')
    voice_duration = request.POST.get('voice_duration')
    post_id = request.POST.get('post_id')
    
    # Validate: must have at least one type of content
    if not any([content, image, video, voice_note, post_id]):
        return JsonResponse({'success': False, 'error': 'Message cannot be empty'}, status=400)
    
    # Create message
    message = DirectMessage(
        conversation=conversation,
        sender=request.user,
        recipient=recipient,
        content=content,
    )
    
    if image:
        message.image = image
    if video:
        message.video = video
    if voice_note:
        message.voice_note = voice_note
        if voice_duration:
            try:
                message.voice_duration = int(float(voice_duration))
            except ValueError:
                message.voice_duration = 0
    if post_id:
        try:
            message.post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            pass
    
    message.save()
    
    # Build response data
    response_data = {
        'success': True,
        'message': {
            'id': message.id,
            'content': message.content,
            'message_type': message.message_type,
            'created_at': message.created_at.strftime('%I:%M %p'),
            'timestamp': message.created_at.isoformat(),
            'is_own': True,
            'sender': {
                'username': request.user.username,
                'profile_picture': request.user.profile.profile_picture.url if request.user.profile.profile_picture else None
            }
        }
    }
    
    if message.image:
        response_data['message']['image_url'] = message.image.url
    if message.video:
        response_data['message']['video_url'] = message.video.url
    if message.voice_note:
        response_data['message']['voice_url'] = message.voice_note.url
        response_data['message']['voice_duration'] = message.voice_duration
    if message.post:
        response_data['message']['post'] = {
            'id': message.post.id,
            'content': message.post.content[:100],
            'author': message.post.get_author_display(),
        }
    
    return JsonResponse(response_data)


@login_required
def get_new_messages(request, username):
    """Poll for new messages in a conversation (for real-time updates)"""
    other_user = get_object_or_404(User, username=username)
    since = request.GET.get('since')
    
    if not since:
        return JsonResponse({'messages': []})
    
    try:
        since_dt = parse_datetime(since)
        
        # Get conversation
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).first()
        
        if not conversation:
            return JsonResponse({'messages': []})
        
        # Get new messages
        new_messages = conversation.messages.filter(
            created_at__gt=since_dt
        ).exclude(
            sender=request.user
        ).select_related('sender', 'sender__profile', 'post', 'post__author').order_by('created_at')
        
        # Mark as read
        new_messages.filter(is_read=False).update(is_read=True)
        
        messages_data = []
        for msg in new_messages:
            message_dict = {
                'id': msg.id,
                'content': msg.content,
                'message_type': msg.message_type,
                'created_at': msg.created_at.strftime('%I:%M %p'),
                'timestamp': msg.created_at.isoformat(),
                'is_own': False,
                'sender': {
                    'username': msg.sender.username,
                    'profile_picture': msg.sender.profile.profile_picture.url if msg.sender.profile.profile_picture else None
                }
            }
            
            if msg.image:
                message_dict['image_url'] = msg.image.url
            if msg.video:
                message_dict['video_url'] = msg.video.url
            if msg.voice_note:
                message_dict['voice_url'] = msg.voice_note.url
                message_dict['voice_duration'] = msg.voice_duration
            if msg.post:
                message_dict['post'] = {
                    'id': msg.post.id,
                    'content': msg.post.content[:100],
                    'author': msg.post.get_author_display(),
                }
            
            messages_data.append(message_dict)
        
        return JsonResponse({'messages': messages_data})
        
    except Exception as e:
        return JsonResponse({'messages': [], 'error': str(e)})


@login_required
def start_conversation(request, username):
    """Start or go to conversation with a user"""
    other_user = get_object_or_404(User, username=username)
    return redirect('conversation', username=other_user.username)


@login_required
def share_post_dm(request, post_id):
    """Share a post via DM"""
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'GET':
        # Return list of recent conversations/users
        recent_conversations = Conversation.objects.filter(
            participants=request.user
        ).prefetch_related('participants', 'participants__profile').order_by('-updated_at')[:20]
        
        users = []
        for conv in recent_conversations:
            other = conv.get_other_participant(request.user)
            if other:
                users.append({
                    'username': other.username,
                    'name': other.get_full_name() or other.username,
                    'profile_picture': other.profile.profile_picture.url if other.profile.profile_picture else None,
                })
        
        return JsonResponse({'success': True, 'users': users})
    
    elif request.method == 'POST':
        username = request.POST.get('username')
        recipient = get_object_or_404(User, username=username)
        
        if recipient == request.user:
            return JsonResponse({'success': False, 'error': 'Cannot share with yourself'}, status=400)
        
        # Get or create conversation
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=recipient
        ).first()
        
        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, recipient)
        
        # Create message with post
        message = DirectMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            recipient=recipient,
            post=post,
            content=request.POST.get('message', '')
        )
        
        # Track share
        PostShare.objects.create(
            user=request.user,
            post=post,
            shared_via='DM'
        )
        
        # Update post share count
        post.shares_count = post.share_records.count()
        post.save(update_fields=['shares_count'])
        
        return JsonResponse({'success': True, 'message': 'Post shared successfully!'})




@login_required
def get_unread_count(request):
    """Get total unread message count for navbar badge"""
    count = DirectMessage.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    return JsonResponse({'unread_count': count})





@login_required
def mark_conversation_read(request, username):
    """Mark all messages in a conversation as read"""
    other_user = get_object_or_404(User, username=username)
    
    conversation = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=other_user
    ).first()
    
    if conversation:
        conversation.messages.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
    
    return JsonResponse({'success': True})


@login_required
def delete_message(request, message_id):
    """Delete a message (only sender can delete)"""
    message = get_object_or_404(DirectMessage, id=message_id)
    
    if message.sender != request.user:
        return JsonResponse({'success': False, 'error': 'You can only delete your own messages'}, status=403)
    
    message.delete()
    return JsonResponse({'success': True})


@login_required
def search_users_dm(request):
    """Search users to start conversation with"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id).select_related('profile')[:15]
    
    results = []
    for user in users:
        results.append({
            'username': user.username,
            'name': user.get_full_name() or user.username,
            'profile_picture': user.profile.profile_picture.url if user.profile.profile_picture else None,
        })
    
    return JsonResponse({'users': results})

@login_required
def get_share_link_view(request, post_id):
    """Generate shareable link for post"""
    post = get_object_or_404(Post, id=post_id)
    
    # Track share
    PostShare.objects.create(
        user=request.user,
        post=post,
        shared_via='LINK'
    )
    
    # Update share count
    post.shares_count = post.share_records.count()
    post.save(update_fields=['shares_count'])
    
    share_url = request.build_absolute_uri(f'/post/{post_id}/')
    
    return JsonResponse({
        'success': True,
        'url': share_url
    })