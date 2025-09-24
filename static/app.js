let username = "";
let questions = [];
let userAnswers = [];
let currentIndex = 0;
let timerInterval;
let timeLeft = 300; // 5 minutes

const quizScreen = document.getElementById("quiz-screen");
const questionContainer = document.getElementById("question-container");
const evaluationDiv = document.getElementById("evaluation");
const resultScreen = document.getElementById("result-screen");
const resultDetails = document.getElementById("result-details");
const timerElement = document.getElementById("timer");

function updateTimer() {
    const minutes = Math.floor(timeLeft / 60);
    const seconds = timeLeft % 60;
    timerElement.textContent = `${minutes.toString().padStart(2, "0")}:${seconds
        .toString()
        .padStart(2, "0")}`;
}

function showQuestion() {
    if (currentIndex >= questions.length) {
        finalizeQuiz();
        return;
    }

    const qObj = questions[currentIndex];
    const questionText = typeof qObj === "string" ? qObj : qObj.q;

    questionContainer.innerHTML = `
        <div class="question-card fade-in">
            <h3>Question ${currentIndex + 1}</h3>
            <p>${questionText}</p>
            <textarea id="answer" rows="4" placeholder="Your answer..."></textarea>
            <button id="submit-btn">Submit</button>
        </div>
    `;
    evaluationDiv.innerHTML = "";

    document.getElementById("submit-btn").onclick = submitAnswer;
}

function submitAnswer() {
    const answer = document.getElementById("answer").value.trim();
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
    quizScreen.classList.add("hidden");
    resultScreen.classList.remove("hidden");

    // Show loader while evaluating
    resultDetails.innerHTML = `<div class="loader">Generating result...</div>`;

    // Send all answers for evaluation
    try {
        const res = await fetch("/api/finalize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, answers: userAnswers }),
        });
        const data = await res.json();

        // Show results
        resultDetails.innerHTML = `<p>Score: ${data.final_score} / ${data.total}</p>`;
        data.answers.forEach((a) => {
            resultDetails.innerHTML += `<div><strong>Q${a.index + 1}:</strong> ${a.feedback} (Score: ${a.score})</div>`;
        });
    } catch (err) {
        resultDetails.innerHTML = `<div class="fade-in error">Something went wrong. Please try again.</div>`;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function (event) {
            event.preventDefault();

            username = document.getElementById('username').value;
            const fullNameInput = document.getElementById('full_name') || document.getElementById('fullName');
            const fullName = fullNameInput ? fullNameInput.value : "";

            fetch('/api/check_user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, full_name: fullName })
            })
            .then(res => res.json())
            .then(data => {
                const msgDiv = document.getElementById('login-message');
                if (data.error) {
                    msgDiv.textContent = data.error;
                } else if (data.taken) {
                    msgDiv.textContent = data.message;
                } else {
                    document.getElementById('login-screen').classList.add('hidden');
                    quizScreen.classList.remove('hidden');
                    questions = data.questions;
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
            })
            .catch(err => {
                document.getElementById('login-message').textContent = 'Error connecting to server.';
            });
        });
    }
});