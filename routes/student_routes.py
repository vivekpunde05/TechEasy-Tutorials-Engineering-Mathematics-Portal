from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, abort
from routes import student_bp
from routes.auth_routes import student_required
from database import query_db, execute_db, extract_youtube_id

# ==================== HOME / LANDING PAGE ====================

# ==================== HOME / LANDING PAGE ====================

@student_bp.route('/')
@student_bp.route('/index')
def index():
    student_id = session.get('student_id')
    admin_id = session.get('admin_id')

    # If Admin is logged in, redirect to admin dashboard or show full portal
    if admin_id:
        return redirect(url_for('admin.dashboard'))

    # If Student is logged in, show their basic information dashboard
    if student_id:
        student = query_db("""
            SELECT id, name, email, mobile, role, course_type, created_at
            FROM users
            WHERE id = ?
        """, (student_id,), one=True)

        student_stream = student.get('course_type', 'Degree') if student else session.get('student_course_type', 'Degree')

        return render_template(
            'student/dashboard.html',
            stream=student_stream,
            student=student
        )

    # When NOT logged in: First page shows ONLY login / register / portal options in clean sections
    return render_template('index.html')

# ==================== DIPLOMA & DEGREE SUBJECTS ====================

@student_bp.route('/student/diploma')
@student_required
def diploma_subjects():
    if not session.get('admin_id'):
        student_stream = session.get('student_course_type', 'Degree')
        if student_stream != 'Diploma':
            flash("You are registered as a Degree student. Access is restricted to Degree Engineering Mathematics.", "warning")
            return redirect(url_for('student.degree_subjects'))

    subjects = query_db("""
        SELECT s.*, 
            COUNT(DISTINCT c.id) as chapter_count,
            COUNT(DISTINCT q.id) as question_count
        FROM subjects s
        LEFT JOIN chapters c ON s.id = c.subject_id
        LEFT JOIN questions q ON s.id = q.subject_id
        WHERE s.course_type = 'Diploma'
        GROUP BY s.id
        ORDER BY s.semester, s.subject_name
    """)
    return render_template('student/subjects.html', course_type='Diploma', subjects=subjects)

@student_bp.route('/student/degree')
@student_required
def degree_subjects():
    if not session.get('admin_id'):
        student_stream = session.get('student_course_type', 'Degree')
        if student_stream != 'Degree':
            flash("You are registered as a Diploma student. Access is restricted to Diploma Engineering Mathematics.", "warning")
            return redirect(url_for('student.diploma_subjects'))

    subjects = query_db("""
        SELECT s.*, 
            COUNT(DISTINCT c.id) as chapter_count,
            COUNT(DISTINCT q.id) as question_count
        FROM subjects s
        LEFT JOIN chapters c ON s.id = c.subject_id
        LEFT JOIN questions q ON s.id = q.subject_id
        WHERE s.course_type = 'Degree'
        GROUP BY s.id
        ORDER BY s.semester, s.subject_name
    """)
    return render_template('student/subjects.html', course_type='Degree', subjects=subjects)

# ==================== CHAPTER PRACTICE MCQs ====================

@student_bp.route('/student/practice', methods=['GET', 'POST'])
@student_required
def practice():
    subject_id = request.args.get('subject_id', type=int) or request.form.get('subject_id', type=int)
    if not subject_id:
        flash("Please select a subject to practice.", "warning")
        return redirect(url_for('student.degree_subjects'))

    subject = query_db("SELECT * FROM subjects WHERE id = ?", (subject_id,), one=True)
    if not subject:
        flash("Subject not found.", "danger")
        return redirect(url_for('student.index'))

    # Check subject stream matches student's registered stream (admin has super permission)
    if not session.get('admin_id'):
        student_stream = session.get('student_course_type', 'Degree')
        if subject['course_type'] != student_stream:
            flash(f"This subject belongs to the {subject['course_type']} stream. Your account is registered in {student_stream}.", "warning")
            return redirect(url_for('student.diploma_subjects' if student_stream == 'Diploma' else 'student.degree_subjects'))

    chapters = query_db("""
        SELECT c.*, COUNT(q.id) as question_count 
        FROM chapters c
        LEFT JOIN questions q ON c.id = q.chapter_id
        WHERE c.subject_id = ?
        GROUP BY c.id
        ORDER BY c.id
    """, (subject_id,))

    chapter_id = request.args.get('chapter_id', type=int) or request.form.get('chapter_id', type=int)
    questions = []
    current_chapter = None

    if chapter_id:
        current_chapter = query_db("SELECT * FROM chapters WHERE id = ? AND subject_id = ?", (chapter_id, subject_id), one=True)
        if current_chapter:
            questions = query_db("SELECT * FROM questions WHERE subject_id = ? AND chapter_id = ? ORDER BY id", (subject_id, chapter_id))

    # Handle submission of practice test
    if request.method == 'POST' and questions:
        student_id = session['student_id']
        total = len(questions)
        correct = 0
        wrong = 0
        unattempted = 0
        user_answers = {}

        for q in questions:
            qid = str(q['id'])
            selected = request.form.get(f'answer_{qid}', '').strip().upper()
            user_answers[q['id']] = selected

            if not selected:
                unattempted += 1
            elif selected == q['correct_answer'].strip().upper():
                correct += 1
            else:
                wrong += 1

        score = correct
        percentage = round((correct / total) * 100, 2) if total > 0 else 0.0

        # Save to database
        execute_db("""
            INSERT INTO test_results 
            (student_id, subject_id, chapter_id, total_questions, correct_answers, wrong_answers, score, percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (student_id, subject_id, chapter_id, total, correct, wrong, score, percentage))

        return render_template(
            'student/practice_result.html',
            subject=subject,
            chapter=current_chapter,
            questions=questions,
            user_answers=user_answers,
            total=total,
            correct=correct,
            wrong=wrong,
            unattempted=unattempted,
            score=score,
            percentage=percentage
        )

    return render_template(
        'student/practice.html',
        subject=subject,
        chapters=chapters,
        current_chapter=current_chapter,
        questions=questions,
        selected_chapter_id=chapter_id
    )

# ==================== MOCK TESTS ====================

@student_bp.route('/student/mock-tests')
@student_required
def mock_tests():
    # Enforce student's registered stream: only show Diploma tests to Diploma students, Degree tests to Degree students
    if session.get('admin_id'):
        course_type = request.args.get('course_type', session.get('student_course_type', 'Degree'))
        if course_type not in ['Degree', 'Diploma']:
            course_type = 'Degree'
    else:
        course_type = session.get('student_course_type', 'Degree')

    student_id = session['student_id']

    tests = query_db("""
        SELECT t.*, s.subject_name,
            (SELECT id FROM attempts WHERE user_id = ? AND test_id = t.id LIMIT 1) as attempt_id,
            (SELECT score FROM attempts WHERE user_id = ? AND test_id = t.id LIMIT 1) as attempt_score,
            (SELECT percentage FROM attempts WHERE user_id = ? AND test_id = t.id LIMIT 1) as attempt_percentage
        FROM tests t
        INNER JOIN subjects s ON t.subject_id = s.id
        WHERE t.course_type = ? AND s.course_type = ?
        ORDER BY t.created_at DESC
    """, (student_id, student_id, student_id, course_type, course_type))

    return render_template('student/mock_tests.html', course_type=course_type, tests=tests)

@student_bp.route('/student/take-test/<int:test_id>', methods=['GET', 'POST'])
@student_required
def take_test(test_id):
    student_id = session['student_id']
    student_stream = session.get('student_course_type', 'Degree')

    # 1. Get test details
    test = query_db("""
        SELECT t.*, s.subject_name 
        FROM tests t
        INNER JOIN subjects s ON t.subject_id = s.id
        WHERE t.id = ?
    """, (test_id,), one=True)

    if not test:
        flash("Mock Test not found.", "danger")
        return redirect(url_for('student.mock_tests'))

    # 2. Check stream match (admin can access both streams)
    if not session.get('admin_id') and test['course_type'] != student_stream:
        flash(f"Access Denied: This test is designed exclusively for {test['course_type']} students.", "danger")
        return redirect(url_for('student.mock_tests'))

    # 3. Check if already attempted
    existing_attempt = query_db("""
        SELECT * FROM attempts WHERE user_id = ? AND test_id = ? LIMIT 1
    """, (student_id, test_id), one=True)

    if existing_attempt:
        flash("You have already completed this Mock Test. Each test allows only one attempt.", "info")
        return redirect(url_for('student.mock_test_results'))

    # 4. Get questions assigned to this test
    questions = query_db("""
        SELECT q.* 
        FROM test_questions tq
        INNER JOIN questions q ON tq.question_id = q.id
        WHERE tq.test_id = ?
        ORDER BY tq.id ASC
    """, (test_id,))

    if not questions:
        flash("This test currently has no questions assigned.", "warning")
        return redirect(url_for('student.mock_tests', course_type=test['course_type']))

    # 5. Handle Submission
    if request.method == 'POST':
        # Check again to avoid double submit
        double_check = query_db("SELECT id FROM attempts WHERE user_id = ? AND test_id = ?", (student_id, test_id), one=True)
        if double_check:
            return redirect(url_for('student.mock_test_results'))

        total_questions = len(questions)
        score = 0
        started_at = request.form.get('started_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Grade answers
        answer_records = []
        for q in questions:
            qid = str(q['id'])
            selected = request.form.get(f'answer_{qid}', '').strip().upper()
            is_correct = 1 if (selected and selected == q['correct_answer'].strip().upper()) else 0
            if is_correct:
                score += 1
            answer_records.append((q['id'], selected, is_correct))

        percentage = round((score / total_questions) * 100, 2) if total_questions > 0 else 0.0

        # Insert attempt
        attempt_id, _ = execute_db("""
            INSERT INTO attempts (user_id, test_id, score, total_questions, percentage, started_at, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (student_id, test_id, score, total_questions, percentage, started_at, submitted_at))

        # Insert answer records
        for q_id, sel, corr in answer_records:
            execute_db("""
                INSERT INTO attempt_answers (attempt_id, question_id, selected_answer, is_correct)
                VALUES (?, ?, ?, ?)
            """, (attempt_id, q_id, sel, corr))

        flash(f"Test submitted successfully! You scored {score}/{total_questions} ({percentage}%).", "success")
        return redirect(url_for('student.mock_test_results'))

    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template('student/take_test.html', test=test, questions=questions, started_at=started_at)

# ==================== RESULTS ====================

@student_bp.route('/student/mock-test-results')
@student_required
def mock_test_results():
    student_id = session['student_id']
    student_stream = session.get('student_course_type', 'Degree')
    attempts = query_db("""
        SELECT a.*, t.test_name, t.course_type, s.subject_name
        FROM attempts a
        INNER JOIN tests t ON a.test_id = t.id
        INNER JOIN subjects s ON t.subject_id = s.id
        WHERE a.user_id = ? AND t.course_type = ?
        ORDER BY a.submitted_at DESC
    """, (student_id, student_stream))

    return render_template('student/mock_test_results.html', attempts=attempts, course_type=student_stream)

@student_bp.route('/student/practice-results')
@student_required
def practice_results():
    student_id = session['student_id']
    student_stream = session.get('student_course_type', 'Degree')
    results = query_db("""
        SELECT tr.*, s.subject_name, c.chapter_name
        FROM test_results tr
        INNER JOIN subjects s ON tr.subject_id = s.id
        LEFT JOIN chapters c ON tr.chapter_id = c.id
        WHERE tr.student_id = ? AND s.course_type = ?
        ORDER BY tr.test_date DESC
    """, (student_id, student_stream))

    return render_template('student/practice_history.html', results=results, course_type=student_stream)

# ==================== VIDEO LECTURES ====================

@student_bp.route('/student/video-lectures')
@student_required
def video_lectures():
    student_stream = session.get('student_course_type', 'Degree')
    if session.get('admin_id'):
        course_type = request.args.get('course_type', student_stream)
        if course_type not in ['Degree', 'Diploma']:
            course_type = 'Degree'
    else:
        course_type = student_stream
    search = request.args.get('search', '').strip()

    query = "SELECT * FROM video_lectures WHERE course_type = ?"
    params = [course_type]

    if search:
        query += " AND description LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY id DESC"
    lectures = query_db(query, tuple(params))

    for lecture in lectures:
        lecture['youtube_id'] = extract_youtube_id(lecture['youtube_link'])

    return render_template('student/video_lectures.html', lectures=lectures, course_type=course_type, search=search)
