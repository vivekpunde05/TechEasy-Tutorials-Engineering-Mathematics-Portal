import unittest
import time
from app import create_app
from database import query_db, execute_db

class EngineeringMathsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_homepage_unauthenticated(self):
        """Test home page when not logged in only gives login options for student and admin, and register for new students."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Student Login', res.data)
        self.assertIn(b'Admin Login', res.data)
        self.assertIn(b'Register here', res.data)

    def test_student_registration_with_stream(self):
        """Test student registration requires choosing Diploma or Degree."""
        ts = int(time.time() * 1000)
        # Register a diploma student
        res_dip = self.client.post('/student/register', data={
            'name': 'Diploma Student Test',
            'email': f'dip_test_{ts}@example.com',
            'mobile': f'9{(ts % 1000000000):09d}',
            'course_type': 'Diploma',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res_dip.status_code, 200)

        user = query_db("SELECT * FROM users WHERE email = ?", (f'dip_test_{ts}@example.com',), one=True)
        self.assertIsNotNone(user)
        self.assertEqual(user['course_type'], 'Diploma')

    def test_degree_student_isolation(self):
        """Test degree student only sees Degree info and cannot access Diploma subjects."""
        # Login as Degree student
        res = self.client.post('/student/login', data={
            'email': 'student@techeasy.com',
            'password': 'student123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Degree', res.data)

        # Allowed: Degree subjects
        res_deg = self.client.get('/student/degree')
        self.assertEqual(res_deg.status_code, 200)
        self.assertIn(b'Degree Engineering Mathematics', res_deg.data)

        # Blocked: Diploma subjects redirects with restriction
        res_dip = self.client.get('/student/diploma', follow_redirects=True)
        self.assertIn(b'Degree student', res_dip.data)

    def test_diploma_student_isolation(self):
        """Test diploma student only sees Diploma info and cannot access Degree subjects."""
        # Login as Diploma student
        res = self.client.post('/student/login', data={
            'email': 'diploma@techeasy.com',
            'password': 'diploma123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Diploma', res.data)

        # Allowed: Diploma subjects
        res_dip = self.client.get('/student/diploma')
        self.assertEqual(res_dip.status_code, 200)
        self.assertIn(b'Diploma Engineering Mathematics', res_dip.data)

        # Blocked: Degree subjects redirects with restriction
        res_deg = self.client.get('/student/degree', follow_redirects=True)
        self.assertIn(b'Diploma student', res_deg.data)

    def test_admin_has_all_permissions(self):
        """Test admin can manage everything across all streams and view students."""
        res = self.client.post('/admin/login', data={
            'email': 'admin@techeasy.com',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Admin Dashboard', res.data)

        # Admin can view students management
        res_stud = self.client.get('/admin/students')
        self.assertEqual(res_stud.status_code, 200)
        self.assertIn(b'Registered Students', res_stud.data)

        # Admin can view both Degree and Diploma subjects
        self.assertEqual(self.client.get('/student/degree').status_code, 200)
        self.assertEqual(self.client.get('/student/diploma').status_code, 200)

    def test_practice_submission(self):
        """Test submitting chapter practice test and viewing result."""
        self.client.post('/student/login', data={'email': 'student@techeasy.com', 'password': 'student123'})
        subject = query_db("SELECT id FROM subjects WHERE course_type = 'Degree' LIMIT 1", one=True)
        chapter = query_db("SELECT id FROM chapters WHERE subject_id = ? LIMIT 1", (subject['id'],), one=True)
        questions = query_db("SELECT id, correct_answer FROM questions WHERE subject_id = ? AND chapter_id = ?", (subject['id'], chapter['id']))

        post_data = {
            'subject_id': subject['id'],
            'chapter_id': chapter['id']
        }
        for q in questions:
            post_data[f"answer_{q['id']}"] = q['correct_answer']

        res = self.client.post('/student/practice', data=post_data)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Practice Evaluation Complete', res.data)

    def test_mock_test_cbt_flow(self):
        """Test taking and submitting a full-length CBT mock test matching student stream."""
        ts = int(time.time() * 1000)
        email = f"cbt_candidate_{ts}@example.com"
        mobile = f"9{(ts % 1000000000):09d}"
        reg_res = self.client.post('/student/register', data={
            'name': 'CBT Candidate',
            'email': email,
            'mobile': mobile,
            'course_type': 'Degree',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)

        # Create a dedicated mock test for Degree
        subject = query_db("SELECT id FROM subjects WHERE course_type = 'Degree' LIMIT 1", one=True)
        test_id, _ = execute_db("""
            INSERT INTO tests (test_name, course_type, subject_id, number_of_questions, time_limit)
            VALUES (?, 'Degree', ?, 1, 30)
        """, (f"Test Paper {ts}", subject['id']))

        q = query_db("SELECT id FROM questions WHERE subject_id = ? LIMIT 1", (subject['id'],), one=True)
        if q:
            execute_db("INSERT INTO test_questions (test_id, question_id) VALUES (?, ?)", (test_id, q['id']))

        # Load take-test page
        res_take = self.client.get(f"/student/take-test/{test_id}")
        self.assertEqual(res_take.status_code, 200)
        self.assertIn(b'Question Palette', res_take.data)

        # Submit test answers
        post_data = {'started_at': '2026-10-15 12:00:00'}
        if q:
            post_data[f"answer_{q['id']}"] = 'A'

        res_submit = self.client.post(f"/student/take-test/{test_id}", data=post_data, follow_redirects=True)
        self.assertEqual(res_submit.status_code, 200)
        self.assertIn(b'Mock Test Results', res_submit.data)

    def test_api_chapters(self):
        """Test /api/chapters endpoint returns valid JSON."""
        subjects = query_db("SELECT id FROM subjects LIMIT 1")
        if subjects:
            s_id = subjects[0]['id']
            res = self.client.get(f'/api/chapters?subject_id={s_id}')
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.is_json)

    def test_admin_dashboard_four_sessions(self):
        """Test admin dashboard contains 4 sessions (Home, Degree, Diploma, Students) and enforces stream student filtering."""
        # Login as admin
        self.client.post('/admin/login', data={'email': 'admin@techeasy.com', 'password': 'admin123'})

        # 1. Home session
        res_home = self.client.get('/admin/dashboard?tab=home')
        self.assertEqual(res_home.status_code, 200)
        self.assertIn(b'Curriculum & Examination Overview', res_home.data)

        # 2. Degree session
        res_deg = self.client.get('/admin/dashboard?tab=degree')
        self.assertEqual(res_deg.status_code, 200)
        self.assertIn(b'Degree Administrative Sections', res_deg.data)

        # 3. Diploma session
        res_dip = self.client.get('/admin/dashboard?tab=diploma')
        self.assertEqual(res_dip.status_code, 200)
        self.assertIn(b'Diploma Administrative Sections', res_dip.data)

        # 4. Students session: Degree selected -> only Degree students
        res_stu_deg = self.client.get('/admin/dashboard?tab=students&student_stream=Degree')
        self.assertEqual(res_stu_deg.status_code, 200)
        self.assertIn(b'student@techeasy.com', res_stu_deg.data)
        self.assertNotIn(b'diploma@techeasy.com', res_stu_deg.data)

        # 5. Students session: Diploma selected -> only Diploma students
        res_stu_dip = self.client.get('/admin/dashboard?tab=students&student_stream=Diploma')
        self.assertEqual(res_stu_dip.status_code, 200)
        self.assertIn(b'diploma@techeasy.com', res_stu_dip.data)
        self.assertNotIn(b'student@techeasy.com', res_stu_dip.data)

    def test_stream_isolated_add_subject(self):
        """Test adding subject from Degree and Diploma does not require selecting course stream."""
        self.client.post('/admin/login', data={'email': 'admin@techeasy.com', 'password': 'admin123'})

        # Degree subjects page does NOT contain course_type dropdown
        res_deg = self.client.get('/admin/subjects?stream=Degree')
        self.assertEqual(res_deg.status_code, 200)
        self.assertNotIn(b'<select name="course_type"', res_deg.data)
        self.assertIn(b'+ Add Degree Subject', res_deg.data)

        # Diploma subjects page does NOT contain course_type dropdown
        res_dip = self.client.get('/admin/subjects?stream=Diploma')
        self.assertEqual(res_dip.status_code, 200)
        self.assertNotIn(b'<select name="course_type"', res_dip.data)
        self.assertIn(b'+ Add Diploma Subject', res_dip.data)

        # Add Degree subject directly with stream pre-set
        ts = int(time.time() * 1000)
        sub_deg_name = f"Degree Subject {ts}"
        post_deg = self.client.post('/admin/subjects?stream=Degree', data={
            'action': 'add',
            'course_type': 'Degree',
            'semester': 'Semester 1',
            'subject_name': sub_deg_name
        }, follow_redirects=True)
        self.assertEqual(post_deg.status_code, 200)
        deg_sub = query_db("SELECT * FROM subjects WHERE subject_name = ?", (sub_deg_name,), one=True)
        self.assertIsNotNone(deg_sub)
        self.assertEqual(deg_sub['course_type'], 'Degree')

        # Add Diploma subject directly with stream pre-set
        sub_dip_name = f"Diploma Subject {ts}"
        post_dip = self.client.post('/admin/subjects?stream=Diploma', data={
            'action': 'add',
            'course_type': 'Diploma',
            'semester': 'Semester 1',
            'subject_name': sub_dip_name
        }, follow_redirects=True)
        self.assertEqual(post_dip.status_code, 200)
        dip_sub = query_db("SELECT * FROM subjects WHERE subject_name = ?", (sub_dip_name,), one=True)
        self.assertIsNotNone(dip_sub)
        self.assertEqual(dip_sub['course_type'], 'Diploma')

    def test_stream_isolated_manage_chapters(self):
        """Test manage chapters only shows Degree subjects in Degree session, and Diploma subjects in Diploma session."""
        self.client.post('/admin/login', data={'email': 'admin@techeasy.com', 'password': 'admin123'})

        # Degree chapters view
        res_deg = self.client.get('/admin/chapters?stream=Degree')
        self.assertEqual(res_deg.status_code, 200)
        self.assertIn(b'Degree Engineering Chapters', res_deg.data)
        self.assertIn(b'Engineering Mathematics - I', res_deg.data)
        self.assertNotIn(b'Basic Mathematics (Diploma M1)', res_deg.data)

        # Diploma chapters view
        res_dip = self.client.get('/admin/chapters?stream=Diploma')
        self.assertEqual(res_dip.status_code, 200)
        self.assertIn(b'Diploma Polytechnic Chapters', res_dip.data)
        self.assertIn(b'Basic Mathematics (Diploma M1)', res_dip.data)
        self.assertNotIn(b'Engineering Mathematics - I', res_dip.data)

    def test_stream_isolated_questions(self):
        """Test MCQ Question Bank isolates questions and subjects by stream."""
        self.client.post('/admin/login', data={'email': 'admin@techeasy.com', 'password': 'admin123'})

        # Degree MCQs view
        res_deg = self.client.get('/admin/questions?stream=Degree')
        self.assertEqual(res_deg.status_code, 200)
        self.assertIn(b'MCQ Question Bank', res_deg.data)
        self.assertNotIn(b'Degree Engineering MCQ Question Bank', res_deg.data)
        self.assertIn(b'+ Add New MCQ', res_deg.data)
        self.assertIn(b'Engineering Mathematics - I', res_deg.data)
        self.assertNotIn(b'Basic Mathematics (Diploma M1)', res_deg.data)

        # Diploma MCQs view
        res_dip = self.client.get('/admin/questions?stream=Diploma')
        self.assertEqual(res_dip.status_code, 200)
        self.assertIn(b'MCQ Question Bank', res_dip.data)
        self.assertNotIn(b'Diploma Polytechnic MCQ Question Bank', res_dip.data)
        self.assertIn(b'+ Add New MCQ', res_dip.data)
        self.assertIn(b'Basic Mathematics (Diploma M1)', res_dip.data)
        self.assertNotIn(b'Engineering Mathematics - I', res_dip.data)

    def test_stream_isolated_mock_tests(self):
        """Test Manage Mock Tests removes course stream dropdown and isolates subjects and tests by stream."""
        self.client.post('/admin/login', data={'email': 'admin@techeasy.com', 'password': 'admin123'})

        # Degree tests view
        res_deg = self.client.get('/admin/tests?stream=Degree')
        self.assertEqual(res_deg.status_code, 200)
        self.assertIn(b'Manage Degree Mock Tests', res_deg.data)
        self.assertNotIn(b'<select name="course_type"', res_deg.data)
        self.assertNotIn(b'Course Stream', res_deg.data)
        self.assertIn(b'Engineering Mathematics - I', res_deg.data)
        self.assertNotIn(b'Basic Mathematics (Diploma M1)', res_deg.data)

        # Diploma tests view
        res_dip = self.client.get('/admin/tests?stream=Diploma')
        self.assertEqual(res_dip.status_code, 200)
        self.assertIn(b'Manage Diploma Mock Tests', res_dip.data)
        self.assertNotIn(b'<select name="course_type"', res_dip.data)
        self.assertNotIn(b'Course Stream', res_dip.data)
        self.assertIn(b'Basic Mathematics (Diploma M1)', res_dip.data)
        self.assertNotIn(b'Engineering Mathematics - I', res_dip.data)

        # Add test in Degree session automatically sets Degree stream
        ts = int(time.time() * 1000)
        deg_sub = query_db("SELECT id FROM subjects WHERE course_type = 'Degree' LIMIT 1", one=True)
        deg_test_name = f"Degree Unit Mock {ts}"
        post_deg = self.client.post('/admin/tests?stream=Degree', data={
            'action': 'add',
            'test_name': deg_test_name,
            'subject_id': deg_sub['id'],
            'time_limit': 45
        }, follow_redirects=True)
        self.assertEqual(post_deg.status_code, 200)
        created_deg = query_db("SELECT * FROM tests WHERE test_name = ?", (deg_test_name,), one=True)
        self.assertIsNotNone(created_deg)
        self.assertEqual(created_deg['course_type'], 'Degree')

        # Add test in Diploma session automatically sets Diploma stream
        dip_sub = query_db("SELECT id FROM subjects WHERE course_type = 'Diploma' LIMIT 1", one=True)
        dip_test_name = f"Diploma Unit Mock {ts}"
        post_dip = self.client.post('/admin/tests?stream=Diploma', data={
            'action': 'add',
            'test_name': dip_test_name,
            'subject_id': dip_sub['id'],
            'time_limit': 40
        }, follow_redirects=True)
        self.assertEqual(post_dip.status_code, 200)
        created_dip = query_db("SELECT * FROM tests WHERE test_name = ?", (dip_test_name,), one=True)
        self.assertIsNotNone(created_dip)
        self.assertEqual(created_dip['course_type'], 'Diploma')

    def test_stream_isolated_practice_results(self):
        """Test Evaluation Scores only shows Degree students in Degree session, and Diploma students in Diploma session."""
        self.client.post('/admin/login', data={'email': 'admin@techeasy.com', 'password': 'admin123'})

        # Insert a sample practice evaluation for Diploma student if needed
        dip_user = query_db("SELECT id, name FROM users WHERE course_type = 'Diploma' AND role = 'student' LIMIT 1", one=True)
        dip_sub = query_db("SELECT id FROM subjects WHERE course_type = 'Diploma' LIMIT 1", one=True)
        if dip_user and dip_sub:
            execute_db("""
                INSERT INTO test_results (student_id, subject_id, chapter_id, total_questions, score, correct_answers, wrong_answers, percentage)
                VALUES (?, ?, NULL, 10, 8, 8, 2, 80.0)
            """, (dip_user['id'], dip_sub['id']))

        # Degree practice results
        res_deg = self.client.get('/admin/practice-results?stream=Degree')
        self.assertEqual(res_deg.status_code, 200)
        self.assertIn(b'Degree Practice Evaluation Scores', res_deg.data)
        self.assertIn(b'Vivek Sharma', res_deg.data)
        if dip_user:
            self.assertNotIn(dip_user['name'].encode('utf-8'), res_deg.data)

        # Diploma practice results
        res_dip = self.client.get('/admin/practice-results?stream=Diploma')
        self.assertEqual(res_dip.status_code, 200)
        self.assertIn(b'Diploma Practice Evaluation Scores', res_dip.data)
        self.assertNotIn(b'Vivek Sharma', res_dip.data)
        if dip_user:
            self.assertIn(dip_user['name'].encode('utf-8'), res_dip.data)

    def test_stream_isolated_video_lectures(self):
        """Test Manage Video Lectures automatically uses stream Degree for degree session, and Diploma for diploma session."""
        self.client.post('/admin/login', data={'email': 'admin@techeasy.com', 'password': 'admin123'})

        # Degree video lectures view
        res_deg = self.client.get('/admin/video-lectures?stream=Degree')
        self.assertEqual(res_deg.status_code, 200)
        self.assertIn(b'Manage Degree Video Lectures', res_deg.data)
        self.assertNotIn(b'<select name="course_type"', res_deg.data)

        # Diploma video lectures view
        res_dip = self.client.get('/admin/video-lectures?stream=Diploma')
        self.assertEqual(res_dip.status_code, 200)
        self.assertIn(b'Manage Diploma Video Lectures', res_dip.data)
        self.assertNotIn(b'<select name="course_type"', res_dip.data)

        # Add Degree video lecture
        ts = int(time.time() * 1000)
        deg_link = f"https://www.youtube.com/watch?v=deg_{ts}"
        deg_desc = f"Degree Lecture {ts}"
        post_deg = self.client.post('/admin/video-lectures?stream=Degree', data={
            'action': 'add',
            'youtube_link': deg_link,
            'description': deg_desc
        }, follow_redirects=True)
        self.assertEqual(post_deg.status_code, 200)
        vid_deg = query_db("SELECT * FROM video_lectures WHERE youtube_link = ?", (deg_link,), one=True)
        self.assertIsNotNone(vid_deg)
        self.assertEqual(vid_deg['course_type'], 'Degree')

        # Add Diploma video lecture
        dip_link = f"https://www.youtube.com/watch?v=dip_{ts}"
        dip_desc = f"Diploma Lecture {ts}"
        post_dip = self.client.post('/admin/video-lectures?stream=Diploma', data={
            'action': 'add',
            'youtube_link': dip_link,
            'description': dip_desc
        }, follow_redirects=True)
        self.assertEqual(post_dip.status_code, 200)
        vid_dip = query_db("SELECT * FROM video_lectures WHERE youtube_link = ?", (dip_link,), one=True)
        self.assertIsNotNone(vid_dip)
        self.assertEqual(vid_dip['course_type'], 'Diploma')

        # Verify Degree view has Degree lecture and NOT Diploma lecture
        view_deg = self.client.get('/admin/video-lectures?stream=Degree')
        self.assertIn(deg_desc.encode('utf-8'), view_deg.data)
        self.assertNotIn(dip_desc.encode('utf-8'), view_deg.data)

        # Verify Diploma view has Diploma lecture and NOT Degree lecture
        view_dip = self.client.get('/admin/video-lectures?stream=Diploma')
        self.assertIn(dip_desc.encode('utf-8'), view_dip.data)
        self.assertNotIn(deg_desc.encode('utf-8'), view_dip.data)

    def test_password_visibility_toggle(self):
        """Test password visibility toggle buttons exist on home login, dedicated student/admin login, and register pages."""
        # 1. Home page (both student and admin login cards)
        res_home = self.client.get('/')
        self.assertEqual(res_home.status_code, 200)
        self.assertIn(b"togglePasswordVisibility('student_password'", res_home.data)
        self.assertIn(b"togglePasswordVisibility('admin_password'", res_home.data)
        self.assertIn(b"password-toggle-btn", res_home.data)

        # 2. Dedicated Student Login page
        res_stud = self.client.get('/student/login')
        self.assertEqual(res_stud.status_code, 200)
        self.assertIn(b"togglePasswordVisibility('password'", res_stud.data)

        # 3. Dedicated Admin Login page
        res_admin = self.client.get('/admin/login')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b"togglePasswordVisibility('password'", res_admin.data)

        # 4. Student Registration page
        res_reg = self.client.get('/student/register')
        self.assertEqual(res_reg.status_code, 200)
        self.assertIn(b"togglePasswordVisibility('password'", res_reg.data)
        self.assertIn(b"togglePasswordVisibility('confirm_password'", res_reg.data)

    def test_student_mock_tests_isolation(self):
        """Test student mock tests page strictly isolates Degree tests/subjects from Diploma tests/subjects."""
        # 1. Degree Student
        self.client.get('/logout')
        self.client.post('/student/login', data={'email': 'student@techeasy.com', 'password': 'student123'}, follow_redirects=True)
        res_deg = self.client.get('/student/mock-tests')
        self.assertEqual(res_deg.status_code, 200)
        self.assertIn(b'Degree Engineering Mathematics Mock Tests', res_deg.data)
        self.assertIn(b'Engineering Mathematics - I', res_deg.data)
        self.assertNotIn(b'Diploma Tests', res_deg.data)
        self.assertNotIn(b'Basic Mathematics (Diploma M1)', res_deg.data)
        self.assertNotIn(b'Applied Mathematics (Diploma M2)', res_deg.data)

        # 2. Diploma Student
        self.client.get('/logout')
        self.client.post('/student/login', data={'email': 'diploma@techeasy.com', 'password': 'diploma123'}, follow_redirects=True)
        res_dip = self.client.get('/student/mock-tests')
        self.assertEqual(res_dip.status_code, 200)
        self.assertIn(b'Diploma Engineering Mathematics Mock Tests', res_dip.data)
        self.assertNotIn(b'Degree Tests', res_dip.data)
        self.assertNotIn(b'Engineering Mathematics - I', res_dip.data)

    def test_student_video_lectures_isolation(self):
        """Test student video lectures page strictly isolates Degree videos from Diploma videos and removes cross-stream tabs."""
        # 1. Degree Student
        self.client.get('/logout')
        self.client.post('/student/login', data={'email': 'student@techeasy.com', 'password': 'student123'}, follow_redirects=True)
        res_deg = self.client.get('/student/video-lectures')
        self.assertEqual(res_deg.status_code, 200)
        self.assertIn(b'Degree Mathematics Video Lectures', res_deg.data)
        self.assertIn(b'Eigenvalues and Eigenvectors', res_deg.data)
        self.assertNotIn(b'>Diploma<', res_deg.data)
        self.assertNotIn(b'>All<', res_deg.data)
        self.assertNotIn(b'Diploma Maths - Integration', res_deg.data)

        # 2. Diploma Student
        self.client.get('/logout')
        self.client.post('/student/login', data={'email': 'diploma@techeasy.com', 'password': 'diploma123'}, follow_redirects=True)
        res_dip = self.client.get('/student/video-lectures')
        self.assertEqual(res_dip.status_code, 200)
        self.assertIn(b'Diploma Mathematics Video Lectures', res_dip.data)
        self.assertIn(b'Diploma Maths - Integration', res_dip.data)
        self.assertNotIn(b'>Degree<', res_dip.data)
        self.assertNotIn(b'>All<', res_dip.data)
        self.assertNotIn(b'Eigenvalues and Eigenvectors', res_dip.data)

    def test_mock_test_results_student_isolation(self):
        """Test mock test results only show details of students enrolled in that test's stream."""
        deg_user = query_db("SELECT id, name, email FROM users WHERE email = 'student@techeasy.com'", one=True)
        dip_user = query_db("SELECT id, name, email FROM users WHERE email = 'diploma@techeasy.com'", one=True)
        deg_test = query_db("SELECT id FROM tests WHERE course_type = 'Degree' LIMIT 1", one=True)
        dip_test = query_db("SELECT id FROM tests WHERE course_type = 'Diploma' LIMIT 1", one=True)

        # Insert attempts
        if deg_test and deg_user:
            execute_db("""
                INSERT OR REPLACE INTO attempts (user_id, test_id, score, total_questions, percentage)
                VALUES (?, ?, 10, 10, 100.0)
            """, (deg_user['id'], deg_test['id']))
        if deg_test and dip_user:
            execute_db("""
                INSERT OR REPLACE INTO attempts (user_id, test_id, score, total_questions, percentage)
                VALUES (?, ?, 8, 10, 80.0)
            """, (dip_user['id'], deg_test['id']))

        if dip_test and dip_user:
            execute_db("""
                INSERT OR REPLACE INTO attempts (user_id, test_id, score, total_questions, percentage)
                VALUES (?, ?, 9, 10, 90.0)
            """, (dip_user['id'], dip_test['id']))
        if dip_test and deg_user:
            execute_db("""
                INSERT OR REPLACE INTO attempts (user_id, test_id, score, total_questions, percentage)
                VALUES (?, ?, 7, 10, 70.0)
            """, (deg_user['id'], dip_test['id']))

        # 1. Admin checks Degree mock test results
        self.client.get('/logout')
        self.client.post('/admin/login', data={'email': 'admin@techeasy.com', 'password': 'admin123'}, follow_redirects=True)
        res_deg = self.client.get(f"/admin/tests/{deg_test['id']}/results")
        self.assertEqual(res_deg.status_code, 200)
        self.assertIn(deg_user['name'].encode('utf-8'), res_deg.data)
        self.assertNotIn(dip_user['name'].encode('utf-8'), res_deg.data)

        # 2. Admin checks Diploma mock test results
        res_dip = self.client.get(f"/admin/tests/{dip_test['id']}/results")
        self.assertEqual(res_dip.status_code, 200)
        self.assertIn(dip_user['name'].encode('utf-8'), res_dip.data)
        self.assertNotIn(deg_user['name'].encode('utf-8'), res_dip.data)

        # 3. Student views their mock test results
        self.client.get('/logout')
        self.client.post('/student/login', data={'email': 'student@techeasy.com', 'password': 'student123'}, follow_redirects=True)
        res_stud_deg = self.client.get('/student/mock-test-results')
        self.assertEqual(res_stud_deg.status_code, 200)
        self.assertIn(b'My Degree Mock Test Results', res_stud_deg.data)

        self.client.get('/logout')
        self.client.post('/student/login', data={'email': 'diploma@techeasy.com', 'password': 'diploma123'}, follow_redirects=True)
        res_stud_dip = self.client.get('/student/mock-test-results')
        self.assertEqual(res_stud_dip.status_code, 200)
        self.assertIn(b'My Diploma Mock Test Results', res_stud_dip.data)

    def test_student_dashboard_home_basic_info_only(self):
        """Test student dashboard home displays only basic student info and excludes removed sections."""
        self.client.get('/logout')
        self.client.post('/student/login', data={'email': 'student@techeasy.com', 'password': 'student123'}, follow_redirects=True)

        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)

        # Basic student information is present
        self.assertIn(b'Basic Student Information', res.data)
        self.assertIn(b'student@techeasy.com', res.data)
        self.assertIn(b'Degree Engineering', res.data)
        self.assertIn(b'Mobile Number', res.data)

        # Removed sections are NOT present
        self.assertNotIn(b'My Degree Subjects', res.data)
        self.assertNotIn(b'Degree Examination Mock Tests', res.data)
        self.assertNotIn(b'Degree Video Tutorials', res.data)
        self.assertNotIn(b'My Recent Exam Submissions', res.data)
        self.assertNotIn(b'\xf0\x9f\x93\x96 Subjects', res.data)
        self.assertNotIn(b'\xe2\x8f\xb1\xef\xb8\x8f Mock Tests', res.data)
        self.assertNotIn(b'\xf0\x9f\x8e\xa5 Videos', res.data)
        self.assertNotIn(b'\xf0\x9f\x93\x8a My Results', res.data)

if __name__ == '__main__':
    unittest.main()

