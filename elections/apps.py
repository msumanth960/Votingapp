from django.apps import AppConfig


class ElectionsConfig(AppConfig):
    """Configuration for the Elections app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'elections'
    verbose_name = 'Local Elections Management'

