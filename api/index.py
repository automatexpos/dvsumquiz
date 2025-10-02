import os
import json
import random
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify
from supabase import create_client
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Load .env file
load_dotenv()
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise Exception('Missing Gemini API key in environment variables')
if not (SUPABASE_URL and SUPABASE_KEY):
    raise Exception('Missing Supabase credentials in environment variables')
genai.configure(api_key=GEMINI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), 'static'),
    template_folder=os.path.join(os.path.dirname(__file__), 'templates')
)


# Course management functions
def load_course_data(course_id):
    """Load questions and knowledge text for a specific course."""
    course_file = f"{course_id.lower()}.json"
    course_path = os.path.join(os.path.dirname(__file__), 'courses', course_file)
    
    if not os.path.exists(course_path):
        return None
    
    with open(course_path, 'r', encoding='utf-8') as f:
        course_data = json.load(f)
    
    return course_data

def pick_random_questions(course_data, n=5):
    """Pick n random questions from the course data."""
    questions = course_data.get("questions", [])
    return [{"q": q} for q in random.sample(questions, min(n, len(questions)))]

def evaluate_answer_gemini(user_answer, question, knowledge_text):
    """Use Gemini to evaluate the user's answer against the knowledge text."""
    prompt = (
        f"You are an expert evaluator. "
        f"Given the following knowledge text, evaluate the user's answer to the question. "
        f"Use ONLY the knowledge text for evaluation. "
        f"Return a score from 0 (incorrect) to 1 (perfect) and a brief feedback on how the user answered "
        f"and give a very small hint on the answer for the next attempt.\n\n"
        f"Knowledge Text:\n{knowledge_text}\n\n"
        f"Question: {question}\n"
        f"User Answer: {user_answer}\n"
        f"Respond in JSON: {{\"score\": <float>, \"feedback\": <string>}}"
    )
    model = genai.GenerativeModel("gemini-2.5-flash")  # <-- changed
    response = model.generate_content(prompt)
    m = re.search(r'\{.*\}', response.text, re.S)
    if m:
        try:
            result = json.loads(m.group(0))
            return result
        except Exception:
            pass
    return {"score": 0, "feedback": "Could not evaluate answer."}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/info')
def course_info():
    return render_template('course_info.html')

@app.route('/course/<course_id>')
def course_quiz(course_id):
    """Render quiz page for a specific course"""
    course_data = load_course_data(course_id)
    if not course_data:
        return f"Course {course_id.upper()} not found", 404
    return render_template('index.html', course_id=course_id, course_title=course_data.get('title', course_id.upper()))

@app.route('/api/courses')
def list_courses():
    """List all available courses"""
    courses_dir = os.path.join(os.path.dirname(__file__), 'courses')
    if not os.path.exists(courses_dir):
        return jsonify({'courses': []})
    
    courses = []
    for filename in os.listdir(courses_dir):
        if filename.endswith('.json'):
            course_id = filename[:-5]  # Remove .json extension
            try:
                course_data = load_course_data(course_id)
                if course_data:
                    courses.append({
                        'id': course_id,
                        'title': course_data.get('title', course_id.upper()),
                        'description': course_data.get('description', ''),
                        'question_count': len(course_data.get('questions', []))
                    })
            except:
                continue
    
    return jsonify({'courses': courses})

@app.route('/api/<course_id>/check_user', methods=['POST'])
def check_user_course(course_id):
    """Check user for a specific course and provide course-specific questions"""
    course_data = load_course_data(course_id)
    if not course_data:
        return jsonify({'error': f'Course {course_id} not found'}), 404
    
    data = request.json
    username = data.get('username')
    full_name = data.get('full_name')
    if not username or not full_name:
        return jsonify({'error': 'username and full_name required'}), 400

    # Check for existing session for this course
    res = supabase.table('quiz_sessions').select('*').eq('username', username).eq('course_id', course_id).execute()
    if res.data and len(res.data) > 0:
        session = res.data[0]
        taken_count = session.get('taken_count', 0)

        # Case 1: max attempts reached
        if taken_count >= 3:
            return jsonify({'error': 'Max attempts reached', 'taken': True, 'taken_count': taken_count})

        # Case 2: already taken but still under limit → reset quiz automatically
        if session.get('taken'):
            questions = pick_random_questions(course_data, 5)
            now = datetime.now(timezone.utc).isoformat()

            supabase.table('quiz_sessions').update({
                'questions': json.dumps(questions),
                'answers': json.dumps([]),
                'score': None,
                'taken': False,
                'end_time': None,
                'start_time': now,
                'taken_count': taken_count + 1
            }).eq('username', username).eq('course_id', course_id).execute()

            return jsonify({'taken': False, 'questions': questions, 'taken_count': taken_count + 1, 'course_id': course_id})

        # Case 3: user has session but not yet taken
        return jsonify({
            'taken': False,
            'questions': json.loads(session.get('questions', '[]')),
            'taken_count': taken_count,
            'course_id': course_id
        })

    # Case 4: brand new user for this course
    questions = pick_random_questions(course_data, 5)
    questions_json = json.dumps(questions)
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        'username': username,
        'full_name': full_name,
        'course_id': course_id,
        'taken': False,
        'taken_count': 0,
        'start_time': now,
        'end_time': None,
        'questions': questions_json,
        'answers': json.dumps([]),
        'score': None,
        'total': len(questions)
    }
    supabase.table('quiz_sessions').insert(payload).execute()
    return jsonify({'taken': False, 'questions': questions, 'taken_count': 0, 'course_id': course_id})

@app.route('/api/check_user', methods=['POST'])
def check_user():
    """Original check_user endpoint - backward compatibility with default course"""
    # Try to load default course or fallback to original knowledge.json
    course_data = load_course_data('default')
    if not course_data:
        # Fallback to original knowledge.json for backward compatibility
        try:
            kb_path = os.path.join(os.path.dirname(__file__), 'knowledge.json')
            with open(kb_path, 'r', encoding='utf-8') as f:
                course_data = json.load(f)
        except:
            return jsonify({'error': 'No course data available'}), 500
    
    data = request.json
    username = data.get('username')
    full_name = data.get('full_name')
    if not username or not full_name:
        return jsonify({'error': 'username and full_name required'}), 400

    # Check for existing session (no course_id filter for backward compatibility)
    res = supabase.table('quiz_sessions').select('*').eq('username', username).execute()
    if res.data and len(res.data) > 0:
        session = res.data[0]
        taken_count = session.get('taken_count', 0)

        if taken_count >= 3:
            return jsonify({'error': 'Max attempts reached', 'taken': True, 'taken_count': taken_count})

        if session.get('taken'):
            questions = pick_random_questions(course_data, 5)
            now = datetime.now(timezone.utc).isoformat()

            supabase.table('quiz_sessions').update({
                'questions': json.dumps(questions),
                'answers': json.dumps([]),
                'score': None,
                'taken': False,
                'end_time': None,
                'start_time': now,
                'taken_count': taken_count + 1
            }).eq('username', username).execute()

            return jsonify({'taken': False, 'questions': questions, 'taken_count': taken_count + 1})

        return jsonify({
            'taken': False,
            'questions': json.loads(session.get('questions', '[]')),
            'taken_count': taken_count
        })

    # Brand new user
    questions = pick_random_questions(course_data, 5)
    questions_json = json.dumps(questions)
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        'username': username,
        'full_name': full_name,
        'course_id': 'default',
        'taken': False,
        'taken_count': 0,
        'start_time': now,
        'end_time': None,
        'questions': questions_json,
        'answers': json.dumps([]),
        'score': None,
        'total': len(questions)
    }
    supabase.table('quiz_sessions').insert(payload).execute()
    return jsonify({'taken': False, 'questions': questions, 'taken_count': 0})

@app.route('/api/<course_id>/finalize', methods=['POST'])
def finalize_course(course_id):
    """Finalize quiz for a specific course"""
    course_data = load_course_data(course_id)
    if not course_data:
        return jsonify({'error': f'Course {course_id} not found'}), 404
    
    data = request.json
    username = data.get('username')
    user_answers = data.get('answers')  # List of {index, question, answer}
    if not username or not user_answers:
        return jsonify({'error': 'username and answers required'}), 400

    # Evaluate all answers using Gemini and course-specific knowledge text
    knowledge_text = course_data.get('knowledgetext', '')
    evaluated_answers = []
    score_sum = 0
    for a in user_answers:
        question = a.get('question')
        answer = a.get('answer')
        index = a.get('index')
        result = evaluate_answer_gemini(answer, question, knowledge_text)
        score = float(result.get('score') or 0)
        score_sum += score
        evaluated_answers.append({
            'index': index,
            'question': question,
            'answer': answer,
            'score': score,
            'feedback': result.get('feedback')
        })

    total = len(user_answers)
    final_score = score_sum
    now = datetime.now(timezone.utc).isoformat()

    # Save to Supabase
    res = supabase.table('quiz_sessions').select('*').eq('username', username).eq('course_id', course_id).execute()
    if not res.data or len(res.data) == 0:
        return jsonify({'error': 'session not found'}), 404
    supabase.table('quiz_sessions').update({
        'answers': json.dumps(evaluated_answers),
        'taken': True,
        'end_time': now,
        'score': final_score
    }).eq('username', username).eq('course_id', course_id).execute()

    return jsonify({'final_score': final_score, 'total': total, 'answers': evaluated_answers})


@app.route('/api/finalize', methods=['POST'])
def finalize():
    """Original finalize endpoint - backward compatibility with default course"""
    # Try to load default course or fallback to original knowledge.json
    course_data = load_course_data('default')
    if not course_data:
        # Fallback to original knowledge.json for backward compatibility
        try:
            kb_path = os.path.join(os.path.dirname(__file__), 'knowledge.json')
            with open(kb_path, 'r', encoding='utf-8') as f:
                course_data = json.load(f)
        except:
            return jsonify({'error': 'No course data available'}), 500
    
    data = request.json
    username = data.get('username')
    user_answers = data.get('answers')  # List of {index, question, answer}
    if not username or not user_answers:
        return jsonify({'error': 'username and answers required'}), 400

    # Evaluate all answers using Gemini and knowledge text
    knowledge_text = course_data.get('knowledgetext', '')
    evaluated_answers = []
    score_sum = 0
    for a in user_answers:
        question = a.get('question')
        answer = a.get('answer')
        index = a.get('index')
        result = evaluate_answer_gemini(answer, question, knowledge_text)
        score = float(result.get('score') or 0)
        score_sum += score
        evaluated_answers.append({
            'index': index,
            'question': question,
            'answer': answer,
            'score': score,
            'feedback': result.get('feedback')
        })

    total = len(user_answers)
    final_score = score_sum
    now = datetime.now(timezone.utc).isoformat()

    # Save to Supabase
    res = supabase.table('quiz_sessions').select('*').eq('username', username).execute()
    if not res.data or len(res.data) == 0:
        return jsonify({'error': 'session not found'}), 404
    supabase.table('quiz_sessions').update({
        'answers': json.dumps(evaluated_answers),
        'taken': True,
        'end_time': now,
        'score': final_score
    }).eq('username', username).execute()

    return jsonify({'final_score': final_score, 'total': total, 'answers': evaluated_answers})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
