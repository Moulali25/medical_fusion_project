import os
import unittest
import json
from io import BytesIO

# Import app components from the backend
from app import app, db  # pyre-ignore
from models import User, Patient  # pyre-ignore

class MedFuseTestCase(unittest.TestCase):
    """
    Test suite for the MedFuse Backend API.
    Covers Authentication, Models, and basic API endpoints.
    """
    
    def setUp(self):
        """Set up the test environment before each test."""
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        # Use an in-memory SQLite database so tests don't affect real data
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' 
        
        self.client = app.test_client()
        
        # Create an application context
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Initialize the database
        db.create_all()

    def tearDown(self):

        """Clean up the test environment after each test."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # --- 1. Authentication Tests ---

    def test_01_user_registration_valid(self):

        """Test successful user registration."""
        response = self.client.post('/api/auth/register', 
            data=json.dumps({
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123"
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"User registered successfully!", response.data)
        
        # Verify user was created in the database
        user = User.query.filter_by(email="test@example.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
        


    def test_02_user_registration_duplicate(self):
        """Test registration failure on duplicate email."""
        # Register the first time
        self.client.post('/api/auth/register', data=json.dumps({
            "username": "testuser", 
            "email": "test@example.com", 
            "password": "password123"
        }), content_type='application/json')
        
        # Attempt to register again with same email
        response = self.client.post('/api/auth/register', data=json.dumps({
            "username": "testuser2", 
            "email": "test@example.com", 
            "password": "password123"
        }), content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Email already exists", response.data)

    def test_03_user_login_valid(self):
        
        """Test successful user login."""
        self.client.post('/api/auth/register', data=json.dumps({
            "username": "testuser", "email": "test@example.com", "password": "password123"
        }), content_type='application/json')
        
        response = self.client.post('/api/auth/login', data=json.dumps({
            "email": "test@example.com", "password": "password123"
        }), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Login successful", response.data)

    def test_04_user_login_invalid(self):
        """Test login failure with invalid password."""
        self.client.post('/api/auth/register', data=json.dumps({
            "username": "testuser", "email": "test@example.com", "password": "password123"
        }), content_type='application/json')
        
        response = self.client.post('/api/auth/login', data=json.dumps({
            "email": "test@example.com", "password": "wrongpassword"
        }), content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Invalid email or password", response.data)

    def test_05_unauthorized_access(self):
        """Test accessing a protected route without logging in."""
        response = self.client.get('/api/history')
        # Flask-Login defaults to 302 redirect to the login page for unauthorized access
        self.assertEqual(response.status_code, 302)

    # --- 2. API Integration Tests ---

    def test_06_add_patient(self):
        """Test adding a patient after logging in."""
        # Setup and Login
        self.client.post('/api/auth/register', data=json.dumps({
            "username": "doctor", "email": "doc@hospital.com", "password": "pass"
        }), content_type='application/json')
        self.client.post('/api/auth/login', data=json.dumps({
            "email": "doc@hospital.com", "password": "pass"
        }), content_type='application/json')

        # Add Patient
        response = self.client.post('/api/patients', data=json.dumps({
            "patient_id": "PT-001",
            "name": "John Doe",
            "age": 45,
            "sex": "M",
            "condition": "Brain Tumor Checkup",
            "status": "Stable"
        }), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Patient added successfully", response.data)
        
        # Verify in DB
        patient = Patient.query.filter_by(patient_id="PT-001").first()
        self.assertIsNotNone(patient)
        self.assertEqual(patient.name, "John Doe")

    def test_07_image_fusion_missing_files(self):
        """Test that fusion API catches missing files."""
        # Setup and Login
        self.client.post('/api/auth/register', data=json.dumps({
            "username": "doctor", "email": "doc@hospital.com", "password": "pass"
        }), content_type='application/json')
        self.client.post('/api/auth/login', data=json.dumps({
            "email": "doc@hospital.com", "password": "pass"
        }), content_type='application/json')

        # Attempt fusion without sending form files
        response = self.client.post('/api/fuse', data={})
        
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Missing files", response.data)

    def test_08_get_patients_list(self):
        """Test retrieving the list of patients."""
        # Setup and Login
        self.client.post('/api/auth/register', data=json.dumps({
            "username": "doctor", "email": "doc@hospital.com", "password": "pass"
        }), content_type='application/json')
        self.client.post('/api/auth/login', data=json.dumps({
            "email": "doc@hospital.com", "password": "pass"
        }), content_type='application/json')
        
        # Add Patient First
        self.client.post('/api/patients', data=json.dumps({
            "patient_id": "PT-002",
            "name": "Jane Doe",
            "age": 30,
            "sex": "F",
            "condition": "Healthy",
            "status": "Stable"
        }), content_type='application/json')

        # Fetch Patients
        response = self.client.get('/api/patients')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Jane Doe", response.data)
        self.assertIn(b"PT-002", response.data)

    def test_09_get_history(self):
        """Test retrieving the fusion history."""
        # Setup and Login
        self.client.post('/api/auth/register', data=json.dumps({
            "username": "doctor", "email": "doc@hospital.com", "password": "pass"
        }), content_type='application/json')
        self.client.post('/api/auth/login', data=json.dumps({
            "email": "doc@hospital.com", "password": "pass"
        }), content_type='application/json')

        # Fetch History
        response = self.client.get('/api/history')
        self.assertEqual(response.status_code, 200)
        # Should return an empty JSON list
        self.assertEqual(json.loads(response.data), [])

    def test_10_logout(self):
        """Test user logout functionality."""
        # Setup and Login
        self.client.post('/api/auth/register', data=json.dumps({
            "username": "doctor", "email": "doc@hospital.com", "password": "pass"
        }), content_type='application/json')
        self.client.post('/api/auth/login', data=json.dumps({
            "email": "doc@hospital.com", "password": "pass"
        }), content_type='application/json')

        # Logout
        response = self.client.post('/api/auth/logout')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Logged out successfully", response.data)

        # Verify unauthorized after logout
        response = self.client.get('/api/history')
        self.assertEqual(response.status_code, 302) # Redirects to login

    def test_11_get_current_user(self):
        """Test retrieving the currently logged in user."""
        self.client.post('/api/auth/register', data=json.dumps({
            "username": "doctor2", "email": "doc2@hospital.com", "password": "pass"
        }), content_type='application/json')
        self.client.post('/api/auth/login', data=json.dumps({
            "email": "doc2@hospital.com", "password": "pass"
        }), content_type='application/json')

        response = self.client.get('/api/auth/current_user')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get("authenticated"))
        self.assertEqual(data.get("username"), "doctor2")

    def test_12_analyze_image_missing_file(self):
        """Test the analyze API without an image file."""
        self.client.post('/api/auth/register', data=json.dumps({
            "username": "tester12", "email": "test12@hospital.com", "password": "pass"
        }), content_type='application/json')
        self.client.post('/api/auth/login', data=json.dumps({
            "email": "test12@hospital.com", "password": "pass"
        }), content_type='application/json')
        
        # Missing file in POST request
        response = self.client.post('/api/analyze', data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"No image uploaded", response.data)

    def test_13_reset_password_valid_email(self):
        """Test password reset request for a valid email."""
        self.client.post('/api/auth/register', data=json.dumps({
            "username": "tester13", "email": "test13@hospital.com", "password": "pass"
        }), content_type='application/json')
        
        response = self.client.post('/api/auth/reset-password', data=json.dumps({
            "email": "test13@hospital.com"
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"A secure password reset link has been formally sent", response.data)

    def test_14_reset_password_invalid_email(self):
        """Test password reset request for a non-existent email."""
        response = self.client.post('/api/auth/reset-password', data=json.dumps({
            "email": "doesntexist@hospital.com"
        }), content_type='application/json')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Email address not found", response.data)

if __name__ == '__main__':
    # Run tests and collect result
    suite = unittest.TestLoader().loadTestsFromTestCase(MedFuseTestCase)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Calculate statistics
    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed
    
    # ANSI Colors
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

    # Print custom formatted summary
    print(f"\n{YELLOW}{'='*50}{RESET}")
    print(f"{YELLOW}               TEST RESULTS SUMMARY               {RESET}")
    print(f"{YELLOW}{'='*50}{RESET}")
    print(f"Total Test Cases Executed  : {total}")
    print(f"Test Cases Passed          : {GREEN}{passed}{RESET} out of {total}")
    print(f"Test Cases Failed/Errors   : {RED if failed > 0 else GREEN}{failed}{RESET}")
    print(f"{YELLOW}{'='*50}{RESET}")
    if failed == 0:
        print(f"Overall Status             : {GREEN}ALL PASSED (OK){RESET}")
    else:
        print(f"Overall Status             : {RED}SOME FAILED (FAIL){RESET}")
    print(f"{YELLOW}{'='*50}{RESET}")
