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


# Load knowledge base
KB_PATH = os.path.join(os.path.dirname(__file__), 'knowledge.json')
with open(KB_PATH, 'r', encoding='utf-8') as f:
    KB = json.load(f)
QUESTIONS = KB["questions"]
KNOWLEDGE_TEXT = KB["knowledgetext"]

def pick_random_questions(n=5):
    """Pick n random questions from the knowledge base."""
    return [{"q": q} for q in random.sample(QUESTIONS, min(n, len(QUESTIONS)))]

def evaluate_answer_gemini(user_answer, question):
    """Use Gemini to evaluate the user's answer against the knowledge text."""
    prompt = (
        f"You are an expert evaluator. "
        f"Given the following knowledge text, evaluate the user's answer to the question. "
        f"Use ONLY the knowledge text for evaluation. "
        f"Return a score from 0 (incorrect) to 1 (perfect) and a brief feedback.\n\n"
        f"Knowledge Text:\n{KNOWLEDGE_TEXT}\n\n"
        f"Question: {question}\n"
        f"User Answer: {user_answer}\n"
        f"Respond in JSON: {{\"score\": <float>, \"feedback\": <string>}}"
    )
    model = genai.GenerativeModel('gemini-1.5-flash')
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

@app.route('/api/check_user', methods=['POST'])
def check_user():
    data = request.json
    username = data.get('username')
    full_name = data.get('full_name')
    if not username or not full_name:
        return jsonify({'error': 'username and full_name required'}), 400

    # Check in supabase if user exists
    res = supabase.table('quiz_sessions').select('*').eq('username', username).execute()
    if res.data and len(res.data) > 0:
        session = res.data[0]
        if session.get('taken'):
            return jsonify({'taken': True, 'message': 'You have already taken the quiz.', 'taken_count': session.get('taken_count', 1)})
        else:
            return jsonify({'taken': False, 'message': 'User has record but not marked taken. Continue.', 'questions': json.loads(session.get('questions', '[]')), 'taken_count': session.get('taken_count', 1)})

    # Pick random questions for this session
    questions = pick_random_questions(5)
    questions_json = json.dumps(questions)
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        'username': username,
        'full_name': full_name,
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


@app.route('/api/retake', methods=['POST'])
def retake():
    data = request.json
    username = data.get('username')
    if not username:
        return jsonify({'error': 'username required'}), 400

    res = supabase.table('quiz_sessions').select('*').eq('username', username).execute()
    if not res.data or len(res.data) == 0:
        return jsonify({'error': 'session not found'}), 404

    session = res.data[0]
    taken_count = session.get('taken_count', 0)

    if taken_count >= 3:
        return jsonify({'error': 'Max attempts reached'}), 400

    # Pick new random questions
    questions = pick_random_questions(5)
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

    return jsonify({'success': True, 'questions': questions, 'taken_count': taken_count + 1})


@app.route('/api/finalize', methods=['POST'])
def finalize():
    data = request.json
    username = data.get('username')
    user_answers = data.get('answers')  # List of {index, question, answer}
    if not username or not user_answers:
        return jsonify({'error': 'username and answers required'}), 400

    # Evaluate all answers using Gemini and knowledgetext
    evaluated_answers = []
    score_sum = 0
    for a in user_answers:
        question = a.get('question')
        answer = a.get('answer')
        index = a.get('index')
        result = evaluate_answer_gemini(answer, question)
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
