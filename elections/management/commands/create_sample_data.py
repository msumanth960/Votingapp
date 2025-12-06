"""
Management command to create sample data for testing the election system.

Usage:
    python manage.py create_sample_data

This creates:
- 3 Districts
- 2-3 Mandals per District
- 2-3 Villages per Mandal
- 3-5 Wards per Village
- 1 Active Election
- Sarpanch and Ward Member candidates for each village/ward
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from elections.models import (
    District, Mandal, Village, Ward,
    Election, Candidate
)


class Command(BaseCommand):
    help = 'Create sample data for testing the local elections voting system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating sample data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Candidate.objects.all().delete()
            Election.objects.all().delete()
            Ward.objects.all().delete()
            Village.objects.all().delete()
            Mandal.objects.all().delete()
            District.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        self.stdout.write('Creating sample data...')

        # Create Districts
        districts_data = [
            'Hyderabad',
            'Rangareddy',
            'Medak',
        ]
        
        districts = {}
        for name in districts_data:
            district, created = District.objects.get_or_create(name=name)
            districts[name] = district
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f'  District: {name} - {status}')

        # Create Mandals
        mandals_data = {
            'Hyderabad': ['Secunderabad', 'Begumpet', 'Ameerpet'],
            'Rangareddy': ['Shamshabad', 'Ibrahimpatnam', 'Hayathnagar'],
            'Medak': ['Siddipet', 'Dubbak', 'Gajwel'],
        }
        
        mandals = {}
        for district_name, mandal_names in mandals_data.items():
            for mandal_name in mandal_names:
                mandal, created = Mandal.objects.get_or_create(
                    district=districts[district_name],
                    name=mandal_name
                )
                mandals[mandal_name] = mandal
                status = 'Created' if created else 'Already exists'
                self.stdout.write(f'  Mandal: {mandal_name} ({district_name}) - {status}')

        # Create Villages
        villages_data = {
            'Secunderabad': ['Bowenpally', 'Trimulgherry'],
            'Begumpet': ['Somajiguda', 'Raj Bhavan'],
            'Ameerpet': ['SR Nagar', 'Balkampet'],
            'Shamshabad': ['Shamshabad Village', 'Rajendranagar'],
            'Ibrahimpatnam': ['Ibrahimpatnam Village', 'Manchal'],
            'Hayathnagar': ['Hayathnagar Village', 'Pedda Amberpet'],
            'Siddipet': ['Siddipet Town', 'Cheriyal'],
            'Dubbak': ['Dubbak Village', 'Toguta'],
            'Gajwel': ['Gajwel Town', 'Pragnapur'],
        }
        
        villages = {}
        for mandal_name, village_names in villages_data.items():
            for village_name in village_names:
                village, created = Village.objects.get_or_create(
                    mandal=mandals[mandal_name],
                    name=village_name
                )
                villages[village_name] = village
                status = 'Created' if created else 'Already exists'
                self.stdout.write(f'  Village: {village_name} ({mandal_name}) - {status}')

        # Create Wards for each village
        wards = {}
        for village_name, village in villages.items():
            village_wards = []
            ward_count = 4  # 4 wards per village
            for ward_num in range(1, ward_count + 1):
                ward, created = Ward.objects.get_or_create(
                    village=village,
                    number=ward_num,
                    defaults={'name': f'Ward {ward_num} Area'}
                )
                village_wards.append(ward)
                status = 'Created' if created else 'Already exists'
                self.stdout.write(f'    Ward {ward_num} in {village_name} - {status}')
            wards[village_name] = village_wards

        # Create Election
        now = timezone.now()
        election, created = Election.objects.get_or_create(
            name='2025 Gram Panchayat Elections',
            defaults={
                'description': 'Local body elections for Sarpanch and Ward Members',
                'start_time': now - timedelta(days=1),  # Started yesterday
                'end_time': now + timedelta(days=7),    # Ends in 7 days
                'is_active': True,
            }
        )
        status = 'Created' if created else 'Already exists'
        self.stdout.write(f'Election: {election.name} - {status}')

        # Sample candidate names
        candidate_first_names = [
            'Rajesh', 'Suresh', 'Ramesh', 'Venkat', 'Krishna',
            'Lakshmi', 'Padma', 'Sarojini', 'Vijaya', 'Anjali',
            'Srinivasrao', 'Narasimha', 'Mahesh', 'Prasad', 'Ravi',
            'Sunitha', 'Kavitha', 'Bharathi', 'Swarupa', 'Madhavi'
        ]
        
        candidate_last_names = [
            'Reddy', 'Rao', 'Kumar', 'Naidu', 'Goud',
            'Sharma', 'Verma', 'Choudhary', 'Singh', 'Gupta',
            'Devi', 'Rani', 'Begum', 'Swamy', 'Prasad'
        ]
        
        parties = [
            'Telugu Desam Party',
            'Bharatiya Janata Party',
            'Indian National Congress',
            'Telangana Rashtra Samithi',
            '',  # Independent
        ]
        
        symbols = ['Bicycle', 'Fan', 'Lotus', 'Hand', 'Car', 'Drum', 'Pot', 'Chair']

        # Create Candidates for each village
        import random
        random.seed(42)  # For reproducible data
        
        candidate_count = 0
        for village_name, village in villages.items():
            # Sarpanch candidates (3 per village)
            for i in range(3):
                full_name = f"{random.choice(candidate_first_names)} {random.choice(candidate_last_names)}"
                party = random.choice(parties)
                symbol = random.choice(symbols) if not party else ''
                
                candidate, created = Candidate.objects.get_or_create(
                    election=election,
                    village=village,
                    ward=None,
                    full_name=full_name,
                    position_type=Candidate.POSITION_SARPANCH,
                    defaults={
                        'party_name': party,
                        'symbol': symbol if not party else '',
                        'bio': f'Experienced leader committed to village development.',
                    }
                )
                if created:
                    candidate_count += 1
            
            # Ward Member candidates (2-3 per ward)
            for ward in wards[village_name]:
                for i in range(random.randint(2, 3)):
                    full_name = f"{random.choice(candidate_first_names)} {random.choice(candidate_last_names)}"
                    party = random.choice(parties)
                    
                    candidate, created = Candidate.objects.get_or_create(
                        election=election,
                        village=village,
                        ward=ward,
                        full_name=full_name,
                        position_type=Candidate.POSITION_WARD_MEMBER,
                        defaults={
                            'party_name': party,
                            'symbol': random.choice(symbols) if not party else '',
                            'bio': f'Dedicated to serving Ward {ward.number} residents.',
                        }
                    )
                    if created:
                        candidate_count += 1

        self.stdout.write(self.style.SUCCESS(f'\nSample data created successfully!'))
        self.stdout.write(f'  - {District.objects.count()} Districts')
        self.stdout.write(f'  - {Mandal.objects.count()} Mandals')
        self.stdout.write(f'  - {Village.objects.count()} Villages')
        self.stdout.write(f'  - {Ward.objects.count()} Wards')
        self.stdout.write(f'  - {Election.objects.count()} Election(s)')
        self.stdout.write(f'  - {Candidate.objects.count()} Candidates')
        
        self.stdout.write(self.style.SUCCESS('\nYou can now:'))
        self.stdout.write('  1. Run the server: python manage.py runserver')
        self.stdout.write('  2. Visit http://127.0.0.1:8000/ to start voting')
        self.stdout.write('  3. Visit http://127.0.0.1:8000/admin/ to manage data')

