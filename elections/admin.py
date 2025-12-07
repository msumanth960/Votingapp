"""
Django Admin configuration for the Elections app.

This module configures the admin interface for managing:
- Location hierarchy (Districts, Mandals, Villages, Wards)
- Elections and Candidates
- Voters and Votes (read-only for votes)
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import District, Mandal, Village, Ward, Election, Candidate, Voter, Vote, SiteSettings


# ==============================================================================
# Site Settings Admin (Singleton)
# ==============================================================================

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin configuration for Site Settings (singleton)."""
    list_display = ['site_name', 'site_tagline', 'updated_at']
    fieldsets = (
        ('Site Identity', {
            'fields': ('site_name', 'site_tagline', 'footer_text')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone'),
            'classes': ('collapse',)
        }),
        ('Content', {
            'fields': ('about_text',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """Only allow one instance - disable add if it exists."""
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of the singleton instance."""
        return False


# ==============================================================================
# Location Hierarchy Admin
# ==============================================================================

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    """Admin configuration for District model."""
    list_display = ['name', 'mandal_count', 'created_at']
    search_fields = ['name']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']

    def mandal_count(self, obj):
        """Display the number of mandals in this district."""
        return obj.mandals.count()
    mandal_count.short_description = 'Mandals'


@admin.register(Mandal)
class MandalAdmin(admin.ModelAdmin):
    """Admin configuration for Mandal model."""
    list_display = ['name', 'district', 'village_count', 'created_at']
    list_filter = ['district']
    search_fields = ['name', 'district__name']
    ordering = ['district__name', 'name']
    autocomplete_fields = ['district']
    readonly_fields = ['created_at', 'updated_at']

    def village_count(self, obj):
        """Display the number of villages in this mandal."""
        return obj.villages.count()
    village_count.short_description = 'Villages'


@admin.register(Village)
class VillageAdmin(admin.ModelAdmin):
    """Admin configuration for Village model."""
    list_display = ['name', 'mandal', 'get_district', 'ward_count', 'created_at']
    list_filter = ['mandal__district', 'mandal']
    search_fields = ['name', 'mandal__name', 'mandal__district__name']
    ordering = ['mandal__district__name', 'mandal__name', 'name']
    autocomplete_fields = ['mandal']
    readonly_fields = ['created_at', 'updated_at']

    def get_district(self, obj):
        """Display the district for this village."""
        return obj.mandal.district.name
    get_district.short_description = 'District'
    get_district.admin_order_field = 'mandal__district__name'

    def ward_count(self, obj):
        """Display the number of wards in this village."""
        return obj.wards.count()
    ward_count.short_description = 'Wards'


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    """Admin configuration for Ward model."""
    list_display = ['__str__', 'village', 'number', 'name', 'created_at']
    list_filter = ['village__mandal__district', 'village__mandal', 'village']
    search_fields = ['name', 'village__name', 'village__mandal__name']
    ordering = ['village__mandal__district__name', 'village__mandal__name', 'village__name', 'number']
    autocomplete_fields = ['village']
    readonly_fields = ['created_at', 'updated_at']


# ==============================================================================
# Election and Candidate Admin
# ==============================================================================

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    """Admin configuration for Election model."""
    list_display = ['name', 'status_badge', 'start_time', 'end_time', 'is_active', 'vote_count']
    list_filter = ['is_active', 'start_time']
    search_fields = ['name', 'description']
    ordering = ['-start_time']
    readonly_fields = ['created_at', 'updated_at', 'status_badge']
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Schedule', {
            'fields': ('start_time', 'end_time', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display a colored badge for the election status."""
        status = obj.status
        colors = {
            'Ongoing': 'green',
            'Upcoming': 'blue',
            'Ended': 'gray',
            'Inactive': 'red'
        }
        color = colors.get(status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, status
        )
    status_badge.short_description = 'Status'

    def vote_count(self, obj):
        """Display the total number of votes in this election."""
        return obj.votes.count()
    vote_count.short_description = 'Total Votes'


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    """Admin configuration for Candidate model."""
    list_display = ['full_name', 'position_type', 'village', 'ward', 'election', 'party_name', 'vote_count']
    list_filter = ['election', 'position_type', 'village__mandal__district', 'village__mandal', 'village']
    search_fields = ['full_name', 'party_name', 'village__name']
    ordering = ['election', 'village', 'position_type', 'full_name']
    autocomplete_fields = ['election', 'village', 'ward']
    readonly_fields = ['created_at', 'updated_at', 'vote_count']
    fieldsets = (
        (None, {
            'fields': ('full_name', 'position_type')
        }),
        ('Election & Location', {
            'fields': ('election', 'village', 'ward')
        }),
        ('Promises & Welfare Activities', {
            'fields': ('promises_csv',),
            'description': 'Enter welfare activities/promises separated by commas'
        }),
        ('Additional Info', {
            'fields': ('party_name', 'symbol', 'photo', 'bio'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def vote_count(self, obj):
        """Display the number of votes received by this candidate."""
        if obj.position_type == Candidate.POSITION_SARPANCH:
            return obj.sarpanch_votes.count()
        return obj.ward_member_votes.count()
    vote_count.short_description = 'Votes'

    def get_form(self, request, obj=None, **kwargs):
        """Customize form to filter ward choices based on village."""
        form = super().get_form(request, obj, **kwargs)
        return form


# ==============================================================================
# Voter and Vote Admin
# ==============================================================================

@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    """Admin configuration for Voter model."""
    list_display = ['id', 'name', 'masked_mobile_display', 'created_at', 'vote_count']
    search_fields = ['name', 'mobile_number']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    list_editable = ['name']

    def masked_mobile_display(self, obj):
        """Display masked mobile number for privacy."""
        return obj.masked_mobile
    masked_mobile_display.short_description = 'Mobile Number'

    def vote_count(self, obj):
        """Display the number of votes cast by this voter."""
        return obj.votes.count()
    vote_count.short_description = 'Votes Cast'


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    """
    Admin configuration for Vote model.
    Votes are read-only to prevent tampering.
    """
    list_display = [
        'id', 'election', 'village', 'ward', 'get_voter_info',
        'sarpanch_candidate', 'ward_member_candidate', 'family_vote_count', 'created_at'
    ]
    list_filter = ['election', 'village__mandal__district', 'village__mandal', 'village', 'ward', 'family_vote_count', 'created_at']
    search_fields = ['voter__name', 'voter__mobile_number', 'ip_address']
    ordering = ['-created_at']
    readonly_fields = [
        'election', 'village', 'ward', 'voter', 'sarpanch_candidate',
        'ward_member_candidate', 'family_vote_count', 'ip_address', 'user_agent', 'created_at'
    ]
    date_hierarchy = 'created_at'

    def get_voter_info(self, obj):
        """Display voter name and masked mobile number."""
        if obj.voter.name:
            return f"{obj.voter.name} ({obj.voter.masked_mobile})"
        return obj.voter.masked_mobile
    get_voter_info.short_description = 'Voter'

    def has_add_permission(self, request):
        """Prevent adding votes through admin."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent editing votes through admin."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow superusers to delete votes if needed (for cleanup)."""
        return request.user.is_superuser

