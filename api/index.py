import os
import json
import random
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from supabase import create_client
from dotenv import load_dotenv
import google.generativeai as genai
import re
from functools import wraps

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

# Set a secret key for session management - in production, use environment variable
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Admin credentials - in production, use environment variables or database
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')


# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

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

def generate_questions_with_gemini(knowledge_text, n=5):
    """Generate n questions using Gemini based on the knowledge text."""
    prompt = (
        f"Based on the following knowledge text, generate exactly {n} educational questions. "
        f"The questions should test understanding of key concepts and be answerable using the provided text.\n\n"
        f"Knowledge Text:\n{knowledge_text}\n\n"
        f"IMPORTANT: Respond with ONLY a valid JSON array of {n} strings, nothing else. "
        f"Format: [\"Question 1?\", \"Question 2?\", \"Question 3?\", \"Question 4?\", \"Question 5?\"]"
    )
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')  # Updated model name
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Clean up the response - remove markdown code blocks if present
        clean_response = response_text.replace('```json', '').replace('```', '').strip()
        
        # Try to find JSON array in the response
        import re
        json_match = re.search(r'\[.*?\]', clean_response, re.DOTALL)
        if json_match:
            questions_json = json_match.group(0)
            try:
                questions = json.loads(questions_json)
                
                # Validate we got the right number of questions
                if isinstance(questions, list) and len(questions) >= 1:
                    # Take up to n questions
                    selected_questions = questions[:n]
                    return [{"q": q.strip()} for q in selected_questions]
            except json.JSONDecodeError:
                pass
        
        # Fallback: try to parse the entire clean response as JSON
        try:
            questions = json.loads(clean_response)
            if isinstance(questions, list) and len(questions) >= 1:
                selected_questions = questions[:n]
                return [{"q": q.strip()} for q in selected_questions]
        except json.JSONDecodeError:
            pass
            
    except Exception as e:
        pass  # Silently fall back to default questions
    
    # Final fallback
    return [
        {"q": "What are the main concepts covered in this topic?"},
        {"q": "How do the key elements relate to each other?"},
        {"q": "What are the most important points to understand?"},
        {"q": "Can you explain the significance of this subject matter?"},
        {"q": "What practical applications does this knowledge have?"}
    ]

def pick_random_questions(course_data, n=5):
    """Pick n random questions from the course data or generate them if none exist."""
    questions = course_data.get("questions", [])
    
    # If no questions are pre-loaded, generate them using Gemini
    if not questions or len(questions) == 0:
        knowledge_text = course_data.get("knowledgetext", "")
        if knowledge_text:
            return generate_questions_with_gemini(knowledge_text, n)
        else:
            return [
                {"q": "What are the main concepts in this course?"},
                {"q": "How do the key elements relate to each other?"},
                {"q": "What are the most important points to understand?"},
                {"q": "Can you explain the significance of this subject matter?"},
                {"q": "What practical applications does this knowledge have?"}
            ]
    
    # If we have pre-loaded questions, use them as before
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

# Admin routes
@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard showing all courses"""
    courses_dir = os.path.join(os.path.dirname(__file__), 'courses')
    courses = []
    
    if os.path.exists(courses_dir):
        for filename in os.listdir(courses_dir):
            if filename.endswith('.json'):
                course_id = filename[:-5]  # Remove .json extension
                course_data = load_course_data(course_id)
                if course_data:
                    courses.append({
                        'id': course_id,
                        'title': course_data.get('title', course_id),
                        'description': course_data.get('description', ''),
                        'questions_count': len(course_data.get('questions', []))
                    })
    
    return render_template('admin_dashboard.html', courses=courses)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/course/new', methods=['GET', 'POST'])
@admin_required
def admin_new_course():
    """Create new course form"""
    if request.method == 'POST':
        course_id = request.form.get('course_id').lower().strip()
        title = request.form.get('title')
        description = request.form.get('description')
        questions = request.form.get('questions').split('\n')
        knowledge_text = request.form.get('knowledge_text')
        
        # Validate input
        if not course_id or not title or not knowledge_text:
            flash('Course ID, Title, and Knowledge Text are required!', 'error')
            return render_template('admin_course_form.html')
        
        # Clean up questions list
        questions = [q.strip() for q in questions if q.strip()]
        
        # Questions are now optional - AI will generate if empty and knowledge text exists
        if len(questions) == 0 and not knowledge_text:
            flash('Either questions or knowledge text is required for AI generation!', 'error')
            return render_template('admin_course_form.html')
        
        # Create course data
        course_data = {
            'title': title,
            'description': description,
            'questions': questions,
            'knowledgetext': knowledge_text
        }
        
        # Save to file
        courses_dir = os.path.join(os.path.dirname(__file__), 'courses')
        os.makedirs(courses_dir, exist_ok=True)
        
        course_file = os.path.join(courses_dir, f'{course_id}.json')
        
        # Check if course already exists
        if os.path.exists(course_file):
            flash(f'Course {course_id} already exists!', 'error')
            return render_template('admin_course_form.html', 
                                 course_id=course_id, title=title, 
                                 description=description, 
                                 questions='\n'.join(questions),
                                 knowledge_text=knowledge_text)
        
        try:
            with open(course_file, 'w', encoding='utf-8') as f:
                json.dump(course_data, f, indent=4, ensure_ascii=False)
            
            flash(f'Course {course_id} created successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        except Exception as e:
            flash(f'Error saving course: {str(e)}', 'error')
            return render_template('admin_course_form.html', 
                                 course_id=course_id, title=title, 
                                 description=description, 
                                 questions='\n'.join(questions),
                                 knowledge_text=knowledge_text)
    
    return render_template('admin_course_form.html')

@app.route('/admin/course/<course_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_course(course_id):
    """Edit existing course"""
    course_data = load_course_data(course_id)
    if not course_data:
        flash('Course not found!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        questions = request.form.get('questions').split('\n')
        knowledge_text = request.form.get('knowledge_text')
        
        # Validate input
        if not title or not knowledge_text:
            flash('Title and Knowledge Text are required!', 'error')
            return render_template('admin_course_form.html', 
                                 course_id=course_id, 
                                 course_data=course_data, 
                                 edit_mode=True)
        
        # Clean up questions list
        questions = [q.strip() for q in questions if q.strip()]
        
        # Questions are now optional - AI will generate if empty and knowledge text exists
        if len(questions) == 0 and not knowledge_text:
            flash('Either questions or knowledge text is required for AI generation!', 'error')
            return render_template('admin_course_form.html', 
                                 course_id=course_id, 
                                 course_data=course_data, 
                                 edit_mode=True)
        
        # Update course data
        course_data['title'] = title
        course_data['description'] = description
        course_data['questions'] = questions
        course_data['knowledgetext'] = knowledge_text
        
        # Save to file
        courses_dir = os.path.join(os.path.dirname(__file__), 'courses')
        course_file = os.path.join(courses_dir, f'{course_id}.json')
        
        try:
            with open(course_file, 'w', encoding='utf-8') as f:
                json.dump(course_data, f, indent=4, ensure_ascii=False)
            
            flash(f'Course {course_id} updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        except Exception as e:
            flash(f'Error updating course: {str(e)}', 'error')
    
    return render_template('admin_course_form.html', 
                         course_id=course_id, 
                         course_data=course_data, 
                         edit_mode=True)

@app.route('/admin/course/<course_id>/delete', methods=['POST'])
@admin_required
def admin_delete_course(course_id):
    """Delete a course"""
    courses_dir = os.path.join(os.path.dirname(__file__), 'courses')
    course_file = os.path.join(courses_dir, f'{course_id}.json')
    
    if os.path.exists(course_file):
        try:
            os.remove(course_file)
            flash(f'Course {course_id} deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting course: {str(e)}', 'error')
    else:
        flash('Course not found!', 'error')
    
    return redirect(url_for('admin_dashboard'))

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
        existing_questions = json.loads(session.get('questions', '[]'))
        
        # Check if we have fallback questions and regenerate if needed
        if (existing_questions and len(existing_questions) > 0 and 
            existing_questions[0].get('q') == "What are the main concepts covered in this topic?"):
            # Regenerate questions with AI
            print("DEBUG: Detected fallback questions, regenerating with AI...")
            new_questions = pick_random_questions(course_data, 5)
            now = datetime.now(timezone.utc).isoformat()
            
            supabase.table('quiz_sessions').update({
                'questions': json.dumps(new_questions),
                'start_time': now
            }).eq('username', username).eq('course_id', course_id).execute()
            
            return jsonify({
                'taken': False,
                'questions': new_questions,
                'taken_count': taken_count,
                'course_id': course_id
            })
        
        return jsonify({
            'taken': False,
            'questions': existing_questions,
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
