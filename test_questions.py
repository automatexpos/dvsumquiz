import sys
import os
sys.path.insert(0, 'api')

from dotenv import load_dotenv
load_dotenv()

from index import load_course_data, pick_random_questions

print("Testing ML Auto course question generation...")

# Load course
course_data = load_course_data('ml_auto')
if course_data:
    print(f"✓ Course loaded: {course_data['title']}")
    print(f"✓ Questions in file: {len(course_data['questions'])}")
    print(f"✓ Knowledge text length: {len(course_data['knowledgetext'])}")
    
    # Test question generation
    print("\nTesting question generation...")
    questions = pick_random_questions(course_data, 5)
    
    print(f"\nGenerated {len(questions)} questions:")
    for i, q in enumerate(questions, 1):
        print(f"{i}. {q['q']}")
else:
    print("✗ Failed to load course")