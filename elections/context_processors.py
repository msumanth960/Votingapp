"""
Context processors for the Elections app.

These make certain data available to all templates automatically.
"""

from django.db import DatabaseError


class DefaultSiteSettings:
    """
    Default settings used when database is unavailable.
    Prevents template rendering failures during migrations or DB issues.
    """
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
    
    Handles database exceptions gracefully to prevent 500 errors.
    """
    try:
        from .models import SiteSettings
        return {'site_settings': SiteSettings.get_settings()}
    except DatabaseError:
        # Catches all DB exceptions: OperationalError, ProgrammingError,
        # IntegrityError, DataError, etc.
        return {'site_settings': DefaultSiteSettings()}
    except Exception:
        # Fallback for any unexpected errors (import issues, etc.)
        return {'site_settings': DefaultSiteSettings()}
