# Multi-Course Quiz System Enhancement

This enhancement adds support for multiple courses with separate JSON files and course-specific endpoints.

## Features

### ✨ **Multi-Course Support**
- Each course has its own JSON file with questions and knowledge text
- Course-specific user sessions and progress tracking
- Isolated quiz experiences per course

### 🎯 **Flexible Access Methods**
1. **Course Selection UI**: Browse all available courses at `/`
2. **Direct Course Access**: Go directly to `/course/{course_id}`
3. **API Integration**: Use course-specific endpoints

### 🔄 **Backward Compatibility**
- Original endpoints (`/api/check_user`, `/api/finalize`) still work
- Automatically uses `default.json` course or fallback to `knowledge.json`

## Quick Start

### 1. Add New Course
Create `api/courses/your_course.json`:
```json
{
    "title": "Your Course Title",
    "description": "Course description",
    "questions": [
        "Question 1?",
        "Question 2?"
    ],
    "knowledgetext": "Knowledge base for AI evaluation..."
}
```

### 2. Access Methods
- **Browse courses**: `http://localhost:5000/`
- **Direct access**: `http://localhost:5000/course/your_course`
- **API check**: `POST /api/your_course/check_user`
- **API submit**: `POST /api/your_course/finalize`

### 3. Database Changes
The `quiz_sessions` table now includes a `course_id` field to track sessions per course.

## API Endpoints

### Course Management
- `GET /api/courses` - List all available courses
- `GET /course/{course_id}` - Access course quiz page

### Course-Specific Operations
- `POST /api/{course_id}/check_user` - Check user for specific course
- `POST /api/{course_id}/finalize` - Submit quiz for specific course

### Backward Compatibility
- `POST /api/check_user` - Use default course
- `POST /api/finalize` - Use default course

## File Structure

```
api/
├── courses/
│   ├── a101.json       # Sample: Intro Programming
│   ├── a102.json       # Sample: Advanced Programming  
│   └── default.json    # Default/fallback course
├── index.py            # Enhanced Flask application
├── static/
│   ├── app.js         # Enhanced frontend with course selection
│   └── styles.css     # Updated styles with course cards
└── templates/
    ├── index.html     # Main quiz interface with course selection
    └── course_info.html # Documentation page
```

## Course JSON Format

```json
{
    "title": "Display name for the course",
    "description": "Brief description shown in course selection",
    "questions": [
        "Array of questions as strings"
    ],
    "knowledgetext": "Comprehensive knowledge base used by AI for evaluation"
}
```

## Examples

### Sample Courses Included
- **A101**: Introduction to Programming (basics, variables, loops)
- **A102**: Advanced Programming (OOP, data structures, algorithms)
- **Default**: General programming knowledge (fallback)

### Usage Examples

#### Course Selection Flow
1. User visits `/` → sees course selection screen
2. User clicks course → goes to login screen for that course
3. User enters credentials → gets course-specific questions
4. User completes quiz → results saved with course context

#### Direct Course Access
1. User visits `/course/a101` → directly to A101 login
2. System loads A101 questions and knowledge base
3. Quiz results are associated with A101 course

## Database Schema

The `quiz_sessions` table should include:
- `course_id` (string): Identifier for the course
- All existing fields remain the same

Users can have separate sessions for different courses.

## Benefits

1. **Scalability**: Easy to add new courses without code changes
2. **Isolation**: Each course has independent question pools and evaluation criteria  
3. **Flexibility**: Support both course selection UI and direct course access
4. **Compatibility**: Existing implementations continue to work
5. **Analytics**: Track performance per course separately

## Deployment Notes

- Ensure the `api/courses/` directory is deployed with your JSON files
- Update your database to include the `course_id` field if needed
- The system gracefully handles missing course files