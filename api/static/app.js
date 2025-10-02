let username = "";
let questions = [];
let userAnswers = [];
let currentIndex = 0;
let timerInterval;
let timeLeft = 300; // 5 minutes
let selectedCourse = null;

// Cache DOM elements safely
const courseSelectionScreen = document.getElementById("course-selection-screen");
const courseList = document.getElementById("course-list");
const loginScreen = document.getElementById("login-screen");
const quizScreen = document.getElementById("quiz-screen");
const questionContainer = document.getElementById("question-container");
const evaluationDiv = document.getElementById("evaluation");
const resultScreen = document.getElementById("result-screen");
const resultDetails = document.getElementById("result-details");
const timerElement = document.getElementById("timer");
const courseTitleElement = document.getElementById("course-title");

// Course selection functions
async function loadCourses() {
    try {
        const response = await fetch('/api/courses');
        const data = await response.json();
        displayCourses(data.courses);
    } catch (error) {
        console.error('Failed to load courses:', error);
        if (courseList) {
            courseList.innerHTML = '<div class="error">Failed to load courses</div>';
        }
    }
}

function displayCourses(courses) {
    if (!courseList) return;
    
    if (courses.length === 0) {
        courseList.innerHTML = '<div class="error">No courses available</div>';
        return;
    }

    courseList.innerHTML = courses.map(course => `
        <div class="course-card" onclick="selectCourse('${course.id}', '${course.title}')">
            <h3>${course.title}</h3>
            <p>${course.description}</p>
            <small>${course.question_count} questions available</small>
        </div>
    `).join('');
}

function selectCourse(courseId, courseTitle) {
    selectedCourse = courseId;
    if (courseSelectionScreen) courseSelectionScreen.classList.add('hidden');
    if (loginScreen) loginScreen.classList.remove('hidden');
    if (courseTitleElement) courseTitleElement.textContent = `Welcome to ${courseTitle}`;
}

function goBackToCourses() {
    if (loginScreen) loginScreen.classList.add('hidden');
    if (courseSelectionScreen) courseSelectionScreen.classList.remove('hidden');
    selectedCourse = null;
}

function updateTimer() {
    const minutes = Math.floor(timeLeft / 60);
    const seconds = timeLeft % 60;
    if (timerElement) {
        timerElement.textContent = `${minutes.toString().padStart(2, "0")}:${seconds
            .toString()
            .padStart(2, "0")}`;
    }
}

function showQuestion() {
    if (currentIndex >= questions.length) {
        finalizeQuiz();
        return;
    }

    const qObj = questions[currentIndex];
    const questionText = typeof qObj === "string" ? qObj : qObj.q;

    if (questionContainer) {
        questionContainer.innerHTML = `
            <div class="question-card fade-in">
                <h3>Question ${currentIndex + 1}</h3>
                <p>${questionText}</p>
                <textarea id="answer" rows="4" placeholder="Your answer..."></textarea>
                <button id="submit-btn">Submit</button>
            </div>
        `;
    }
    if (evaluationDiv) evaluationDiv.innerHTML = "";

    const submitBtn = document.getElementById("submit-btn");
    if (submitBtn) submitBtn.onclick = submitAnswer;
}

function submitAnswer() {
    const answerBox = document.getElementById("answer");
    if (!answerBox) return;

    const answer = answerBox.value.trim();
    if (!answer) return;

    const qObj = questions[currentIndex];
    const questionText = typeof qObj === "string" ? qObj : qObj.q;

    userAnswers.push({
        index: currentIndex,
        question: questionText,
        answer: answer
    });

    currentIndex++;
    showQuestion();
}

async function finalizeQuiz() {
    clearInterval(timerInterval);
    if (quizScreen) quizScreen.classList.add("hidden");
    if (resultScreen) resultScreen.classList.remove("hidden");

    if (resultDetails) {
        resultDetails.innerHTML = `<div class="loader">Generating result...</div>`;
    }

    try {
        const endpoint = selectedCourse ? `/api/${selectedCourse}/finalize` : '/api/finalize';
        const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, answers: userAnswers }),
        });
        const data = await res.json();

        if (resultDetails) {
            resultDetails.innerHTML = `<p>Score: ${data.final_score} / ${data.total}</p>`;
            data.answers.forEach((a) => {
                resultDetails.innerHTML += `<div><strong>Q${a.index + 1}:</strong> ${a.feedback} (Score: ${a.score})</div>`;
            });
        }
    } catch (err) {
        if (resultDetails) {
            resultDetails.innerHTML = `<div class="fade-in error">Something went wrong. Please try again.</div>`;
        }
    }
}

function startQuiz(quizQuestions) {
    if (loginScreen) loginScreen.classList.add("hidden");
    if (quizScreen) quizScreen.classList.remove("hidden");
    
    questions = quizQuestions;
    userAnswers = [];
    currentIndex = 0;
    timeLeft = 300;
    updateTimer();
    
    timerInterval = setInterval(function () {
        timeLeft--;
        updateTimer();
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            finalizeQuiz();
        }
    }, 1000);
    
    showQuestion();
}

// Quiz form (prevent refresh)
// const quizForm = document.getElementById("quizForm");
// if (quizForm) {
//     quizForm.addEventListener("submit", function (e) {
//         e.preventDefault();
//     });
// }

// Login handling
document.addEventListener("DOMContentLoaded", function () {
    // Check if we're on a course-specific page or need course selection
    const urlPath = window.location.pathname;
    const courseMatch = urlPath.match(/^\/course\/([^\/]+)$/);
    
    if (courseMatch) {
        // Direct course access - skip course selection
        selectedCourse = courseMatch[1];
        if (courseSelectionScreen) courseSelectionScreen.classList.add('hidden');
        if (loginScreen) loginScreen.classList.remove('hidden');
        if (courseTitleElement) courseTitleElement.textContent = `Welcome to ${selectedCourse.toUpperCase()}`;
    } else {
        // Show course selection
        loadCourses();
    }

    // Back to courses button
    const backToCoursesBtn = document.getElementById("back-to-courses");
    if (backToCoursesBtn) {
        backToCoursesBtn.addEventListener("click", goBackToCourses);
    }

    const loginForm = document.getElementById("login-form");
    const retakeBtn = document.getElementById("retake-btn");

    if (loginForm) {
        loginForm.addEventListener("submit", function (event) {
            event.preventDefault();

            username = document.getElementById("username").value;
            const fullNameInput = document.getElementById("full_name") || document.getElementById("fullName");
            const fullName = fullNameInput ? fullNameInput.value : "";

            const endpoint = selectedCourse ? `/api/${selectedCourse}/check_user` : '/api/check_user';
            
            fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, full_name: fullName })
            })
                .then(res => res.json())
                .then(data => {
                    const msgDiv = document.getElementById("login-message");

                    if (data.error) {
                        msgDiv.textContent = data.error;
                    } else if (data.taken) {
                        msgDiv.textContent = data.message + ` (Attempts: ${data.taken_count}/3)`;
                    } else {
                        startQuiz(data.questions);
                    }
                })
                .catch(err => {
                    console.error("Error in check_user:", err);
                    document.getElementById("login-message").textContent = "Error connecting to server.";
                });
        });
    }

    if (retakeBtn) {
        retakeBtn.addEventListener("click", function () {
            fetch("/api/retake", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username })
            })
                .then(res => res.json())
                .then(data => {
                    const msgDiv = document.getElementById("retake-message");
                    if (data.error) {
                        msgDiv.textContent = data.error;
                    } else {
                        msgDiv.textContent = "";
                        startQuiz(data.questions);
                    }
                })
                .catch(err => {
                    console.error("Error in /api/retake:", err);
                    document.getElementById("retake-message").textContent = "Error connecting to server.";
                });
        });
    }
});

// Helper to start quiz
function startQuiz(questionsData) {
    document.getElementById("login-screen").classList.add("hidden");
    quizScreen.classList.remove("hidden");
    resultScreen.classList.add("hidden");

    questions = questionsData;
    userAnswers = [];
    currentIndex = 0;
    timeLeft = 300;
    updateTimer();

    timerInterval = setInterval(function () {
        timeLeft--;
        updateTimer();
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            finalizeQuiz();
        }
    }, 1000);

    showQuestion();
}