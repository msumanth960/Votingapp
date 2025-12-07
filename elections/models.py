"""
Models for the Local Elections Voting System.

This module defines the data models for:
- Site Settings (dynamic configuration)
- Location hierarchy: District -> Mandal -> Village -> Ward
- Election and Candidates
- Voters and Votes
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone
import re


# ==============================================================================
# Site Settings Model (Singleton)
# ==============================================================================

class SiteSettings(models.Model):
    """
    Singleton model for site-wide settings.
    Only one instance should exist - enforced by the save method.
    """
    site_name = models.CharField(
        max_length=200,
        default="Local Elections",
        help_text="Main site name displayed in header"
    )
    site_tagline = models.CharField(
        max_length=300,
        default="Voting System",
        help_text="Tagline displayed below site name"
    )
    footer_text = models.CharField(
        max_length=500,
        default="Gram Panchayat Elections Management",
        blank=True,
        help_text="Text displayed in footer"
    )
    contact_email = models.EmailField(
        blank=True,
        help_text="Contact email (optional)"
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact phone number (optional)"
    )
    about_text = models.TextField(
        blank=True,
        help_text="About section text for landing page"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return f"Site Settings - {self.site_name}"

    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton pattern)."""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of the singleton instance."""
        pass

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


# ==============================================================================
# Location Hierarchy Models
# ==============================================================================

class District(models.Model):
    """
    Represents a District in the administrative hierarchy.
    Top level of the location hierarchy.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the district"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'District'
        verbose_name_plural = 'Districts'

    def __str__(self):
        return self.name


class Mandal(models.Model):
    """
    Represents a Mandal (sub-district/taluk) within a District.
    Second level of the location hierarchy.
    """
    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name='mandals',
        help_text="District this mandal belongs to"
    )
    name = models.CharField(
        max_length=100,
        help_text="Name of the mandal"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['district__name', 'name']
        unique_together = ['district', 'name']
        verbose_name = 'Mandal'
        verbose_name_plural = 'Mandals'

    def __str__(self):
        return f"{self.name} ({self.district.name})"


class Village(models.Model):
    """
    Represents a Village (Gram Panchayat) within a Mandal.
    Third level of the location hierarchy.
    This is where Sarpanch elections take place.
    """
    mandal = models.ForeignKey(
        Mandal,
        on_delete=models.CASCADE,
        related_name='villages',
        help_text="Mandal this village belongs to"
    )
    name = models.CharField(
        max_length=100,
        help_text="Name of the village/gram panchayat"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['mandal__district__name', 'mandal__name', 'name']
        unique_together = ['mandal', 'name']
        verbose_name = 'Village'
        verbose_name_plural = 'Villages'

    def __str__(self):
        return f"{self.name} ({self.mandal.name}, {self.mandal.district.name})"

    @property
    def full_location(self):
        """Returns the full location path."""
        return f"{self.name}, {self.mandal.name}, {self.mandal.district.name}"


class Ward(models.Model):
    """
    Represents a Ward within a Village.
    Fourth level of the location hierarchy.
    This is where Ward Member elections take place.
    """
    village = models.ForeignKey(
        Village,
        on_delete=models.CASCADE,
        related_name='wards',
        help_text="Village this ward belongs to"
    )
    number = models.PositiveIntegerField(
        help_text="Ward number within the village"
    )
    name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional descriptive name for the ward"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['village__name', 'number']
        unique_together = ['village', 'number']
        verbose_name = 'Ward'
        verbose_name_plural = 'Wards'

    def __str__(self):
        village_info = f"{self.village.name}, {self.village.mandal.name}, {self.village.mandal.district.name}"
        if self.name:
            return f"Ward {self.number} - {self.name} ({village_info})"
        return f"Ward {self.number} ({village_info})"


# ==============================================================================
# Election and Candidate Models
# ==============================================================================

class Election(models.Model):
    """
    Represents an election event (e.g., "2025 Local Body Elections").
    All votes are scoped to a specific Election.
    """
    name = models.CharField(
        max_length=200,
        help_text="Name of the election (e.g., '2025 Gram Panchayat Elections')"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the election"
    )
    start_time = models.DateTimeField(
        help_text="When voting starts"
    )
    end_time = models.DateTimeField(
        help_text="When voting ends"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this election is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']
        verbose_name = 'Election'
        verbose_name_plural = 'Elections'

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({status})"

    def clean(self):
        """Validate that end_time is after start_time."""
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError({
                    'end_time': 'End time must be after start time.'
                })

    @property
    def is_ongoing(self):
        """Check if the election is currently ongoing."""
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    @property
    def status(self):
        """Get the current status of the election."""
        now = timezone.now()
        if not self.is_active:
            return "Inactive"
        if now < self.start_time:
            return "Upcoming"
        if now > self.end_time:
            return "Ended"
        return "Ongoing"


class Candidate(models.Model):
    """
    Represents a candidate for either Sarpanch or Ward Member position.
    
    - Sarpanch candidates: ward is NULL (village-level position)
    - Ward Member candidates: ward is required
    """
    POSITION_SARPANCH = 'SARPANCH'
    POSITION_WARD_MEMBER = 'WARD_MEMBER'
    POSITION_CHOICES = [
        (POSITION_SARPANCH, 'Sarpanch'),
        (POSITION_WARD_MEMBER, 'Ward Member'),
    ]

    election = models.ForeignKey(
        Election,
        on_delete=models.CASCADE,
        related_name='candidates',
        help_text="Election this candidate is participating in"
    )
    village = models.ForeignKey(
        Village,
        on_delete=models.CASCADE,
        related_name='candidates',
        help_text="Village for this candidacy"
    )
    ward = models.ForeignKey(
        Ward,
        on_delete=models.CASCADE,
        related_name='candidates',
        null=True,
        blank=True,
        help_text="Ward for Ward Member candidates (NULL for Sarpanch)"
    )
    full_name = models.CharField(
        max_length=200,
        help_text="Full name of the candidate"
    )
    position_type = models.CharField(
        max_length=20,
        choices=POSITION_CHOICES,
        help_text="Type of position: Sarpanch or Ward Member"
    )
    party_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Political party or affiliation (optional)"
    )
    symbol = models.CharField(
        max_length=100,
        blank=True,
        help_text="Election symbol (optional)"
    )
    photo = models.ImageField(
        upload_to='candidates/',
        blank=True,
        null=True,
        help_text="Candidate photo (optional)"
    )
    bio = models.TextField(
        blank=True,
        help_text="Brief biography of the candidate (optional)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['election', 'village', 'position_type', 'full_name']
        verbose_name = 'Candidate'
        verbose_name_plural = 'Candidates'

    def __str__(self):
        position = self.get_position_type_display()
        if self.ward:
            return f"{self.full_name} ({position}) - {self.village.name}, Ward {self.ward.number}"
        return f"{self.full_name} ({position}) - {self.village.name}"

    def clean(self):
        """
        Validate candidate data:
        - Sarpanch candidates must NOT have a ward
        - Ward Member candidates MUST have a ward
        - Ward must belong to the same village
        """
        errors = {}

        # Validate position_type and ward relationship
        if self.position_type == self.POSITION_SARPANCH:
            if self.ward is not None:
                errors['ward'] = 'Sarpanch candidates should not be assigned to a specific ward.'
        
        elif self.position_type == self.POSITION_WARD_MEMBER:
            if self.ward is None:
                errors['ward'] = 'Ward Member candidates must be assigned to a ward.'
            elif self.village and self.ward.village_id != self.village_id:
                errors['ward'] = 'Ward must belong to the same village as the candidate.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Ensure validation is run before saving."""
        self.full_clean()
        super().save(*args, **kwargs)


# ==============================================================================
# Voter and Vote Models
# ==============================================================================

# Mobile number validator for Indian mobile numbers
mobile_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message='Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.'
)


class Voter(models.Model):
    """
    Represents a voter identified by their mobile number.
    Mobile numbers must be unique to ensure one-person-one-vote.
    """
    mobile_number = models.CharField(
        max_length=10,
        unique=True,
        validators=[mobile_validator],
        help_text="10-digit mobile number (used for voter identification)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Voter'
        verbose_name_plural = 'Voters'

    def __str__(self):
        # Mask the mobile number for privacy (show only last 4 digits)
        return f"Voter ******{self.mobile_number[-4:]}"

    @property
    def masked_mobile(self):
        """Return masked mobile number for display."""
        return f"******{self.mobile_number[-4:]}"


class Vote(models.Model):
    """
    Represents a vote cast by a voter in an election for a specific village.
    
    Constraints:
    - One vote per voter per election per village
    - Sarpanch candidate must be valid for the village
    - Ward Member candidate must be valid for the ward
    """
    election = models.ForeignKey(
        Election,
        on_delete=models.CASCADE,
        related_name='votes',
        help_text="Election for this vote"
    )
    village = models.ForeignKey(
        Village,
        on_delete=models.CASCADE,
        related_name='votes',
        help_text="Village where the vote was cast"
    )
    ward = models.ForeignKey(
        Ward,
        on_delete=models.SET_NULL,
        related_name='votes',
        null=True,
        blank=True,
        help_text="Ward for the Ward Member vote"
    )
    voter = models.ForeignKey(
        Voter,
        on_delete=models.CASCADE,
        related_name='votes',
        help_text="Voter who cast this vote"
    )
    sarpanch_candidate = models.ForeignKey(
        Candidate,
        on_delete=models.PROTECT,
        related_name='sarpanch_votes',
        null=True,
        blank=True,
        help_text="Sarpanch candidate voted for"
    )
    ward_member_candidate = models.ForeignKey(
        Candidate,
        on_delete=models.PROTECT,
        related_name='ward_member_votes',
        null=True,
        blank=True,
        help_text="Ward Member candidate voted for"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the voter (for audit)"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser user agent (for audit)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # Ensure one vote per voter per election per village
        unique_together = ['election', 'voter', 'village']
        verbose_name = 'Vote'
        verbose_name_plural = 'Votes'

    def __str__(self):
        return f"Vote by {self.voter} in {self.election.name} - {self.village.name}"

    def clean(self):
        """
        Validate vote data:
        - Sarpanch candidate must be valid for the election and village
        - Ward Member candidate must be valid for the election, village, and ward
        """
        errors = {}

        # Validate sarpanch candidate
        if self.sarpanch_candidate:
            if self.sarpanch_candidate.position_type != Candidate.POSITION_SARPANCH:
                errors['sarpanch_candidate'] = 'Selected candidate is not a Sarpanch candidate.'
            elif self.sarpanch_candidate.election_id != self.election_id:
                errors['sarpanch_candidate'] = 'Sarpanch candidate is not from this election.'
            elif self.sarpanch_candidate.village_id != self.village_id:
                errors['sarpanch_candidate'] = 'Sarpanch candidate is not from this village.'

        # Validate ward member candidate
        if self.ward_member_candidate:
            if self.ward_member_candidate.position_type != Candidate.POSITION_WARD_MEMBER:
                errors['ward_member_candidate'] = 'Selected candidate is not a Ward Member candidate.'
            elif self.ward_member_candidate.election_id != self.election_id:
                errors['ward_member_candidate'] = 'Ward Member candidate is not from this election.'
            elif self.ward and self.ward_member_candidate.ward_id != self.ward_id:
                errors['ward_member_candidate'] = 'Ward Member candidate is not from the selected ward.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Ensure validation is run before saving."""
        self.full_clean()
        super().save(*args, **kwargs)

