# Local Elections Voting System

A Django-based web application for conducting local elections for **Sarpanch** and **Ward Member** positions at the Gram Panchayat (village) level.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Django](https://img.shields.io/badge/Django-5.0-green)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- 🗳️ **Complete Voting Flow**: District → Mandal → Village selection with candidate voting
- 👤 **Dual Position Voting**: Vote for both Sarpanch and Ward Member in one session
- 📱 **Mobile Number Verification**: One-person-one-vote enforcement using mobile numbers
- 📊 **Real-time Results**: Admin dashboard with vote counts and percentages
- 📥 **CSV Export**: Export voting data for analysis
- 🔒 **Security**: CSRF protection, form validation, and audit trails
- 📱 **Responsive Design**: Mobile-friendly Bootstrap 5 UI

## Tech Stack

- **Backend**: Django 5.x (Python 3.10+)
- **Database**: SQLite (development) / PostgreSQL (production-ready)
- **Frontend**: Django Templates, Bootstrap 5, JavaScript
- **Forms**: Django Crispy Forms with Bootstrap 5

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd VoterApp
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Linux/macOS
   python -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser** (for admin access):
   ```bash
   python manage.py createsuperuser
   ```

6. **Load sample data** (optional but recommended):
   ```bash
   python manage.py create_sample_data
   ```

7. **Start the development server**:
   ```bash
   python manage.py runserver
   ```

8. **Access the application**:
   - **Voting Portal**: http://127.0.0.1:8000/
   - **Admin Panel**: http://127.0.0.1:8000/admin/
   - **Results Dashboard**: http://127.0.0.1:8000/admin-results/ (staff only)

## Project Structure

```
VoterApp/
├── local_elections/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── elections/                # Main application
│   ├── models.py            # Database models
│   ├── views.py             # View controllers
│   ├── forms.py             # Form definitions
│   ├── admin.py             # Admin configuration
│   ├── urls.py              # URL routing
│   └── management/
│       └── commands/
│           └── create_sample_data.py
├── templates/                # HTML templates
│   ├── base.html
│   └── elections/
│       ├── landing.html
│       ├── select_location.html
│       ├── vote.html
│       ├── thank_you.html
│       └── admin_results_village.html
├── static/                   # Static files (CSS, JS)
├── manage.py
├── requirements.txt
└── README.md
```

## Data Models

### Location Hierarchy
- **District** → **Mandal** → **Village** → **Ward**

### Election System
- **Election**: Represents an election event with start/end times
- **Candidate**: Candidates for Sarpanch (village-level) or Ward Member (ward-level)
- **Voter**: Identified by unique mobile number
- **Vote**: Records the vote with audit information

## Voting Flow

1. **Landing Page** (`/`): Introduction and "Start Voting" button
2. **Location Selection** (`/select-location/`): Select District → Mandal → Village
3. **Voting Page** (`/vote/`):
   - View and select Sarpanch candidate
   - Select Ward and Ward Member candidate
   - Enter mobile number for verification
4. **Thank You** (`/thank-you/`): Confirmation of successful vote

## Admin Features

Access the admin panel at `/admin/` to:

- Manage Districts, Mandals, Villages, and Wards
- Create and configure Elections
- Add/edit Candidates
- View Voters (read-only mobile numbers)
- View Votes (read-only, cannot be edited)

### Results Dashboard

Staff users can access `/admin-results/` to:

- View election statistics
- See vote counts per candidate
- Export voting data as CSV

## API Endpoints

### AJAX Endpoints (for dynamic dropdowns)
- `GET /ajax/mandals/?district_id=<id>` - Get mandals for a district
- `GET /ajax/villages/?mandal_id=<id>` - Get villages for a mandal
- `GET /ajax/ward-candidates/?ward_id=<id>` - Get ward member candidates

## Configuration

### Database (PostgreSQL for Production)

Edit `local_elections/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'local_elections',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Security (Production)

For production deployment:

1. Set `DEBUG = False`
2. Set a strong `SECRET_KEY` (use environment variable)
3. Configure `ALLOWED_HOSTS`
4. Enable HTTPS settings

## Validation Rules

- **One Vote Per Person**: Each mobile number can only vote once per election per village
- **Candidate Validation**: 
  - Sarpanch candidates must belong to the selected village
  - Ward Member candidates must belong to the selected ward
- **Mobile Number**: Must be a valid 10-digit Indian mobile number (starts with 6-9)
- **Election Timing**: Votes only accepted during active election period

## Sample Data

The `create_sample_data` command creates:

- 3 Districts (Hyderabad, Rangareddy, Medak)
- 9 Mandals (3 per district)
- 18 Villages (2 per mandal)
- 72 Wards (4 per village)
- 1 Active Election
- ~150+ Candidates (Sarpanch and Ward Members)

```bash
# Create sample data
python manage.py create_sample_data

# Clear existing data and recreate
python manage.py create_sample_data --clear
```

## Future Enhancements

- [ ] OTP verification via SMS gateway integration
- [ ] Voter registration with Aadhaar/ID verification
- [ ] Real-time result updates using WebSockets
- [ ] Multi-language support (Telugu, Hindi)
- [ ] Candidate photo uploads
- [ ] Voting receipts (PDF generation)
- [ ] Election scheduling automation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues or questions, please open a GitHub issue or contact the development team.

---

**Disclaimer**: This is a demonstration voting system for educational purposes. For actual elections, use certified and audited election management systems that comply with local election laws and regulations.

