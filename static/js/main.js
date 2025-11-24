function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Create Post via AJAX
document.addEventListener('DOMContentLoaded', function() {
    const postForm = document.getElementById('postForm');
    
    if (postForm) {
        postForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = postForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            
            // Disable submit button and show loading
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Posting...';
            
            // Create FormData from form
            const formData = new FormData(postForm);
            
            try {
                const response = await fetch('/posts/create/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Clear form
                    postForm.reset();
                    
                    // Remove image preview if exists
                    const imagePreview = document.getElementById('imagePreview');
                    if (imagePreview) {
                        imagePreview.innerHTML = '';
                    }
                    
                    // Add new post to feed
                    addPostToFeed(data.post);
                    
                    // Show success message
                    showAlert('Post created successfully! 🎉', 'success');
                    
                    // Scroll to top to see new post
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                } else {
                    // Show error messages
                    let errorMsg = 'Error creating post: ';
                    for (let field in data.errors) {
                        errorMsg += data.errors[field].join(', ') + ' ';
                    }
                    showAlert(errorMsg, 'danger');
                }
            } catch (error) {
                console.error('Error:', error);
                showAlert('An error occurred while creating the post.', 'danger');
            } finally {
                // Re-enable submit button
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        });
    }
    
    // Image preview
    const imageInput = document.getElementById('id_image');
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            const preview = document.getElementById('imagePreview');
            
            if (file && preview) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.innerHTML = `
                        <div class="position-relative d-inline-block">
                            <img src="${e.target.result}" class="img-fluid rounded" style="max-height: 200px;">
                            <button type="button" class="btn btn-sm btn-danger position-absolute top-0 end-0 m-2" onclick="removeImage()">
                                <i class="bi bi-x"></i>
                            </button>
                        </div>
                    `;
                };
                reader.readAsDataURL(file);
            }
        });
    }
});

// Remove image preview
function removeImage() {
    const imageInput = document.getElementById('id_image');
    const preview = document.getElementById('imagePreview');
    
    if (imageInput) imageInput.value = '';
    if (preview) preview.innerHTML = '';
}

// Add post to feed dynamically
function addPostToFeed(post) {
    const postsContainer = document.getElementById('postsContainer');
    if (!postsContainer) return;
    
    const postHTML = createPostHTML(post);
    postsContainer.insertAdjacentHTML('afterbegin', postHTML);
    
    // Add animation
    const newPost = postsContainer.firstElementChild;
    newPost.style.opacity = '0';
    setTimeout(() => {
        newPost.style.transition = 'opacity 0.5s';
        newPost.style.opacity = '1';
    }, 10);
}

// Create post HTML
function createPostHTML(post) {
    const imageHTML = post.image_url 
        ? `<img src="${post.image_url}" class="img-fluid rounded mt-2" alt="Post image">` 
        : '';
    
    const authorBadge = post.is_anonymous 
        ? '<span class="badge bg-secondary ms-2">Anonymous</span>'
        : '';
    
    const departmentLevel = (!post.is_anonymous && post.author.department) 
        ? `<small class="text-muted">• ${post.author.department} • ${post.author.level}</small>`
        : '';
    
    return `
        <div class="card shadow-sm border-0 mb-3 post-card" data-post-id="${post.id}">
            <div class="card-body">
                <div class="d-flex align-items-start mb-3">
                    <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center me-3" 
                         style="width: 48px; height: 48px; min-width: 48px;">
                        <i class="bi bi-person-fill"></i>
                    </div>
                    <div class="flex-grow-1">
                        <h6 class="mb-0">
                            ${post.author.username}${authorBadge}
                        </h6>
                        <small class="text-muted">${post.created_at} ${departmentLevel}</small>
                    </div>
                    <span class="badge bg-light text-dark">${post.category}</span>
                </div>
                
                <p class="card-text">${post.content}</p>
                ${imageHTML}
                
                <hr>
                
                <div class="d-flex justify-content-between align-items-center">
                    <button class="btn btn-sm btn-outline-primary like-btn" data-post-id="${post.id}">
                        <i class="bi bi-heart"></i> <span class="like-count">${post.likes_count}</span>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary comment-btn" data-post-id="${post.id}">
                        <i class="bi bi-chat"></i> <span class="comment-count">${post.comments_count}</span>
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Show alert message
function showAlert(message, type) {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Format time ago
function timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    let interval = Math.floor(seconds / 31536000);
    if (interval >= 1) return interval + " year" + (interval > 1 ? "s" : "") + " ago";
    
    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) return interval + " month" + (interval > 1 ? "s" : "") + " ago";
    
    interval = Math.floor(seconds / 86400);
    if (interval >= 1) return interval + " day" + (interval > 1 ? "s" : "") + " ago";
    
    interval = Math.floor(seconds / 3600);
    if (interval >= 1) return interval + " hour" + (interval > 1 ? "s" : "") + " ago";
    
    interval = Math.floor(seconds / 60);
    if (interval >= 1) return interval + " minute" + (interval > 1 ? "s" : "") + " ago";
    
    return "Just now";
}