"""
Security-specific tests for the AI Diet Planner Flask application.
"""

import os
import sys
import json
import uuid
import tempfile
import shutil
import unittest
from unittest.mock import patch

# Setup temp DB environment
_tmpdir = tempfile.mkdtemp(prefix="diet_sec_test_")
os.environ["DATABASE_URL"] = ""          # empty → SQLite
os.environ["DATABASE_PATH"] = os.path.join(_tmpdir, "test_sec.db")
os.environ["GEMINI_API_KEY"] = ""        # disable real AI calls
os.environ["OPENAI_API_KEY"] = ""
os.environ["SECRET_KEY"] = "test-secret-key-for-security-tests"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from models.user_model import create_tables, save_user, get_user_by_id, add_extended_columns
from models.auth_model import create_accounts_table, register_account
from models.reset_model import create_reset_token_table
from services.password_validator import validate_password


class TestSecurityFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build clean database schema
        try:
            create_tables()
            add_extended_columns()
            create_accounts_table()
            create_reset_token_table()
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(_tmpdir, ignore_errors=True)
        except Exception:
            pass

    def setUp(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def _create_user_data(self, email, name="Test User"):
        return {
            'session_id': str(uuid.uuid4()),
            'name': name,
            'email': email,
            'age': 25,
            'gender': 'male',
            'height': 170,
            'weight': 70,
            'country': 'India',
            'goal': 'maintain',
            'target_weight': 68,
            'diet_type': 'vegetarian',
            'food_allergies': '',
            'budget_preference': 'moderate',
            'activity_level': 'moderate',
            'exercise_type': 'Walking',
            'daily_steps': '3000-6000',
            'sleep_hours': 7,
            'sleep_quality': 'good',
            'night_wakeups': 0,
            'daytime_fatigue': 'rarely',
            'stress_level': 'low',
            'stress_sources': '',
            'work_hours': 8,
            'work_type': 'sedentary',
            'breakfast_time': '08:00',
            'lunch_time': '13:00',
            'dinner_time': '20:00',
            'late_night_eating': 'rarely',
            'water_intake': '2-3 liters',
            'breakfast_foods': 'oats',
            'lunch_foods': 'dal roti',
            'dinner_foods': 'sabzi roti',
            'snacks': 'nuts',
            'beverages': 'green tea',
            'meals_per_day': 3,
            'outside_food_frequency': 'rarely',
            'junk_food_frequency': '0',
            'medical_conditions': '',
            'medications': '',
            'health_issues': '',
            'menstrual_issues': 'not_applicable',
            'cuisine_preference': 'Indian',
            'food_dislikes': '',
            'cooking_time': '30 minutes',
            'cooking_skill': 'basic',
            'eating_speed': 'normal',
            'meal_prep': 'fresh_daily',
            'alcohol': 'never',
            'smoking': 'never',
            'supplements': '',
            'health_motivation': 'stay healthy',
            'exercise_intensity': 'moderate',
            'sleep_issues': 'Difficulty falling asleep',
            'digestive_issues': 'Frequent bloating',
            'bowel_frequency': 'once_daily',
            'probiotic_intake': 'often',
            'regular_drinks': 'Tea (chai) 3+ cups/day',
            'sitting_hours': 6,
            'screen_time': 8,
            'work_shift': 'day',
            'meal_skip': 'never',
            'stress_eating': 'no_change',
            'bedtime': '23:00',
        }

    # ── 1. CSRF Protection ──
    def test_csrf_protection_enforced(self):
        """POST request without CSRF token should be rejected (redirected with warning)."""
        app.config['WTF_CSRF_ENABLED'] = True
        resp = self.client.post('/login', data={'email': 'any@any.com', 'password': 'Password123'})
        # Flask-WTF CSRFProtect redirects to request.referrer or '/' with a flashed warning
        self.assertEqual(resp.status_code, 302)

    # ── 2. IDOR protection ──
    def test_idor_unauthorized_dashboard_access(self):
        """User A should not be allowed to access User B's dashboard."""
        # Register two accounts
        email_a = f"usera_{uuid.uuid4().hex[:8]}@example.com"
        email_b = f"userb_{uuid.uuid4().hex[:8]}@example.com"
        acct_a_id, _ = register_account("User A", email_a, "Password123")
        acct_b_id, _ = register_account("User B", email_b, "Password123")

        # Create user profiles for each account
        user_a_id = save_user(self._create_user_data(email_a, "User A Profile"))
        user_b_id = save_user(self._create_user_data(email_b, "User B Profile"))

        # Link them
        from models.auth_model import link_user_to_account
        link_user_to_account(user_a_id, acct_a_id)
        link_user_to_account(user_b_id, acct_b_id)

        # Login as User A
        with self.client.session_transaction() as sess:
            sess['account_id'] = acct_a_id
            sess['account_name'] = "User A"
            sess['account_email'] = email_a

        # Attempt to access User B's dashboard
        resp = self.client.get(f'/dashboard/{user_b_id}')
        # Should redirect to index with permission warning
        self.assertEqual(resp.status_code, 302)
        # Attempt to access User A's dashboard
        resp_a = self.client.get(f'/dashboard/{user_a_id}')
        self.assertEqual(resp_a.status_code, 200)

    def test_idor_api_diary_unauthorized(self):
        """User A should not be allowed to add diary entry for User B."""
        email_a = f"usera_{uuid.uuid4().hex[:8]}@example.com"
        email_b = f"userb_{uuid.uuid4().hex[:8]}@example.com"
        acct_a_id, _ = register_account("User A", email_a, "Password123")
        acct_b_id, _ = register_account("User B", email_b, "Password123")

        user_a_id = save_user(self._create_user_data(email_a))
        user_b_id = save_user(self._create_user_data(email_b))

        from models.auth_model import link_user_to_account
        link_user_to_account(user_a_id, acct_a_id)
        link_user_to_account(user_b_id, acct_b_id)

        with self.client.session_transaction() as sess:
            sess['account_id'] = acct_a_id

        # POST to User B's diary
        resp = self.client.post('/api/diary/add', json={
            'user_id': user_b_id,
            'meal_type': 'lunch',
            'food_name': 'Apple',
            'calories': 50,
            'date': '2026-06-15'
        })
        self.assertEqual(resp.status_code, 403)
        self.assertIn('Unauthorized', resp.get_json()['error'])

    # ── 3. Security Headers ──
    def test_security_headers_present(self):
        """Verify standard security headers are present in all responses."""
        resp = self.client.get('/')
        self.assertEqual(resp.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(resp.headers.get('X-Frame-Options'), 'SAMEORIGIN')
        self.assertEqual(resp.headers.get('X-XSS-Protection'), '1; mode=block')
        self.assertEqual(resp.headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')

    # ── 4. Admin Auth & Session Security ──
    def test_admin_dashboard_requires_auth(self):
        """Accessing admin dashboard without login should redirect to login."""
        resp = self.client.get('/admin/dashboard')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/admin/login', resp.headers.get('Location'))

    def test_admin_login_success(self):
        """Admin login with correct credentials should work and set session."""
        from config import Config
        resp = self.client.post('/admin/login', data={
            'username': Config.ADMIN_USERNAME,
            'password': Config.ADMIN_PASSWORD
        })
        self.assertEqual(resp.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('admin_logged_in'))

    # ── 5. Password Policy ──
    def test_password_policy_validation(self):
        """Verify password policy accepts strong passwords and rejects weak ones."""
        # 1. Too short
        valid, err = validate_password("Sh1")
        self.assertFalse(valid)
        self.assertIn("at least 8 characters", err)

        # 2. No uppercase
        valid, err = validate_password("weakpassword123")
        self.assertFalse(valid)
        self.assertIn("uppercase letter", err)

        # 3. No lowercase
        valid, err = validate_password("WEAKPASSWORD123")
        self.assertFalse(valid)
        self.assertIn("lowercase letter", err)

        # 4. No digits
        valid, err = validate_password("WeakPassword")
        self.assertFalse(valid)
        self.assertIn("at least one digit", err)

        # 5. Strong password
        valid, err = validate_password("StrongPassword123")
        self.assertTrue(valid)
        self.assertEqual(err, "")

    # ── 6. Open Redirect ──
    def test_open_redirect_protection(self):
        """Login redirect should reject external domain names and unsafe schemes."""
        email = f"redir_{uuid.uuid4().hex[:8]}@example.com"
        register_account("Redir User", email, "Password123")

        # Unsafe redirect
        resp = self.client.post('/login', data={
            'email': email,
            'password': 'Password123',
            'next': '//evil.com/malware'
        })
        # Should fall back to /my-dashboard
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('evil.com', resp.headers.get('Location'))
        self.assertIn('/my-dashboard', resp.headers.get('Location'))

        # Safe redirect (log out first to clear the session)
        self.client.get('/logout')
        resp_safe = self.client.post('/login', data={
            'email': email,
            'password': 'Password123',
            'next': '/questionnaire'
        })
        self.assertEqual(resp_safe.status_code, 302)
        self.assertIn('/questionnaire', resp_safe.headers.get('Location'))

    # ── 7. Error Handling Information Leak ──
    @patch('app.get_admin_stats')
    def test_500_handler_hides_stack_trace(self, mock_stats):
        """500 error should show clean error page rather than stack traces."""
        # Force a 500 error on the index route by mocking get_admin_stats to raise an error
        mock_stats.side_effect = Exception("Internal DB Crash")
        
        # Temporarily disable TESTING mode so Flask handles the error rather than raising it
        original_testing = app.config.get('TESTING', True)
        original_propagate = app.config.get('PROPAGATE_EXCEPTIONS')
        app.config['TESTING'] = False
        app.config['PROPAGATE_EXCEPTIONS'] = False
        
        try:
            resp = self.client.get('/')
            self.assertEqual(resp.status_code, 500)
            self.assertNotIn("Internal DB Crash", resp.get_data(as_text=True))
            self.assertNotIn("Traceback", resp.get_data(as_text=True))
            # It should render 500.html content (e.g. typical branding/apologies)
            self.assertIn("Something went wrong", resp.get_data(as_text=True))
        finally:
            app.config['TESTING'] = original_testing
            if original_propagate is not None:
                app.config['PROPAGATE_EXCEPTIONS'] = original_propagate
            else:
                app.config.pop('PROPAGATE_EXCEPTIONS', None)

    # ── 8. Static File Caching Optimization ──
    def test_static_file_caching(self):
        """Verify static files return Cache-Control headers for performance optimization."""
        resp = self.client.get('/static/js/script.js')
        self.assertEqual(resp.status_code, 200)
        cache_control = resp.headers.get('Cache-Control', '')
        self.assertIn('public', cache_control)
        self.assertIn('max-age=31536000', cache_control)

    # ── 9. Vision & Voice API Hardening ──
    def test_vision_api_auth_enforced(self):
        """Verify Vision API rejects unauthorized and unauthenticated requests."""
        # Unauthenticated request (no user_id)
        resp = self.client.post('/api/analyze-food-image', json={'image': 'mock-base64'})
        self.assertEqual(resp.status_code, 403)

        # Unauthenticated request (with user_id but not logged in)
        resp = self.client.post('/api/analyze-food-image', json={'user_id': 9999, 'image': 'mock-base64'})
        self.assertEqual(resp.status_code, 403)

        # Authenticated request (valid user_id logged in)
        email = f"vision_{uuid.uuid4().hex[:8]}@example.com"
        acct_id, _ = register_account("Vision User", email, "Password123")
        user_id = save_user(self._create_user_data(email))
        from models.auth_model import link_user_to_account
        link_user_to_account(user_id, acct_id)

        with self.client.session_transaction() as sess:
            sess['account_id'] = acct_id

        # Make the request - should pass auth check and return 400 (Bad Request due to mock image) rather than 403
        resp = self.client.post('/api/analyze-food-image', json={'user_id': user_id, 'image': ''})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('No image provided', resp.get_json()['error'])

    def test_voice_log_api_auth_enforced(self):
        """Verify Voice log API rejects unauthorized and unauthenticated requests."""
        # Unauthenticated request (no user_id)
        resp = self.client.post('/api/voice-log', json={'transcript': 'ate an apple'})
        self.assertEqual(resp.status_code, 403)

        # Unauthenticated request (with user_id but not logged in)
        resp = self.client.post('/api/voice-log', json={'user_id': 9999, 'transcript': 'ate an apple'})
        self.assertEqual(resp.status_code, 403)

        # Authenticated request (valid user_id logged in)
        email = f"voice_{uuid.uuid4().hex[:8]}@example.com"
        acct_id, _ = register_account("Voice User", email, "Password123")
        user_id = save_user(self._create_user_data(email))
        from models.auth_model import link_user_to_account
        link_user_to_account(user_id, acct_id)

        with self.client.session_transaction() as sess:
            sess['account_id'] = acct_id

        # Make the request - should pass auth check and return 400 (no transcript) rather than 403
        resp = self.client.post('/api/voice-log', json={'user_id': user_id, 'transcript': ''})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('No transcript provided', resp.get_json()['error'])

    # ── 10. Account Lockout ──
    def test_account_lockout_after_10_attempts(self):
        """Verify that an account is locked after 10 failed login attempts, returning 429."""
        from app import _failed_logins
        from services.rate_limiter import _store
        
        # Clear rate limiter and failed login stores to ensure isolation
        _failed_logins.clear()
        if hasattr(_store, 'clear'):
            _store.clear()

        email = "lockout_test@example.com"
        
        # Register the user first so we are hitting a valid but wrong password scenario
        register_account("Lockout User", email, "ValidPassword123")
        
        # Perform 10 failed login attempts
        for i in range(10):
            # We must clear the rate limiter store on each iteration so that we don't hit the IP rate limit (max 10 in 5 min)
            if hasattr(_store, 'clear'):
                _store.clear()
            resp = self.client.post('/login', data={
                'email': email,
                'password': 'WrongPassword123'
            })
            if i < 9:
                self.assertEqual(resp.status_code, 200)  # Returns 200 with login form / error message
        
        # The 11th attempt should return 429
        if hasattr(_store, 'clear'):
            _store.clear()
        resp = self.client.post('/login', data={
            'email': email,
            'password': 'WrongPassword123'
        })
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Account temporarily locked", resp.get_data(as_text=True))
        
        # An attempt with the correct password should also be rejected
        if hasattr(_store, 'clear'):
            _store.clear()
        resp = self.client.post('/login', data={
            'email': email,
            'password': 'ValidPassword123'
        })
        self.assertEqual(resp.status_code, 429)

    # ── 11. Health Check Route ──
    def test_health_endpoint(self):
        """Verify the health check endpoint returns 200 and expected status fields."""
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertTrue(data.get('db'))
        self.assertIn('cache', data)
        self.assertEqual(data.get('rate_limits'), 'active')

    # ── 12. Anomaly Detection Scans ──
    @patch('app.sec_log')
    def test_anomaly_detection_suspicious_ua(self, mock_sec_log):
        """Verify that requests with suspicious User-Agents log anomalies."""
        self.client.get('/ping', headers={'User-Agent': 'sqlmap/1.4.5'})
        mock_sec_log.assert_called_with('ANOMALY', '127.0.0.1', {
            'path': '/ping',
            'flags': ['suspicious_ua:sqlmap/1.4.5']
        })

    @patch('app.sec_log')
    def test_anomaly_detection_missing_ua(self, mock_sec_log):
        """Verify that requests with missing User-Agent log anomalies."""
        self.client.get('/ping', headers={'User-Agent': ''})
        mock_sec_log.assert_called_with('ANOMALY', '127.0.0.1', {
            'path': '/ping',
            'flags': ['missing_ua']
        })

    @patch('app.sec_log')
    def test_anomaly_detection_long_voice_transcript(self, mock_sec_log):
        """Verify that abnormally long transcripts in voice logging trigger an anomaly."""
        email = f"voice_anon_{uuid.uuid4().hex[:8]}@example.com"
        acct_id, _ = register_account("Voice Anon", email, "Password123")
        user_id = save_user(self._create_user_data(email))
        from models.auth_model import link_user_to_account
        link_user_to_account(user_id, acct_id)

        with self.client.session_transaction() as sess:
            sess['account_id'] = acct_id

        long_transcript = "a" * 501
        self.client.post('/api/voice-log', json={
            'user_id': user_id,
            'transcript': long_transcript
        })
        
        called_args = [call[0] for call in mock_sec_log.call_args_list]
        anomaly_calls = [arg for arg in called_args if arg[0] == 'ANOMALY']
        self.assertTrue(len(anomaly_calls) > 0)
        flags = anomaly_calls[0][2]['flags']
        self.assertIn('long_transcript', flags)

    @patch('app.sec_log')
    def test_anomaly_detection_large_payload(self, mock_sec_log):
        """Verify that requests with large payloads log anomalies."""
        large_data = "x" * (1024 * 1024 + 10)
        self.client.post('/ping', data=large_data)
        
        called_args = [call[0] for call in mock_sec_log.call_args_list]
        anomaly_calls = [arg for arg in called_args if arg[0] == 'ANOMALY']
        self.assertTrue(len(anomaly_calls) > 0)
        flags = anomaly_calls[0][2]['flags']
        self.assertTrue(any(f.startswith('large_request:') for f in flags))

    # ── 13. Google OAuth ──
    def test_google_login_redirect(self):
        """Verify GET /login/google redirects correctly."""
        # Test mock mode (default when keys are unset)
        with patch('config.Config.GOOGLE_CLIENT_ID', ''), patch('config.Config.GOOGLE_CLIENT_SECRET', ''):
            resp = self.client.get('/login/google')
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Sign in with Google (Sandbox)", resp.get_data(as_text=True))
            
        # Test real mode
        with patch('config.Config.GOOGLE_CLIENT_ID', 'fake-client-id'), patch('config.Config.GOOGLE_CLIENT_SECRET', 'fake-client-secret'):
            resp = self.client.get('/login/google')
            self.assertEqual(resp.status_code, 302)
            self.assertIn("accounts.google.com", resp.headers.get('Location'))

    def test_google_login_callback_mock(self):
        """Verify /login/google/callback registers and logs in mock Google user."""
        with patch('config.Config.GOOGLE_CLIENT_ID', ''), patch('config.Config.GOOGLE_CLIENT_SECRET', ''):
            resp = self.client.get('/login/google/callback?code=mock-code-123')
            self.assertEqual(resp.status_code, 302)
            self.assertIn('/my-dashboard', resp.headers.get('Location'))
            
            # Verify user session is established
            with self.client.session_transaction() as sess:
                self.assertIsNotNone(sess.get('account_id'))
                self.assertEqual(sess.get('account_email'), 'google_test_user@example.com')
                self.assertEqual(sess.get('account_name'), 'Google Test User')

    # ── 14. Compliance Age Gating (DPDP) ──
    def test_compliance_age_gating_under_18(self):
        """Verify that questionnaire submissions with age < 18 are rejected under DPDP compliance rules."""
        data = self._create_user_data("minor@example.com")
        data['age'] = 17  # Under 18
        resp = self.client.post('/analyze', data=data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("You must be 18 years of age or older", resp.get_data(as_text=True))

    def test_compliance_age_gating_18_or_older(self):
        """Verify that questionnaire submissions with age >= 18 are processed normally."""
        data = self._create_user_data("adult@example.com")
        data['age'] = 18  # Exactly 18
        resp = self.client.post('/analyze', data=data)
        self.assertNotEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
