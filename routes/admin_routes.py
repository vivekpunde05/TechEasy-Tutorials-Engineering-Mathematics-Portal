import os
import uuid
from flask import render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.utils import secure_filename
from routes import admin_bp
from routes.auth_routes import admin_required
from database import query_db, execute_db, extract_youtube_id
from config import Config

def save_uploaded_image(file_storage):
    """Save uploaded image file to uploads/questions directory and return filename."""
    if not file_storage or file_storage.filename == '':
        return ''
    
    filename = secure_filename(file_storage.filename)
    if '.' not in filename:
        return ''
    
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in Config.ALLOWED_EXTENSIONS:
        return ''
    
    new_filename = f"mcq_{uuid.uuid4().hex[:12]}.{ext}"
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    file_storage.save(os.path.join(Config.UPLOAD_FOLDER, new_filename))
    return new_filename

# ==================== ADMIN DASHBOARD ====================

# ==================== ADMIN DASHBOARD ====================

@admin_bp.route('/', methods=['GET', 'POST'])
@admin_bp.route('/dashboard', methods=['GET', 'POST'])
@admin_required
def dashboard():
    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id', type=int)
        current_tab = request.form.get('current_tab', 'students')
        current_stream = request.form.get('student_stream', 'Degree')

        if action == 'change_stream' and user_id:
            new_stream = request.form.get('course_type')
            if new_stream in ['Degree', 'Diploma']:
                execute_db("UPDATE users SET course_type = ? WHERE id = ? AND role = 'student'", (new_stream, user_id))
                flash("Student stream updated successfully.", "success")

        elif action == 'delete_student' and user_id:
            execute_db("DELETE FROM users WHERE id = ? AND role = 'student'", (user_id,))
            flash("Student account removed.", "info")

        return redirect(url_for('admin.dashboard', tab=current_tab, student_stream=current_stream))

    active_tab = request.args.get('tab', 'home')
    if active_tab not in ['home', 'degree', 'diploma', 'students']:
        active_tab = 'home'

    student_stream = request.args.get('student_stream', 'Degree')
    if student_stream not in ['Degree', 'Diploma']:
        student_stream = 'Degree'

    # Global Stats
    stats = {
        'subjects': query_db("SELECT COUNT(*) as c FROM subjects", one=True)['c'],
        'chapters': query_db("SELECT COUNT(*) as c FROM chapters", one=True)['c'],
        'topics': query_db("SELECT COUNT(*) as c FROM topics", one=True)['c'],
        'questions': query_db("SELECT COUNT(*) as c FROM questions", one=True)['c'],
        'tests': query_db("SELECT COUNT(*) as c FROM tests", one=True)['c'],
        'attempts': query_db("SELECT COUNT(*) as c FROM attempts", one=True)['c'],
        'students': query_db("SELECT COUNT(*) as c FROM users WHERE role = 'student'", one=True)['c'],
        'videos': query_db("SELECT COUNT(*) as c FROM video_lectures", one=True)['c'],
        'degree_students': query_db("SELECT COUNT(*) as c FROM users WHERE role = 'student' AND course_type = 'Degree'", one=True)['c'],
        'diploma_students': query_db("SELECT COUNT(*) as c FROM users WHERE role = 'student' AND course_type = 'Diploma'", one=True)['c']
    }

    # Degree Specific Stats
    degree_stats = {
        'subjects': query_db("SELECT COUNT(*) as c FROM subjects WHERE course_type = 'Degree'", one=True)['c'],
        'chapters': query_db("SELECT COUNT(DISTINCT c.id) as c FROM chapters c JOIN subjects s ON c.subject_id = s.id WHERE s.course_type = 'Degree'", one=True)['c'],
        'questions': query_db("SELECT COUNT(DISTINCT q.id) as c FROM questions q JOIN subjects s ON q.subject_id = s.id WHERE s.course_type = 'Degree'", one=True)['c'],
        'tests': query_db("SELECT COUNT(*) as c FROM tests WHERE course_type = 'Degree'", one=True)['c'],
        'students': stats['degree_students'],
        'videos': query_db("SELECT COUNT(*) as c FROM video_lectures WHERE course_type = 'Degree'", one=True)['c']
    }

    # Diploma Specific Stats
    diploma_stats = {
        'subjects': query_db("SELECT COUNT(*) as c FROM subjects WHERE course_type = 'Diploma'", one=True)['c'],
        'chapters': query_db("SELECT COUNT(DISTINCT c.id) as c FROM chapters c JOIN subjects s ON c.subject_id = s.id WHERE s.course_type = 'Diploma'", one=True)['c'],
        'questions': query_db("SELECT COUNT(DISTINCT q.id) as c FROM questions q JOIN subjects s ON q.subject_id = s.id WHERE s.course_type = 'Diploma'", one=True)['c'],
        'tests': query_db("SELECT COUNT(*) as c FROM tests WHERE course_type = 'Diploma'", one=True)['c'],
        'students': stats['diploma_students'],
        'videos': query_db("SELECT COUNT(*) as c FROM video_lectures WHERE course_type = 'Diploma'", one=True)['c']
    }

    # Subjects with counts
    all_subjects = query_db("""
        SELECT s.*, 
            COUNT(DISTINCT c.id) as chapter_count,
            COUNT(DISTINCT q.id) as question_count,
            COUNT(DISTINCT t.id) as test_count
        FROM subjects s
        LEFT JOIN chapters c ON s.id = c.subject_id
        LEFT JOIN questions q ON s.id = q.subject_id
        LEFT JOIN tests t ON s.id = t.subject_id
        GROUP BY s.id
        ORDER BY s.course_type, s.semester, s.subject_name
    """)
    degree_subjects = [s for s in all_subjects if s['course_type'] == 'Degree']
    diploma_subjects = [s for s in all_subjects if s['course_type'] == 'Diploma']

    # Students strictly for selected stream (Degree or Diploma)
    stream_students = query_db("""
        SELECT u.*,
            (SELECT COUNT(*) FROM attempts WHERE user_id = u.id) as mock_attempts,
            (SELECT COUNT(*) FROM test_results WHERE student_id = u.id) as practice_attempts
        FROM users u
        WHERE u.role = 'student' AND u.course_type = ?
        ORDER BY u.id DESC
    """, (student_stream,))

    recent_attempts = query_db("""
        SELECT a.*, u.name as student_name, u.email as student_email, t.test_name, s.subject_name, t.course_type as test_course_type
        FROM attempts a
        INNER JOIN users u ON a.user_id = u.id
        INNER JOIN tests t ON a.test_id = t.id
        INNER JOIN subjects s ON t.subject_id = s.id
        ORDER BY a.submitted_at DESC
        LIMIT 6
    """)

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        degree_stats=degree_stats,
        diploma_stats=diploma_stats,
        all_subjects=all_subjects,
        degree_subjects=degree_subjects,
        diploma_subjects=diploma_subjects,
        stream_students=stream_students,
        student_stream=student_stream,
        active_tab=active_tab,
        recent_attempts=recent_attempts
    )

# ==================== SUBJECTS ====================

@admin_bp.route('/subjects', methods=['GET', 'POST'])
@admin_required
def subjects():
    stream = request.args.get('stream', request.form.get('course_type', 'Degree')).strip()
    if stream not in ['Degree', 'Diploma']:
        stream = 'Degree'

    if request.method == 'POST':
        action = request.form.get('action')
        course_type = request.form.get('course_type', stream).strip()
        if course_type not in ['Degree', 'Diploma']:
            course_type = stream

        redirect_tab = request.form.get('redirect_tab', '').strip()

        if action == 'add':
            semester = request.form.get('semester', '').strip()
            subject_name = request.form.get('subject_name', '').strip()

            if not semester or not subject_name:
                flash("Please fill in all subject fields.", "danger")
            else:
                existing = query_db("""
                    SELECT id FROM subjects 
                    WHERE course_type = ? AND semester = ? AND subject_name = ?
                """, (course_type, semester, subject_name), one=True)
                if existing:
                    flash(f"This {course_type} subject already exists for this semester.", "warning")
                else:
                    execute_db("""
                        INSERT INTO subjects (course_type, semester, subject_name)
                        VALUES (?, ?, ?)
                    """, (course_type, semester, subject_name))
                    flash(f"{course_type} Subject '{subject_name}' added successfully!", "success")

        elif action == 'edit':
            subject_id = request.form.get('subject_id', type=int)
            semester = request.form.get('semester', '').strip()
            subject_name = request.form.get('subject_name', '').strip()

            if subject_id and semester and subject_name:
                execute_db("""
                    UPDATE subjects SET course_type = ?, semester = ?, subject_name = ?
                    WHERE id = ?
                """, (course_type, semester, subject_name, subject_id))
                flash(f"{course_type} Subject updated successfully!", "success")

        elif action == 'delete':
            subject_id = request.form.get('subject_id', type=int)
            if subject_id:
                execute_db("DELETE FROM subjects WHERE id = ?", (subject_id,))
                flash("Subject deleted successfully.", "info")

        if redirect_tab in ['degree', 'diploma']:
            return redirect(url_for('admin.dashboard', tab=redirect_tab))
        return redirect(url_for('admin.subjects', stream=course_type))

    subjects_list = query_db("""
        SELECT s.*, 
            COUNT(DISTINCT c.id) as chapter_count,
            COUNT(DISTINCT q.id) as question_count
        FROM subjects s
        LEFT JOIN chapters c ON s.id = c.subject_id
        LEFT JOIN questions q ON s.id = q.subject_id
        WHERE s.course_type = ?
        GROUP BY s.id
        ORDER BY s.semester, s.subject_name
    """, (stream,))

    degree_count = query_db("SELECT COUNT(*) as c FROM subjects WHERE course_type = 'Degree'", one=True)['c']
    diploma_count = query_db("SELECT COUNT(*) as c FROM subjects WHERE course_type = 'Diploma'", one=True)['c']

    return render_template(
        'admin/subjects.html',
        subjects=subjects_list,
        selected_stream=stream,
        degree_count=degree_count,
        diploma_count=diploma_count,
        active_tab=stream.lower()
    )

# ==================== CHAPTERS ====================

@admin_bp.route('/chapters', methods=['GET', 'POST'])
@admin_required
def chapters():
    stream = request.args.get('stream', '').strip()
    selected_subject_id = request.args.get('subject_id', type=int)

    # Infer stream from selected_subject_id if stream not explicitly given
    if not stream and selected_subject_id:
        sub = query_db("SELECT course_type FROM subjects WHERE id = ?", (selected_subject_id,), one=True)
        if sub:
            stream = sub['course_type']

    if request.method == 'POST':
        action = request.form.get('action')
        post_stream = request.form.get('stream', stream).strip()

        if action == 'add':
            subject_id = request.form.get('subject_id', type=int)
            chapter_name = ' '.join(request.form.get('chapter_name', '').split())

            if not subject_id or not chapter_name:
                flash("Please select a subject and enter chapter name.", "danger")
            else:
                existing = query_db("""
                    SELECT id FROM chapters WHERE subject_id = ? AND chapter_name = ?
                """, (subject_id, chapter_name), one=True)
                if existing:
                    flash("This chapter already exists for this subject.", "warning")
                else:
                    execute_db("""
                        INSERT INTO chapters (subject_id, chapter_name) VALUES (?, ?)
                    """, (subject_id, chapter_name))
                    flash("Chapter added successfully!", "success")
                sub = query_db("SELECT course_type FROM subjects WHERE id = ?", (subject_id,), one=True)
                if sub:
                    post_stream = sub['course_type']

        elif action == 'edit':
            chapter_id = request.form.get('chapter_id', type=int)
            subject_id = request.form.get('subject_id', type=int)
            chapter_name = ' '.join(request.form.get('chapter_name', '').split())

            if chapter_id and subject_id and chapter_name:
                execute_db("""
                    UPDATE chapters SET subject_id = ?, chapter_name = ? WHERE id = ?
                """, (subject_id, chapter_name, chapter_id))
                flash("Chapter updated successfully!", "success")
                sub = query_db("SELECT course_type FROM subjects WHERE id = ?", (subject_id,), one=True)
                if sub:
                    post_stream = sub['course_type']

        elif action == 'delete':
            chapter_id = request.form.get('chapter_id', type=int)
            if chapter_id:
                chap = query_db("SELECT s.course_type FROM chapters c JOIN subjects s ON c.subject_id = s.id WHERE c.id = ?", (chapter_id,), one=True)
                if chap:
                    post_stream = chap['course_type']
                execute_db("DELETE FROM chapters WHERE id = ?", (chapter_id,))
                flash("Chapter deleted successfully.", "info")

        redirect_args = {}
        if post_stream in ['Degree', 'Diploma']:
            redirect_args['stream'] = post_stream
        return redirect(url_for('admin.chapters', **redirect_args))

    if stream not in ['Degree', 'Diploma']:
        stream = 'Degree'

    # Filter subjects by the current stream
    subjects_list = query_db("""
        SELECT * FROM subjects 
        WHERE course_type = ? 
        ORDER BY semester, subject_name
    """, (stream,))

    query = """
        SELECT c.*, s.subject_name, s.course_type, s.semester,
            COUNT(DISTINCT q.id) as question_count,
            COUNT(DISTINCT t.id) as topic_count
        FROM chapters c
        INNER JOIN subjects s ON c.subject_id = s.id
        LEFT JOIN questions q ON c.id = q.chapter_id
        LEFT JOIN topics t ON c.id = t.chapter_id
        WHERE s.course_type = ?
    """
    params = [stream]
    if selected_subject_id:
        query += " AND c.subject_id = ?"
        params.append(selected_subject_id)

    query += " GROUP BY c.id ORDER BY s.semester, c.id DESC"
    all_chapters = query_db(query, tuple(params))

    return render_template(
        'admin/chapters.html',
        chapters=all_chapters,
        subjects=subjects_list,
        selected_subject_id=selected_subject_id,
        selected_stream=stream,
        active_tab=stream.lower()
    )

# ==================== TOPICS ====================

@admin_bp.route('/topics', methods=['GET', 'POST'])
@admin_required
def topics():
    chapter_id = request.args.get('chapter_id', type=int) or request.form.get('chapter_id', type=int)
    if not chapter_id:
        flash("Please select a chapter to manage topics.", "info")
        return redirect(url_for('admin.chapters'))

    chapter = query_db("""
        SELECT c.*, s.subject_name, s.course_type 
        FROM chapters c
        INNER JOIN subjects s ON c.subject_id = s.id
        WHERE c.id = ?
    """, (chapter_id,), one=True)

    if not chapter:
        flash("Chapter not found.", "danger")
        return redirect(url_for('admin.chapters'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            topic_name = ' '.join(request.form.get('topic_name', '').split())
            if not topic_name:
                flash("Please enter topic name.", "danger")
            else:
                existing = query_db("SELECT id FROM topics WHERE chapter_id = ? AND topic_name = ?", (chapter_id, topic_name), one=True)
                if existing:
                    flash("This topic already exists in this chapter.", "warning")
                else:
                    execute_db("INSERT INTO topics (chapter_id, topic_name) VALUES (?, ?)", (chapter_id, topic_name))
                    flash("Topic added successfully!", "success")

        elif action == 'delete':
            topic_id = request.form.get('topic_id', type=int)
            if topic_id:
                execute_db("DELETE FROM topics WHERE id = ?", (topic_id,))
                flash("Topic deleted successfully.", "info")

        return redirect(url_for('admin.topics', chapter_id=chapter_id))

    all_topics = query_db("SELECT * FROM topics WHERE chapter_id = ? ORDER BY id DESC", (chapter_id,))
    return render_template('admin/topics.html', chapter=chapter, topics=all_topics)

# ==================== QUESTIONS / MCQs ====================

@admin_bp.route('/questions')
@admin_required
def questions():
    stream = request.args.get('stream', '').strip()
    subject_id = request.args.get('subject_id', type=int)
    chapter_id = request.args.get('chapter_id', type=int)
    difficulty = request.args.get('difficulty', '')
    search = request.args.get('search', '').strip()

    # If stream not given, infer from subject or chapter
    if not stream and subject_id:
        sub = query_db("SELECT course_type FROM subjects WHERE id = ?", (subject_id,), one=True)
        if sub:
            stream = sub['course_type']

    if not stream and chapter_id:
        chap = query_db("SELECT s.course_type FROM chapters c JOIN subjects s ON c.subject_id = s.id WHERE c.id = ?", (chapter_id,), one=True)
        if chap:
            stream = chap['course_type']

    if stream not in ['Degree', 'Diploma']:
        stream = 'Degree'

    subjects_list = query_db("SELECT * FROM subjects WHERE course_type = ? ORDER BY semester, subject_name", (stream,))
    
    if subject_id:
        chapters_list = query_db("SELECT * FROM chapters WHERE subject_id = ? ORDER BY chapter_name", (subject_id,))
    else:
        chapters_list = query_db("""
            SELECT c.* FROM chapters c 
            JOIN subjects s ON c.subject_id = s.id 
            WHERE s.course_type = ? 
            ORDER BY c.chapter_name
        """, (stream,))

    query = """
        SELECT q.*, s.subject_name, s.course_type, c.chapter_name
        FROM questions q
        INNER JOIN subjects s ON q.subject_id = s.id
        INNER JOIN chapters c ON q.chapter_id = c.id
        WHERE s.course_type = ?
    """
    params = [stream]

    if subject_id:
        query += " AND q.subject_id = ?"
        params.append(subject_id)
    if chapter_id:
        query += " AND q.chapter_id = ?"
        params.append(chapter_id)
    if difficulty:
        query += " AND q.difficulty = ?"
        params.append(difficulty)
    if search:
        query += " AND (q.question LIKE ? OR q.explanation LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY q.id DESC"
    questions_list = query_db(query, tuple(params))

    return render_template(
        'admin/questions.html',
        questions=questions_list,
        subjects=subjects_list,
        chapters=chapters_list,
        selected_subject_id=subject_id,
        selected_chapter_id=chapter_id,
        selected_difficulty=difficulty,
        search=search,
        selected_stream=stream,
        active_tab=stream.lower()
    )

@admin_bp.route('/questions/add', methods=['GET', 'POST'])
@admin_required
def add_question():
    stream = request.args.get('stream', request.form.get('stream', '')).strip()

    if request.method == 'POST':
        subject_id = request.form.get('subject_id', type=int)
        chapter_id = request.form.get('chapter_id', type=int)
        question_text = request.form.get('question', '').strip()
        option_a = request.form.get('option_a', '').strip()
        option_b = request.form.get('option_b', '').strip()
        option_c = request.form.get('option_c', '').strip()
        option_d = request.form.get('option_d', '').strip()
        correct_answer = request.form.get('correct_answer', '').strip().upper()
        explanation = request.form.get('explanation', '').strip()
        difficulty = request.form.get('difficulty', 'Medium')

        if not stream and subject_id:
            sub = query_db("SELECT course_type FROM subjects WHERE id = ?", (subject_id,), one=True)
            if sub:
                stream = sub['course_type']

        if not subject_id or not chapter_id or not question_text or not option_a or not option_b or not option_c or not option_d or not correct_answer:
            flash("Please fill in all required question fields.", "danger")
        else:
            q_img = save_uploaded_image(request.files.get('question_image'))
            oa_img = save_uploaded_image(request.files.get('option_a_image'))
            ob_img = save_uploaded_image(request.files.get('option_b_image'))
            oc_img = save_uploaded_image(request.files.get('option_c_image'))
            od_img = save_uploaded_image(request.files.get('option_d_image'))
            exp_img = save_uploaded_image(request.files.get('explanation_image'))

            execute_db("""
                INSERT INTO questions (
                    subject_id, chapter_id, question, question_image,
                    option_a, option_a_image,
                    option_b, option_b_image,
                    option_c, option_c_image,
                    option_d, option_d_image,
                    correct_answer, explanation, explanation_image, difficulty
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subject_id, chapter_id, question_text, q_img,
                option_a, oa_img,
                option_b, ob_img,
                option_c, oc_img,
                option_d, od_img,
                correct_answer, explanation, exp_img, difficulty
            ))
            flash(f"{stream} MCQ Question added successfully!", "success")
            return redirect(url_for('admin.questions', stream=stream, subject_id=subject_id, chapter_id=chapter_id))

    if stream not in ['Degree', 'Diploma']:
        stream = 'Degree'

    subjects_list = query_db("SELECT * FROM subjects WHERE course_type = ? ORDER BY semester, subject_name", (stream,))
    return render_template(
        'admin/question_form.html',
        mode='add',
        subjects=subjects_list,
        mcq=None,
        selected_stream=stream,
        active_tab=stream.lower()
    )

@admin_bp.route('/questions/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_question(id):
    mcq = query_db("""
        SELECT q.*, s.course_type 
        FROM questions q 
        JOIN subjects s ON q.subject_id = s.id 
        WHERE q.id = ?
    """, (id,), one=True)
    if not mcq:
        flash("Question not found.", "danger")
        return redirect(url_for('admin.questions'))

    stream = mcq['course_type']
    subjects_list = query_db("SELECT * FROM subjects WHERE course_type = ? ORDER BY semester, subject_name", (stream,))
    chapters_list = query_db("SELECT * FROM chapters WHERE subject_id = ? ORDER BY chapter_name", (mcq['subject_id'],))

    if request.method == 'POST':
        subject_id = request.form.get('subject_id', type=int)
        chapter_id = request.form.get('chapter_id', type=int)
        question_text = request.form.get('question', '').strip()
        option_a = request.form.get('option_a', '').strip()
        option_b = request.form.get('option_b', '').strip()
        option_c = request.form.get('option_c', '').strip()
        option_d = request.form.get('option_d', '').strip()
        correct_answer = request.form.get('correct_answer', '').strip().upper()
        explanation = request.form.get('explanation', '').strip()
        difficulty = request.form.get('difficulty', 'Medium')

        if not subject_id or not chapter_id or not question_text or not option_a or not option_b or not option_c or not option_d or not correct_answer:
            flash("Please fill in all required question fields.", "danger")
        else:
            q_img = save_uploaded_image(request.files.get('question_image')) or mcq['question_image']
            oa_img = save_uploaded_image(request.files.get('option_a_image')) or mcq['option_a_image']
            ob_img = save_uploaded_image(request.files.get('option_b_image')) or mcq['option_b_image']
            oc_img = save_uploaded_image(request.files.get('option_c_image')) or mcq['option_c_image']
            od_img = save_uploaded_image(request.files.get('option_d_image')) or mcq['option_d_image']
            exp_img = save_uploaded_image(request.files.get('explanation_image')) or mcq.get('explanation_image', '')

            execute_db("""
                UPDATE questions SET
                    subject_id = ?, chapter_id = ?, question = ?, question_image = ?,
                    option_a = ?, option_a_image = ?,
                    option_b = ?, option_b_image = ?,
                    option_c = ?, option_c_image = ?,
                    option_d = ?, option_d_image = ?,
                    correct_answer = ?, explanation = ?, explanation_image = ?, difficulty = ?
                WHERE id = ?
            """, (
                subject_id, chapter_id, question_text, q_img,
                option_a, oa_img,
                option_b, ob_img,
                option_c, oc_img,
                option_d, od_img,
                correct_answer, explanation, exp_img, difficulty, id
            ))
            flash(f"{stream} MCQ Question updated successfully!", "success")
            return redirect(url_for('admin.questions', stream=stream, subject_id=subject_id, chapter_id=chapter_id))

    return render_template(
        'admin/question_form.html',
        mode='edit',
        subjects=subjects_list,
        chapters=chapters_list,
        mcq=mcq,
        selected_stream=stream,
        active_tab=stream.lower()
    )

@admin_bp.route('/questions/delete/<int:id>', methods=['POST'])
@admin_required
def delete_question(id):
    mcq = query_db("""
        SELECT s.course_type 
        FROM questions q 
        JOIN subjects s ON q.subject_id = s.id 
        WHERE q.id = ?
    """, (id,), one=True)
    stream = mcq['course_type'] if mcq else 'Degree'
    execute_db("DELETE FROM questions WHERE id = ?", (id,))
    flash("Question deleted successfully.", "info")
    return redirect(request.referrer or url_for('admin.questions', stream=stream))

# ==================== TESTS ====================

@admin_bp.route('/tests', methods=['GET', 'POST'])
@admin_required
def tests():
    stream = request.args.get('stream', '').strip()
    if stream not in ['Degree', 'Diploma']:
        stream = request.form.get('stream', '').strip()
        if stream not in ['Degree', 'Diploma']:
            stream = 'Degree'

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            test_name = request.form.get('test_name', '').strip()
            subject_id = request.form.get('subject_id', type=int)
            time_limit = request.form.get('time_limit', type=int, default=30)
            course_type = request.form.get('course_type', stream).strip()

            if subject_id:
                subj = query_db("SELECT course_type FROM subjects WHERE id = ?", (subject_id,), one=True)
                if subj:
                    course_type = subj['course_type']
            if course_type not in ['Degree', 'Diploma']:
                course_type = stream

            if not test_name or not course_type or not subject_id or time_limit <= 0:
                flash("Please fill in all valid test details.", "danger")
            else:
                existing = query_db("""
                    SELECT id FROM tests WHERE test_name = ? AND course_type = ? AND subject_id = ?
                """, (test_name, course_type, subject_id), one=True)
                if existing:
                    flash("This test already exists for this course and subject.", "warning")
                else:
                    execute_db("""
                        INSERT INTO tests (test_name, course_type, subject_id, number_of_questions, time_limit)
                        VALUES (?, ?, ?, 0, ?)
                    """, (test_name, course_type, subject_id, time_limit))
                    flash(f"Test '{test_name}' created successfully! Now add questions to it.", "success")

            return redirect(url_for('admin.tests', stream=course_type))

        elif action == 'delete':
            test_id = request.form.get('test_id', type=int)
            target_stream = stream
            if test_id:
                test_obj = query_db("SELECT course_type FROM tests WHERE id = ?", (test_id,), one=True)
                if test_obj:
                    target_stream = test_obj['course_type']
                execute_db("DELETE FROM tests WHERE id = ?", (test_id,))
                flash("Test deleted successfully.", "info")
            return redirect(url_for('admin.tests', stream=target_stream))

        return redirect(url_for('admin.tests', stream=stream))

    subjects_list = query_db(
        "SELECT * FROM subjects WHERE course_type = ? ORDER BY semester, subject_name",
        (stream,)
    )
    all_tests = query_db("""
        SELECT t.*, s.subject_name,
            (SELECT COUNT(*) FROM attempts a2 INNER JOIN users u2 ON a2.user_id = u2.id WHERE a2.test_id = t.id AND u2.course_type = t.course_type) as attempt_count
        FROM tests t
        INNER JOIN subjects s ON t.subject_id = s.id
        WHERE t.course_type = ?
        ORDER BY t.id DESC
    """, (stream,))

    return render_template(
        'admin/tests.html',
        tests=all_tests,
        subjects=subjects_list,
        selected_stream=stream,
        active_tab=stream.lower()
    )

@admin_bp.route('/tests/<int:test_id>/manage', methods=['GET', 'POST'])
@admin_required
def manage_test(test_id):
    test = query_db("""
        SELECT t.*, s.subject_name 
        FROM tests t
        INNER JOIN subjects s ON t.subject_id = s.id
        WHERE t.id = ?
    """, (test_id,), one=True)

    if not test:
        flash("Test not found.", "danger")
        return redirect(url_for('admin.tests'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_question':
            question_id = request.form.get('question_id', type=int)
            if question_id:
                existing = query_db("SELECT id FROM test_questions WHERE test_id = ? AND question_id = ?", (test_id, question_id), one=True)
                if not existing:
                    execute_db("INSERT INTO test_questions (test_id, question_id) VALUES (?, ?)", (test_id, question_id))
                    # Update count
                    cnt = query_db("SELECT COUNT(*) as c FROM test_questions WHERE test_id = ?", (test_id,), one=True)['c']
                    execute_db("UPDATE tests SET number_of_questions = ? WHERE id = ?", (cnt, test_id))
                    flash("Question added to test!", "success")

        elif action == 'remove_question':
            question_id = request.form.get('question_id', type=int)
            if question_id:
                execute_db("DELETE FROM test_questions WHERE test_id = ? AND question_id = ?", (test_id, question_id))
                cnt = query_db("SELECT COUNT(*) as c FROM test_questions WHERE test_id = ?", (test_id,), one=True)['c']
                execute_db("UPDATE tests SET number_of_questions = ? WHERE id = ?", (cnt, test_id))
                flash("Question removed from test.", "info")

        return redirect(url_for('admin.manage_test', test_id=test_id))

    # Assigned questions
    assigned_questions = query_db("""
        SELECT q.*, c.chapter_name
        FROM test_questions tq
        INNER JOIN questions q ON tq.question_id = q.id
        INNER JOIN chapters c ON q.chapter_id = c.id
        WHERE tq.test_id = ?
        ORDER BY tq.id ASC
    """, (test_id,))

    # Available questions for this subject that are NOT yet assigned
    assigned_ids = [q['id'] for q in assigned_questions]
    available_query = """
        SELECT q.*, c.chapter_name
        FROM questions q
        INNER JOIN chapters c ON q.chapter_id = c.id
        WHERE q.subject_id = ?
    """
    if assigned_ids:
        placeholders = ','.join('?' for _ in assigned_ids)
        available_query += f" AND q.id NOT IN ({placeholders})"
        available_questions = query_db(available_query, (test['subject_id'], *assigned_ids))
    else:
        available_questions = query_db(available_query, (test['subject_id'],))

    return render_template(
        'admin/manage_test.html',
        test=test,
        assigned_questions=assigned_questions,
        available_questions=available_questions
    )

@admin_bp.route('/tests/<int:test_id>/results')
@admin_required
def test_results(test_id):
    test = query_db("""
        SELECT t.*, s.subject_name 
        FROM tests t
        INNER JOIN subjects s ON t.subject_id = s.id
        WHERE t.id = ?
    """, (test_id,), one=True)

    if not test:
        flash("Test not found.", "danger")
        return redirect(url_for('admin.tests'))

    attempts = query_db("""
        SELECT a.*, u.name as student_name, u.email as student_email, u.mobile as student_mobile, u.course_type as student_stream
        FROM attempts a
        INNER JOIN users u ON a.user_id = u.id
        WHERE a.test_id = ? AND u.course_type = ?
        ORDER BY a.submitted_at DESC
    """, (test_id, test['course_type']))

    return render_template('admin/test_results.html', test=test, attempts=attempts)

@admin_bp.route('/practice-results')
@admin_required
def practice_results():
    stream = request.args.get('stream', '').strip()
    if stream not in ['Degree', 'Diploma']:
        stream = 'Degree'

    results = query_db("""
        SELECT tr.*, u.name as student_name, u.email as student_email, u.course_type as student_stream,
               s.subject_name, c.chapter_name
        FROM test_results tr
        INNER JOIN users u ON tr.student_id = u.id
        INNER JOIN subjects s ON tr.subject_id = s.id
        LEFT JOIN chapters c ON tr.chapter_id = c.id
        WHERE u.course_type = ?
        ORDER BY tr.test_date DESC
    """, (stream,))

    return render_template(
        'admin/practice_results.html',
        results=results,
        selected_stream=stream,
        active_tab=stream.lower()
    )

# ==================== VIDEO LECTURES ====================

@admin_bp.route('/video-lectures', methods=['GET', 'POST'])
@admin_required
def video_lectures():
    stream = request.args.get('stream', '').strip()
    if stream not in ['Degree', 'Diploma']:
        stream = request.form.get('stream', '').strip()
        if stream not in ['Degree', 'Diploma']:
            stream = 'Degree'

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            course_type = request.form.get('course_type', stream).strip()
            if course_type not in ['Degree', 'Diploma']:
                course_type = stream
            youtube_link = request.form.get('youtube_link', '').strip()
            description = request.form.get('description', '').strip()

            if not course_type or not youtube_link or not description:
                flash("Please fill in all fields.", "danger")
            elif "youtube.com" not in youtube_link and "youtu.be" not in youtube_link:
                flash("Please enter a valid YouTube link.", "danger")
            else:
                existing = query_db("SELECT id FROM video_lectures WHERE youtube_link = ? AND course_type = ?", (youtube_link, course_type), one=True)
                if existing:
                    flash("This YouTube lecture has already been added for this stream.", "warning")
                else:
                    execute_db("""
                        INSERT INTO video_lectures (course_type, youtube_link, description)
                        VALUES (?, ?, ?)
                    """, (course_type, youtube_link, description))
                    flash(f"{course_type} video lecture added successfully!", "success")

            return redirect(url_for('admin.video_lectures', stream=course_type))

        elif action == 'delete':
            video_id = request.form.get('video_id', type=int)
            target_stream = stream
            if video_id:
                vid = query_db("SELECT course_type FROM video_lectures WHERE id = ?", (video_id,), one=True)
                if vid:
                    target_stream = vid['course_type']
                execute_db("DELETE FROM video_lectures WHERE id = ?", (video_id,))
                flash("Video lecture deleted.", "info")
            return redirect(url_for('admin.video_lectures', stream=target_stream))

        return redirect(url_for('admin.video_lectures', stream=stream))

    lectures = query_db("SELECT * FROM video_lectures WHERE course_type = ? ORDER BY id DESC", (stream,))
    for lecture in lectures:
        lecture['youtube_id'] = extract_youtube_id(lecture['youtube_link'])

    return render_template(
        'admin/video_lectures.html',
        lectures=lectures,
        selected_stream=stream,
        active_tab=stream.lower()
    )

# ==================== STUDENTS MANAGEMENT ====================

@admin_bp.route('/students', methods=['GET', 'POST'])
@admin_required
def students():
    selected_stream = request.args.get('stream', 'Degree')
    if selected_stream not in ['Degree', 'Diploma']:
        selected_stream = 'Degree'

    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id', type=int)

        if action == 'change_stream' and user_id:
            new_stream = request.form.get('course_type')
            if new_stream in ['Degree', 'Diploma']:
                execute_db("UPDATE users SET course_type = ? WHERE id = ? AND role = 'student'", (new_stream, user_id))
                flash("Student stream updated successfully.", "success")

        elif action == 'delete_student' and user_id:
            execute_db("DELETE FROM users WHERE id = ? AND role = 'student'", (user_id,))
            flash("Student account removed.", "info")

        return redirect(url_for('admin.students', stream=selected_stream))

    query = """
        SELECT u.*,
            (SELECT COUNT(*) FROM attempts WHERE user_id = u.id) as mock_attempts,
            (SELECT COUNT(*) FROM test_results WHERE student_id = u.id) as practice_attempts
        FROM users u
        WHERE u.role = 'student' AND u.course_type = ?
        ORDER BY u.id DESC
    """
    stream_students = query_db(query, (selected_stream,))

    degree_count = query_db("SELECT COUNT(*) as c FROM users WHERE role = 'student' AND course_type = 'Degree'", one=True)['c']
    diploma_count = query_db("SELECT COUNT(*) as c FROM users WHERE role = 'student' AND course_type = 'Diploma'", one=True)['c']

    return render_template(
        'admin/students.html',
        students=stream_students,
        selected_stream=selected_stream,
        degree_count=degree_count,
        diploma_count=diploma_count
    )
