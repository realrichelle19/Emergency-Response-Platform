# Emergency Response Platform

A comprehensive emergency response coordination system that connects verified citizen skills with emergency and civic needs during disasters or crises. Built with Flask backend and vanilla JavaScript frontend, this platform enables real-time coordination between volunteers, emergency authorities, and administrators.

## 🚨 Overview

The Emergency Response Platform is designed to streamline emergency response by matching skilled volunteers with urgent needs during disasters. The system supports location-based matching, skill verification, and real-time coordination to ensure effective emergency response.

## ✨ Key Features

### Multi-Role System
- **Volunteers**: Register skills, set availability, respond to emergency assignments
- **Authorities**: Create and manage emergency requests, coordinate response efforts
- **Administrators**: Verify volunteer skills, manage users, oversee system operations

### Core Capabilities
- **Real-time Matching**: Location and skill-based volunteer matching for emergencies
- **Skill Verification**: Admin-managed verification system with documentation tracking
- **Assignment Management**: Complete assignment lifecycle from creation to completion
- **Live Updates**: Polling-based real-time status updates across all user roles
- **Geographic Coordination**: Location-based emergency request distribution
- **Priority Management**: Critical, high, medium, and low priority emergency classification

### Skill Categories
- **Medical**: First Aid, Emergency Medicine, Nursing, Paramedic, Mental Health Support
- **Rescue**: Search and Rescue, Water Rescue, Fire Fighting, Technical Rescue, K9 Handler
- **Logistics**: Supply Chain, Transportation, Warehouse Operations, Food Service, Shelter Management
- **Technical**: Communications, IT Support, Engineering, Heavy Equipment, Drone Operations
- **Communication**: Translation, Public Information, Sign Language, Community Outreach
- **Other**: Administrative Support, Legal Aid, Childcare, Pet Care

## 🏗️ Architecture

### Backend (Flask)
```
backend/
├── app/
│   ├── admin/          # Admin management routes and forms
│   ├── api/            # REST API endpoints
│   ├── auth/           # Authentication and authorization
│   ├── authority/      # Authority-specific features
│   ├── main/           # Main application routes
│   ├── models/         # SQLAlchemy database models
│   ├── services/       # Business logic services
│   └── volunteer/      # Volunteer-specific features
├── scripts/            # Database initialization and utilities
├── config.py           # Application configuration
└── run.py             # Application entry point
```

### Frontend (Vanilla JavaScript)
```
frontend/
├── css/               # Styling (Bootstrap + custom CSS)
├── html/              # HTML templates for different user roles
├── js/                # JavaScript modules (API client, main logic)
└── index.html         # Main application entry point
```

### Database Schema
- **Users**: Base user model with role-based access control
- **VolunteerProfiles**: Location, availability, and bio information
- **Skills**: Master skill catalog with categories and descriptions
- **VolunteerSkills**: Skill assignments with verification status
- **EmergencyRequests**: Emergency incidents with location and requirements
- **Assignments**: Volunteer-emergency assignments with status tracking
- **ActivityLogs**: Comprehensive audit trail for all system actions

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd emergency-response-platform
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   # Initialize database with sample data
   flask init-db
   
   # Or reset existing database
   flask reset-db
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

7. **Access the application**
   - Backend API: http://localhost:5000
   - Frontend: Open `frontend/index.html` in your browser

### Sample Users
After running `flask init-db`, you can log in with these sample accounts:

**Admin**
- Email: `admin@emergency.local`
- Password: `password123`

**Authority**
- Email: `fire.chief@emergency.local`
- Password: `password123`

**Volunteer**
- Email: `volunteer1@emergency.local`
- Password: `password123`

## ⚙️ Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Database Configuration
DATABASE_URL=sqlite:///emergency_response.db
DEV_DATABASE_URL=sqlite:///emergency_response_dev.db
TEST_DATABASE_URL=sqlite:///:memory:

# Emergency System Configuration
DEFAULT_SEARCH_RADIUS_KM=10
MAX_SEARCH_RADIUS_KM=100
ESCALATION_TIMEOUT_MINUTES=30
```

### Database Options
- **Development**: SQLite (default, no setup required)
- **Production**: MySQL/PostgreSQL (configure DATABASE_URL)

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/login` - User authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/logout` - User logout

### Volunteers
- `GET /api/volunteers/profile` - Get volunteer profile
- `PUT /api/volunteers/profile` - Update volunteer profile
- `GET /api/volunteers/nearby-emergencies` - Get nearby emergency requests
- `POST /api/volunteers/respond` - Respond to emergency assignment

### Authorities
- `POST /api/authority/emergency` - Create emergency request
- `GET /api/authority/emergencies` - Get managed emergencies
- `PUT /api/authority/emergency/{id}` - Update emergency status

### Admin
- `GET /api/admin/users` - Get all users
- `PUT /api/admin/verify-skill` - Verify volunteer skill
- `GET /api/admin/pending-verifications` - Get pending skill verifications

### Real-time Updates
- `GET /api/volunteer/updates` - Volunteer dashboard updates
- `GET /api/authority/updates` - Authority dashboard updates
- `GET /api/admin/updates` - Admin dashboard updates

## 🧪 Testing

The project includes comprehensive testing with property-based testing using Hypothesis:

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/test_emergency_*.py
python -m pytest tests/test_assignment_*.py
python -m pytest tests/test_user_*.py

# Run with coverage
python -m pytest --cov=app
```

### Testing Philosophy
- **Property-based testing** for robust edge case coverage
- **Data integrity** and consistency validation
- **State management** and transition testing
- **Security** and access control verification
- **Performance** and scalability testing

## 🛠️ Development

### Flask CLI Commands
```bash
# Initialize database with sample data
flask init-db

# Reset database (drops all data)
flask reset-db

# Access Flask shell with models loaded
flask shell
```

### Code Quality
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write comprehensive docstrings
- Maintain test coverage above 80%

### Adding New Features
1. Create feature branch from main
2. Implement backend models and services
3. Add API endpoints with proper authentication
4. Create frontend interface
5. Write comprehensive tests
6. Update documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`python -m pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `docs/` folder
- Review the sample data in `backend/scripts/create_sample_data.py`

## 🔮 Future Enhancements

- Mobile application for field volunteers
- SMS/push notification integration
- Advanced mapping and routing features
- Integration with external emergency services
- Multi-language support
- Advanced analytics and reporting