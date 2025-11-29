from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import UserProfile, Post


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget for multiple file uploads"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Custom field for multiple file uploads"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class UserRegistrationForm(UserCreationForm):
    """
    Extended registration form with campus-specific fields
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
        
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        self.fields['password1'].help_text = 'Your password must contain at least 8 characters.'
    
    def save(self, commit=True):
        user = super(UserRegistrationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            profile = user.profile
            profile.save()
        
        return user


class UserLoginForm(AuthenticationForm):
    """
    Custom login form with Bootstrap styling
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user profile
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'department', 'level', 'bio']
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Tell us about yourself...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        profile = super(ProfileUpdateForm, self).save(commit=False)
        
        if commit:
            profile.save()
            user = profile.user
            user.email = self.cleaned_data['email']
            user.save()
        
        return profile


class PostForm(forms.ModelForm):
    """
    Form for creating posts - now handles multiple images
    """
    # Override to handle multiple images with custom field
    images = MultipleFileField(
        required=False,
        label='Add images (optional)'
    )
    
    class Meta:
        model = Post
        fields = ['content', 'video', 'category', 'is_anonymous']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': "What's on your mind?",
            }),
            'video': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'content': 'What\'s on your mind?',
            'video': 'Add a video (optional)',
            'category': 'Category (optional)',
            'is_anonymous': 'Post anonymously'
        }
    
    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        # Make all fields optional - validation will check if at least one media exists
        self.fields['content'].required = False
        self.fields['video'].required = False
        self.fields['category'].required = False
        self.fields['images'].required = False
        self.fields['category'].empty_label = "Select category (optional)"
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content', '').strip()
        video = cleaned_data.get('video')
        
        # Check if images were uploaded (these come from request.FILES)
        # We'll validate this in the view since the form doesn't have direct access
        
        # Don't raise validation error here - let the view handle it
        # since we need to check request.FILES for multiple images
        
        return cleaned_data