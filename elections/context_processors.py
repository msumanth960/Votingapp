"""
Context processors for the Elections app.

These make certain data available to all templates automatically.
"""

from django.db import OperationalError, ProgrammingError


class DefaultSiteSettings:
    """Default settings used when database table doesn't exist yet."""
    site_name = "Local Elections"
    site_tagline = "Voting System"
    footer_text = "Gram Panchayat Elections Management"
    contact_email = ""
    contact_phone = ""
    about_text = ""


def site_settings(request):
    """
    Add site settings to template context.
    
    Usage in templates:
        {{ site_settings.site_name }}
        {{ site_settings.site_tagline }}
        {{ site_settings.footer_text }}
    
    Handles cases where the database table doesn't exist yet.
    """
    try:
        from .models import SiteSettings
        settings = SiteSettings.get_settings()
    except (OperationalError, ProgrammingError):
        # Table doesn't exist yet (before migrations)
        settings = DefaultSiteSettings()
    
    return {
        'site_settings': settings
    }

