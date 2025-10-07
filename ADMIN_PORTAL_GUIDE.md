# Admin Portal Setup and Usage Guide

## Overview
This admin portal provides a web-based interface for managing quiz courses. Administrators can login, view all courses, create new courses, edit existing ones, and delete courses as needed.

## Features
- **Secure Login**: Username/password authentication with session management
- **Dashboard**: Overview of all courses with statistics
- **Course Management**: Create, edit, and delete quiz courses
- **Form Validation**: Client-side and server-side validation
- **Responsive Design**: Works on desktop and mobile devices
- **Vercel Compatible**: Designed to work with Vercel deployment

## Default Admin Credentials
- **Username**: `admin`
- **Password**: `admin123`

⚠️ **IMPORTANT**: Change these credentials before deploying to production!

## How to Change Admin Credentials

### Method 1: Environment Variables (Recommended for Production)
Set these environment variables in your Vercel dashboard or deployment environment:
```
ADMIN_USERNAME=your_chosen_username
ADMIN_PASSWORD=your_secure_password
SECRET_KEY=your_secret_session_key
```

### Method 2: Direct Code Modification (For Development Only)
In `api/index.py`, modify these lines:
```python
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'your_username')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'your_password')
```

## Accessing the Admin Portal

### Local Development
1. Start the Flask app: `python api/index.py`
2. Open browser and go to: `http://localhost:5000/admin`
3. You'll be redirected to the login page if not authenticated
4. Login with the credentials above

### Production (Vercel)
1. Go to your deployed URL + `/admin` (e.g., `https://yourapp.vercel.app/admin`)
2. Login with your configured credentials

## Using the Admin Portal

### 1. Dashboard
- View all existing courses
- See total statistics (courses, questions, etc.)
- Quick access to create, edit, view, or delete courses

### 2. Creating a New Course
1. Click "New Course" button on dashboard
2. Fill in the form:
   - **Course ID**: Unique identifier (lowercase, numbers, hyphens, underscores only)
   - **Title**: Display name for the course
   - **Description**: Brief description of the course content
   - **Questions**: One question per line OR leave empty for AI generation 🤖
   - **Knowledge Text**: Comprehensive reference material for AI evaluation and question generation

3. **Question Options**:
   - **Manual**: Write your own questions for full control
   - **AI-Generated**: Leave empty and AI creates questions from knowledge text
   - **Mixed**: Provide some questions, AI fills gaps if needed

4. Click "Create Course" to save

### 3. Editing an Existing Course
1. Click "Edit" button on any course card
2. Modify the fields as needed
3. Click "Update Course" to save changes

### 4. Deleting a Course
1. Click "Delete" button on any course card
2. Confirm the deletion in the popup modal
3. The course file will be permanently deleted

## Course File Structure
Each course is stored as a JSON file in the `api/courses/` directory with this structure:
```json
{
    "title": "Course Title",
    "description": "Course description",
    "questions": [
        "Question 1?",
        "Question 2?",
        "Question 3?"
    ],
    "knowledgetext": "Comprehensive reference material that the AI uses to evaluate answers..."
}
```

### 🤖 AI Question Generation
**NEW FEATURE**: If the `questions` array is empty or not provided, the system will automatically generate 5 diverse questions using Gemini AI based on the `knowledgetext`. This allows for:
- **Dynamic Content**: Fresh questions every time based on your knowledge base
- **Reduced Manual Work**: No need to write questions manually
- **Intelligent Variety**: AI creates diverse question types and difficulty levels

## Best Practices for Course Creation

### Question Management Options

#### Option 1: Manual Questions (Traditional)
- Write specific questions in the questions field
- One question per line
- Full control over question content and difficulty
- Questions are randomly selected from your list

#### Option 2: AI-Generated Questions (New!)
- Leave the questions field empty
- AI will generate 5 diverse questions from your knowledge text
- Questions are created dynamically using Gemini AI
- Provides variety and reduces manual effort

#### Option 3: Hybrid Approach
- Provide some manual questions for key topics
- If fewer than 5 questions, AI will supplement with generated ones
- Best of both worlds: control + automation

### Writing Good Manual Questions
- Make questions clear and specific
- Focus on understanding rather than memorization
- Use varied question types (what, how, why, compare, explain)
- Ensure questions can be answered using the knowledge text

### Knowledge Text Guidelines
- Include comprehensive information about all topics
- Write in clear, detailed prose
- Cover all concepts that questions might reference
- Aim for at least 500 characters for effective AI evaluation
- **For AI generation**: Rich knowledge text produces better questions

### Course ID Naming
- Use descriptive but short identifiers
- Follow format: `subject###` (e.g., `math101`, `python_basics`)
- Avoid spaces and special characters
- Keep it under 20 characters

## Security Considerations

### For Production Deployment:
1. **Change default credentials** using environment variables
2. **Set a secure SECRET_KEY** for session encryption
3. **Use HTTPS** (automatic with Vercel)
4. **Regularly update passwords**
5. **Monitor access logs** if available

### Session Management:
- Sessions expire when browser is closed
- No persistent "remember me" option for security
- Multiple admin users can be logged in simultaneously

## Troubleshooting

### Cannot Access Admin Portal
- Check if you're using the correct URL (`/admin`)
- Verify credentials are correct
- Clear browser cookies/session data

### Course Creation Fails
- Ensure Course ID is unique and follows naming rules
- Check that all required fields are filled
- Verify questions are entered one per line
- Ensure knowledge text is substantial

### File Permissions Issues
- Ensure the `api/courses/` directory is writable
- Check that the application has permission to create/modify files

## Vercel Deployment Notes

The admin portal is fully compatible with Vercel serverless deployment:
- All admin routes are properly configured
- File operations work with Vercel's file system
- Environment variables are supported
- Static files (CSS, JS) are served correctly

No additional configuration is needed beyond setting environment variables for production credentials.

## Support

If you encounter issues:
1. Check the browser console for JavaScript errors
2. Verify all environment variables are set correctly
3. Ensure the Flask app is running without errors
4. Check file permissions in the courses directory