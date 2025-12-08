"""
Django Forms for the Elections app.

This module defines forms for:
- Location selection (District -> Mandal -> Village)
- Voting (Sarpanch and Ward Member selection with mobile number)
"""

from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import District, Mandal, Village, Ward, Candidate, Voter, Vote, Election


# Mobile number validator
mobile_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message='Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.'
)


class LocationSelectionForm(forms.Form):
    """
    Form for selecting location hierarchy: District -> Mandal -> Village.
    Used in the location selection step before voting.
    """
    district = forms.ModelChoiceField(
        queryset=District.objects.all(),
        empty_label="-- Select District --",
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'id': 'district-select'
        }),
        help_text="Select your district"
    )
    
    mandal = forms.ModelChoiceField(
        queryset=Mandal.objects.none(),
        empty_label="-- Select Mandal --",
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'id': 'mandal-select'
        }),
        help_text="Select your mandal"
    )
    
    village = forms.ModelChoiceField(
        queryset=Village.objects.none(),
        empty_label="-- Select Village --",
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'id': 'village-select'
        }),
        help_text="Select your village (Gram Panchayat)"
    )

    def __init__(self, *args, **kwargs):
        """
        Initialize form with dynamic querysets based on selected values.
        """
        super().__init__(*args, **kwargs)
        
        # If district is provided, filter mandals
        if 'district' in self.data:
            try:
                district_id = int(self.data.get('district'))
                self.fields['mandal'].queryset = Mandal.objects.filter(
                    district_id=district_id
                ).order_by('name')
            except (ValueError, TypeError):
                pass
        
        # If mandal is provided, filter villages
        if 'mandal' in self.data:
            try:
                mandal_id = int(self.data.get('mandal'))
                self.fields['village'].queryset = Village.objects.filter(
                    mandal_id=mandal_id
                ).order_by('name')
            except (ValueError, TypeError):
                pass


class VotingForm(forms.Form):
    """
    Form for casting a vote.
    
    Contains fields for:
    - Sarpanch candidate selection
    - Ward selection
    - Ward Member candidate selection
    - Voter name and mobile number
    - Family vote count
    """
    sarpanch_candidate = forms.ModelChoiceField(
        queryset=Candidate.objects.none(),
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        empty_label=None,
        required=True,
        help_text="Select one Sarpanch candidate"
    )
    
    ward = forms.ModelChoiceField(
        queryset=Ward.objects.none(),
        empty_label="-- Select Your Ward --",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'ward-select'
        }),
        required=True,
        help_text="Select your ward number"
    )
    
    ward_member_candidate = forms.ModelChoiceField(
        queryset=Candidate.objects.none(),
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        empty_label=None,
        required=True,
        help_text="Select one Ward Member candidate"
    )
    
    voter_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your full name'
        }),
        help_text="Your name (optional but recommended)"
    )
    
    mobile_number = forms.CharField(
        max_length=10,
        min_length=10,
        validators=[mobile_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter 10-digit mobile number',
            'pattern': '[6-9][0-9]{9}',
            'inputmode': 'numeric',
            'maxlength': '10'
        }),
        help_text="Your mobile number is used only to ensure one-person-one-vote and will not be publicly exposed."
    )
    
    family_vote_count = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '20'
        }),
        help_text="Number of family members voting together (including yourself)"
    )

    def __init__(self, village=None, election=None, *args, **kwargs):
        """
        Initialize form with village and election context.
        
        Args:
            village: Village object for filtering candidates
            election: Election object for filtering candidates
        """
        super().__init__(*args, **kwargs)
        
        self.village = village
        self.election = election
        
        if village and election:
            # Set Sarpanch candidates queryset (only active)
            self.fields['sarpanch_candidate'].queryset = Candidate.objects.filter(
                election=election,
                village=village,
                position_type=Candidate.POSITION_SARPANCH,
                is_active=True
            ).order_by('full_name')
            
            # Set Wards queryset
            self.fields['ward'].queryset = Ward.objects.filter(
                village=village
            ).order_by('number')
        
        # If ward is selected, filter ward member candidates (only active)
        if 'ward' in self.data:
            try:
                ward_id = int(self.data.get('ward'))
                self.fields['ward_member_candidate'].queryset = Candidate.objects.filter(
                    election=election,
                    ward_id=ward_id,
                    position_type=Candidate.POSITION_WARD_MEMBER,
                    is_active=True
                ).order_by('full_name')
            except (ValueError, TypeError):
                pass

    def clean_mobile_number(self):
        """Validate mobile number format."""
        mobile = self.cleaned_data.get('mobile_number')
        if mobile:
            # Remove any spaces or special characters
            mobile = ''.join(filter(str.isdigit, mobile))
            if len(mobile) != 10:
                raise ValidationError('Mobile number must be exactly 10 digits.')
            if mobile[0] not in '6789':
                raise ValidationError('Mobile number must start with 6, 7, 8, or 9.')
        return mobile

    def clean(self):
        """
        Validate the entire form:
        - Ensure candidates belong to the correct election and location
        - Ensure ward member candidate belongs to selected ward
        """
        cleaned_data = super().clean()
        
        sarpanch = cleaned_data.get('sarpanch_candidate')
        ward = cleaned_data.get('ward')
        ward_member = cleaned_data.get('ward_member_candidate')
        
        # Validate sarpanch candidate
        if sarpanch:
            if sarpanch.position_type != Candidate.POSITION_SARPANCH:
                self.add_error('sarpanch_candidate', 'Invalid Sarpanch candidate selection.')
            if self.election and sarpanch.election_id != self.election.id:
                self.add_error('sarpanch_candidate', 'Candidate is not from this election.')
            if self.village and sarpanch.village_id != self.village.id:
                self.add_error('sarpanch_candidate', 'Candidate is not from this village.')
        
        # Validate ward belongs to village
        if ward and self.village:
            if ward.village_id != self.village.id:
                self.add_error('ward', 'Selected ward does not belong to this village.')
        
        # Validate ward member candidate
        if ward_member:
            if ward_member.position_type != Candidate.POSITION_WARD_MEMBER:
                self.add_error('ward_member_candidate', 'Invalid Ward Member candidate selection.')
            if self.election and ward_member.election_id != self.election.id:
                self.add_error('ward_member_candidate', 'Candidate is not from this election.')
            if ward and ward_member.ward_id != ward.id:
                self.add_error('ward_member_candidate', 'Candidate is not from the selected ward.')
        
        return cleaned_data


class OTPVerificationForm(forms.Form):
    """
    Form for OTP verification (placeholder for future implementation).
    Currently used for simulation/testing purposes.
    """
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': 'Enter 6-digit OTP',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
            'maxlength': '6',
            'autocomplete': 'one-time-code'
        }),
        help_text="Enter the 6-digit OTP sent to your mobile number"
    )

    def clean_otp(self):
        """Validate OTP format."""
        otp = self.cleaned_data.get('otp')
        if otp:
            if not otp.isdigit():
                raise ValidationError('OTP must contain only digits.')
            if len(otp) != 6:
                raise ValidationError('OTP must be exactly 6 digits.')
        return otp

