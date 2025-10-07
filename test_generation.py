import sys
import os

# Add the api directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from index import generate_questions_with_gemini, load_course_data

# Test the ML course
course_data = load_course_data('ml_auto')
if course_data:
    print("Course data loaded successfully:")
    print(f"Title: {course_data['title']}")
    print(f"Questions count: {len(course_data['questions'])}")
    print(f"Knowledge text length: {len(course_data['knowledgetext'])}")
    
    print("\nTesting question generation...")
    questions = generate_questions_with_gemini(course_data['knowledgetext'], 5)
    print(f"Generated questions: {questions}")
else:
    print("Failed to load course data")