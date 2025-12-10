"""
Views for the Elections app.

This module contains views for:
- Public voting flow (landing, location selection, voting, thank you)
- Admin/Staff reporting (results, CSV export)
- AJAX endpoints for dynamic form loading
"""

import csv
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.generic import TemplateView, FormView
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Count, Q

from .models import (
    District, Mandal, Village, Ward,
    Election, Candidate, Voter, Vote
)
from .forms import LocationSelectionForm, VotingForm, OTPVerificationForm


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_active_election():
    """Get the currently active and ongoing election."""
    now = timezone.now()
    return Election.objects.filter(
        is_active=True,
        start_time__lte=now,
        end_time__gte=now
    ).first()


def generate_otp():
    """Generate a 6-digit OTP for verification."""
    return str(random.randint(100000, 999999))


# ==============================================================================
# Public Views - Voting Flow
# ==============================================================================

class LandingPageView(TemplateView):
    """
    Landing page for the voting application.
    Displays information about the election and a button to start voting.
    """
    template_name = 'elections/landing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_election'] = get_active_election()
        context['upcoming_elections'] = Election.objects.filter(
            is_active=True,
            start_time__gt=timezone.now()
        ).order_by('start_time')[:3]
        return context


class LocationSelectionView(FormView):
    """
    View for selecting location hierarchy: District -> Mandal -> Village.
    """
    template_name = 'elections/select_location.html'
    form_class = LocationSelectionForm

    def dispatch(self, request, *args, **kwargs):
        """Check if there's an active election before proceeding."""
        self.election = get_active_election()
        if not self.election:
            messages.error(request, 'There is no active election at the moment. Please check back later.')
            return redirect('elections:landing')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['election'] = self.election
        return context

    def form_valid(self, form):
        """Store selected village in session and redirect to voting page."""
        village = form.cleaned_data['village']
        self.request.session['selected_village_id'] = village.id
        self.request.session['selected_election_id'] = self.election.id
        return redirect('elections:vote')


class VotingView(View):
    """
    Main voting view where users select candidates and submit their vote.
    """
    template_name = 'elections/vote.html'

    def dispatch(self, request, *args, **kwargs):
        """Validate session data and election status."""
        # Check for active election
        self.election = get_active_election()
        if not self.election:
            messages.error(request, 'There is no active election at the moment.')
            return redirect('elections:landing')

        # Check for selected village in session
        village_id = request.session.get('selected_village_id')
        if not village_id:
            messages.warning(request, 'Please select your location first.')
            return redirect('elections:select_location')

        try:
            self.village = Village.objects.get(id=village_id)
        except Village.DoesNotExist:
            messages.error(request, 'Invalid location. Please select again.')
            return redirect('elections:select_location')

        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """Display the voting form."""
        form = VotingForm(village=self.village, election=self.election)
        context = {
            'form': form,
            'village': self.village,
            'election': self.election,
            'sarpanch_candidates': Candidate.objects.filter(
                election=self.election,
                village=self.village,
                position_type=Candidate.POSITION_SARPANCH,
                is_active=True  # Only show active candidates
            ).order_by('full_name'),
            'wards': Ward.objects.filter(village=self.village).order_by('number'),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        """Process the vote submission."""
        form = VotingForm(
            village=self.village,
            election=self.election,
            data=request.POST
        )

        if form.is_valid():
            return self.process_vote(request, form)

        # Form is invalid, re-render with errors
        context = {
            'form': form,
            'village': self.village,
            'election': self.election,
            'sarpanch_candidates': Candidate.objects.filter(
                election=self.election,
                village=self.village,
                position_type=Candidate.POSITION_SARPANCH,
                is_active=True  # Only show active candidates
            ).order_by('full_name'),
            'wards': Ward.objects.filter(village=self.village).order_by('number'),
        }
        return render(request, self.template_name, context)

    def process_vote(self, request, form):
        """Process a valid vote submission."""
        mobile_number = form.cleaned_data['mobile_number']
        voter_name = form.cleaned_data.get('voter_name', '')
        family_vote_count = form.cleaned_data.get('family_vote_count', 1)
        sarpanch_candidate = form.cleaned_data['sarpanch_candidate']
        ward = form.cleaned_data['ward']
        ward_member_candidate = form.cleaned_data['ward_member_candidate']

        # Get or create voter
        voter, created = Voter.objects.get_or_create(
            mobile_number=mobile_number
        )
        
        # Update voter name if provided
        if voter_name and (not voter.name or created):
            voter.name = voter_name
            voter.save()

        # Check if voter has already voted in this election for this village
        existing_vote = Vote.objects.filter(
            election=self.election,
            voter=voter,
            village=self.village
        ).exists()

        if existing_vote:
            messages.error(
                request,
                'You have already voted in this election for this village. '
                'Each mobile number can only vote once per village per election.'
            )
            return redirect('elections:vote')

        # Create the vote
        try:
            vote = Vote.objects.create(
                election=self.election,
                village=self.village,
                ward=ward,
                voter=voter,
                sarpanch_candidate=sarpanch_candidate,
                ward_member_candidate=ward_member_candidate,
                family_vote_count=family_vote_count,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            # Clear session data
            if 'selected_village_id' in request.session:
                del request.session['selected_village_id']
            if 'selected_election_id' in request.session:
                del request.session['selected_election_id']

            messages.success(request, 'Your vote has been recorded successfully!')
            return redirect('elections:thank_you')

        except IntegrityError:
            messages.error(
                request,
                'An error occurred while recording your vote. '
                'You may have already voted in this election.'
            )
            return redirect('elections:vote')


class ThankYouView(TemplateView):
    """
    Thank you page displayed after successful vote submission.
    """
    template_name = 'elections/thank_you.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['election'] = get_active_election()
        return context


# ==============================================================================
# AJAX Endpoints for Dynamic Form Loading
# ==============================================================================

def load_mandals(request):
    """
    AJAX endpoint to load mandals for a selected district.
    """
    district_id = request.GET.get('district_id')
    mandals = Mandal.objects.filter(district_id=district_id).order_by('name')
    return JsonResponse(list(mandals.values('id', 'name')), safe=False)


def load_villages(request):
    """
    AJAX endpoint to load villages for a selected mandal.
    """
    mandal_id = request.GET.get('mandal_id')
    villages = Village.objects.filter(
        mandal_id=mandal_id,
        is_active=True  # Only show active villages
    ).order_by('name')
    return JsonResponse(list(villages.values('id', 'name')), safe=False)


def load_ward_candidates(request):
    """
    AJAX endpoint to load ward member candidates for a selected ward.
    """
    ward_id = request.GET.get('ward_id')
    election_id = request.session.get('selected_election_id')
    
    if not ward_id or not election_id:
        return JsonResponse([], safe=False)
    
    candidates = Candidate.objects.filter(
        ward_id=ward_id,
        election_id=election_id,
        position_type=Candidate.POSITION_WARD_MEMBER,
        is_active=True  # Only show active candidates
    ).order_by('full_name')
    
    data = [{
        'id': c.id,
        'full_name': c.full_name,
        'party_name': c.party_name or 'Independent',
        'symbol': c.symbol or '-',
        'symbol_url': c.symbol_url or '',
        'promises': c.promises_list  # Include promises list
    } for c in candidates]
    
    return JsonResponse(data, safe=False)


# ==============================================================================
# Admin/Staff Views - Results and Reporting
# ==============================================================================

@method_decorator(staff_member_required, name='dispatch')
class VillageResultsView(View):
    """
    View to display election results for a specific village.
    Shows vote counts for Sarpanch and Ward Member candidates.
    """
    template_name = 'elections/admin_results_village.html'

    def get(self, request, village_id):
        village = get_object_or_404(Village, id=village_id)
        election = get_active_election()
        
        # Get election from query param if provided
        election_id = request.GET.get('election_id')
        if election_id:
            election = get_object_or_404(Election, id=election_id)
        
        if not election:
            # Get the most recent election with votes for this village
            election = Election.objects.filter(
                votes__village=village
            ).order_by('-start_time').first()

        if not election:
            messages.warning(request, 'No election data found for this village.')
            return redirect('admin:index')

        # Total votes for this village in this election
        total_votes = Vote.objects.filter(
            election=election,
            village=village
        ).count()

        # Sarpanch vote counts
        sarpanch_results = Candidate.objects.filter(
            election=election,
            village=village,
            position_type=Candidate.POSITION_SARPANCH
        ).annotate(
            vote_count=Count('sarpanch_votes', filter=Q(sarpanch_votes__election=election))
        ).order_by('-vote_count')

        # Ward-wise results
        wards = Ward.objects.filter(village=village).order_by('number')
        ward_results = []
        for ward in wards:
            ward_candidates = Candidate.objects.filter(
                election=election,
                ward=ward,
                position_type=Candidate.POSITION_WARD_MEMBER
            ).annotate(
                vote_count=Count('ward_member_votes', filter=Q(ward_member_votes__election=election))
            ).order_by('-vote_count')
            
            ward_votes = Vote.objects.filter(
                election=election,
                ward=ward
            ).count()
            
            ward_results.append({
                'ward': ward,
                'candidates': ward_candidates,
                'total_votes': ward_votes
            })

        # All elections for dropdown
        all_elections = Election.objects.all().order_by('-start_time')

        context = {
            'village': village,
            'election': election,
            'total_votes': total_votes,
            'sarpanch_results': sarpanch_results,
            'ward_results': ward_results,
            'all_elections': all_elections,
        }
        return render(request, self.template_name, context)


@staff_member_required
def export_votes_csv(request, village_id):
    """
    Export votes for a village as CSV.
    Mobile numbers are partially masked for privacy.
    """
    village = get_object_or_404(Village, id=village_id)
    
    # Get election from query param or use active election
    election_id = request.GET.get('election_id')
    if election_id:
        election = get_object_or_404(Election, id=election_id)
    else:
        election = get_active_election()
        if not election:
            election = Election.objects.filter(
                votes__village=village
            ).order_by('-start_time').first()

    if not election:
        messages.error(request, 'No election found for export.')
        return redirect('elections:admin_results_village', village_id=village_id)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f"votes_{village.name}_{election.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Vote ID',
        'Voter ID',
        'Mobile (Masked)',
        'Election',
        'Village',
        'Ward',
        'Sarpanch Candidate',
        'Ward Member Candidate',
        'Voted At',
        'IP Address'
    ])

    votes = Vote.objects.filter(
        election=election,
        village=village
    ).select_related(
        'voter', 'election', 'village', 'ward',
        'sarpanch_candidate', 'ward_member_candidate'
    ).order_by('-created_at')

    for vote in votes:
        writer.writerow([
            vote.id,
            vote.voter.id,
            vote.voter.masked_mobile,
            vote.election.name,
            vote.village.name,
            f"Ward {vote.ward.number}" if vote.ward else '-',
            vote.sarpanch_candidate.full_name if vote.sarpanch_candidate else '-',
            vote.ward_member_candidate.full_name if vote.ward_member_candidate else '-',
            vote.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            vote.ip_address or '-'
        ])

    return response


@staff_member_required
def results_dashboard(request):
    """
    Dashboard view showing overview of all elections and results.
    """
    elections = Election.objects.annotate(
        vote_count=Count('votes')
    ).order_by('-start_time')

    villages_with_votes = Village.objects.filter(
        votes__isnull=False
    ).distinct().annotate(
        vote_count=Count('votes')
    ).order_by('-vote_count')[:20]

    context = {
        'elections': elections,
        'villages_with_votes': villages_with_votes,
        'total_votes': Vote.objects.count(),
        'total_voters': Voter.objects.count(),
    }
    return render(request, 'elections/results_dashboard.html', context)


# ==============================================================================
# OTP Verification Views (Placeholder for future implementation)
# ==============================================================================

class OTPVerificationView(FormView):
    """
    OTP verification view (placeholder implementation).
    In production, integrate with SMS gateway.
    For now, simulates OTP verification.
    """
    template_name = 'elections/otp_verification.html'
    form_class = OTPVerificationForm

    def dispatch(self, request, *args, **kwargs):
        """Check if OTP is in session."""
        if 'pending_vote_otp' not in request.session:
            messages.error(request, 'Session expired. Please start over.')
            return redirect('elections:select_location')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # In debug mode, show the OTP for testing
        from django.conf import settings
        if settings.DEBUG:
            context['debug_otp'] = self.request.session.get('pending_vote_otp')
        return context

    def form_valid(self, form):
        """Verify OTP and process vote if correct."""
        entered_otp = form.cleaned_data['otp']
        expected_otp = self.request.session.get('pending_vote_otp')

        if entered_otp != expected_otp:
            messages.error(self.request, 'Invalid OTP. Please try again.')
            return self.form_invalid(form)

        # OTP verified - clear session and redirect to success
        if 'pending_vote_otp' in self.request.session:
            del self.request.session['pending_vote_otp']
        
        messages.success(self.request, 'OTP verified successfully!')
        return redirect('elections:thank_you')

