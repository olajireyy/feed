from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def smart_time(date):
    """
    Format time smartly:
    - < 1 day: "Xh" or "Xm"
    - 1-3 days: "1d", "2d", "3d"
    - > 3 days: "Jan 15, 2024 at 3:45 PM"
    """
    if not date:
        return ""
    
    now = timezone.now()
    diff = now - date
    
    # Less than 1 minute
    if diff.total_seconds() < 60:
        return "now"
    
    # Less than 1 hour
    if diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes}m"
    
    # Less than 24 hours
    if diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}h"
    
    # 1-3 days
    if diff.days <= 3:
        return f"{diff.days}d"
    
    # More than 3 days
    return date.strftime("%b %d, %Y at %I:%M %p")


@register.filter
def full_time(date):
    """
    Full time format for post details
    """
    if not date:
        return ""
    return date.strftime("%B %d, %Y at %I:%M %p")