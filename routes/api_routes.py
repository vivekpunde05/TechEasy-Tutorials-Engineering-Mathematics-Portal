from flask import jsonify, request
from routes import api_bp
from database import query_db

@api_bp.route('/chapters')
def get_chapters():
    subject_id = request.args.get('subject_id', type=int)
    if not subject_id:
        return jsonify([])

    chapters = query_db("""
        SELECT id, chapter_name 
        FROM chapters 
        WHERE subject_id = ? 
        ORDER BY chapter_name
    """, (subject_id,))
    return jsonify(chapters)

@api_bp.route('/topics')
def get_topics():
    chapter_id = request.args.get('chapter_id', type=int)
    if not chapter_id:
        return jsonify([])

    topics = query_db("""
        SELECT id, topic_name 
        FROM topics 
        WHERE chapter_id = ? 
        ORDER BY topic_name
    """, (chapter_id,))
    return jsonify(topics)

@api_bp.route('/questions/<int:id>')
def get_question(id):
    question = query_db("""
        SELECT q.*, s.subject_name, c.chapter_name
        FROM questions q
        INNER JOIN subjects s ON q.subject_id = s.id
        INNER JOIN chapters c ON q.chapter_id = c.id
        WHERE q.id = ?
    """, (id,), one=True)
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    return jsonify(question)
