"""
URL configuration for the Elections app.

URL Patterns:
- /                     - Landing page
- /select-location/     - Location selection (District -> Mandal -> Village)
- /vote/                - Voting page
- /thank-you/           - Thank you confirmation page
- /verify-otp/          - OTP verification (placeholder)

AJAX Endpoints:
- /ajax/mandals/        - Load mandals for a district
- /ajax/villages/       - Load villages for a mandal
- /ajax/ward-candidates/ - Load ward member candidates for a ward

Admin/Staff Results:
- /admin-results/                           - Results dashboard
- /admin-results/village/<village_id>/      - Village results
- /admin-results/export/<village_id>/       - CSV export
"""

from django.urls import path
from . import views

app_name = 'elections'

urlpatterns = [
    # Public voting flow
    path('', views.LandingPageView.as_view(), name='landing'),
    path('select-location/', views.LocationSelectionView.as_view(), name='select_location'),
    path('vote/', views.VotingView.as_view(), name='vote'),
    path('thank-you/', views.ThankYouView.as_view(), name='thank_you'),
    path('verify-otp/', views.OTPVerificationView.as_view(), name='verify_otp'),

    # AJAX endpoints for dynamic form loading
    path('ajax/mandals/', views.load_mandals, name='ajax_load_mandals'),
    path('ajax/villages/', views.load_villages, name='ajax_load_villages'),
    path('ajax/ward-candidates/', views.load_ward_candidates, name='ajax_load_ward_candidates'),

    # Admin/Staff result pages
    path('admin-results/', views.results_dashboard, name='results_dashboard'),
    path('admin-results/village/<int:village_id>/', views.VillageResultsView.as_view(), name='admin_results_village'),
    path('admin-results/export/<int:village_id>/', views.export_votes_csv, name='export_votes_csv'),
]

