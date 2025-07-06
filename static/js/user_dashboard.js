const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
let transcriptionLines = [];
let isPaused = false;
let silenceTimer;
let lastSavedText = ""; // Track the last saved transcription
let accumulatedTranscription = ""; // Accumulate the transcription until stop is clicked
let transcriptionMode = "mic"; // Default mode is microphone

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;  
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;
} else {
    alert("Sorry, your browser doesn't support speech recognition.");
}

function startTranscription() {
    if (isPaused) {
        resumeTranscription();
    } else {
        isPaused = false; 
        recognition.start();
        displayTranscription("🎤 Listening...");
        toggleButtons("pause"); // Ensure buttons reflect "pause" state
    }

    recognition.onresult = (event) => {
        let interimTranscript = "";
        let finalTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript + " ";
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }

        if (finalTranscript) {
            accumulatedTranscription += finalTranscript.trim() + " "; // Accumulate the final transcript
            displayTranscription(accumulatedTranscription.trim()); // Display the accumulated transcription
        } else {
            updateCurrentTranscription(interimTranscript);
        }
    };

    recognition.onerror = (event) => {
        console.error("Speech Recognition Error:", event.error);
        displayTranscription("⚠ Error: " + event.error);
    };
}

function resetSilenceTimer(text) {
    clearTimeout(silenceTimer);
    silenceTimer = setTimeout(() => {
        if (text.trim() && text.trim() !== lastSavedText) { // Avoid saving duplicate text
            transcriptionLines.push(text.trim()); // Add the full transcription to the lines
            saveTranscription(transcriptionLines.join(" ")); // Save the combined transcription
            lastSavedText = transcriptionLines.join(" "); // Update the last saved text
            transcriptionLines = []; // Clear the lines after saving
        }
    }, 5000); // Trigger after 5 seconds of silence
}

function stopTranscription() {
    recognition.stop();
    isPaused = true;

    console.log("Stopping transcription and saving the final text."); // Debug log

    storeFinalText(accumulatedTranscription.trim()).then(() => {
        checkFactStatus().then(() => {
            fetchAlerts().then(() => {
                fetchResolvedAlerts().then(() => {
                    // Refresh the page after fetching alerts and resolved alerts
                    location.reload();
                });
            });
        });
    });

    accumulatedTranscription = ""; // Clear the accumulated transcription after saving
    toggleButtons("start"); // Ensure buttons reflect "start" state after stopping
}

function togglePauseResume() {
    if (!isPaused) {
        recognition.stop();
        isPaused = true;
        document.getElementById("pause-btn").innerText = "Resume";
        displayTranscription("⏸ Paused...");
        toggleButtons("stop"); // Update buttons to reflect "stop" state
    } else {
        resumeTranscription();
    }
}

function resumeTranscription() {
    recognition.start();
    isPaused = false;
    document.getElementById("pause-btn").innerText = "Pause";
    displayTranscription("🎤 Listening...");
}

async function saveTranscription(text) {
    if (!text.trim()) return;

    try {
        let response = await fetch('/save_transcription', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcription: text })
        });

        let data = await response.json();
        console.log("Saved Transcription:", data);
    } catch (error) {
        console.error("Error saving transcription:", error);
    }
}

async function storeFinalText(text) {
    try {
        let response = await fetch('/store-final-transcription', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcription: text })
        });

        let data = await response.json();
        console.log("Final Text Saved:", data);

        // ✅ Automatically trigger fact-checking after saving the final text
        setTimeout(checkFactStatus, 2000); 

    } catch (error) {
        console.error("Error saving final text:", error);
    }
}

function displayTranscription(text) {
    document.getElementById('transcription-text').innerText = text;
}

function updateCurrentTranscription(transcript) {
    document.getElementById('transcription-text').innerText = transcript;
}

function addFinalTranscription(transcript) {
    transcriptionLines.push(transcript); // Add the transcript to the lines
    displayTranscription(transcriptionLines.join(" ")); // Display the combined transcription
}

function toggleButtons(action) {
    if (action === "start") {
        document.getElementById("start-btn").style.display = "inline-block";
        document.getElementById("pause-btn").style.display = "none";
        document.getElementById("stop-btn").style.display = "none";
    } else if (action === "pause") {
        document.getElementById("start-btn").style.display = "none";
        document.getElementById("pause-btn").style.display = "inline-block";
        document.getElementById("stop-btn").style.display = "inline-block";
    } else if (action === "stop") {
        document.getElementById("start-btn").style.display = "inline-block";
        document.getElementById("pause-btn").style.display = "none";
        document.getElementById("stop-btn").style.display = "none";
    }
}

document.getElementById("stopButton").addEventListener("click", function() {
    stopTranscription();
});

async function checkFactStatus() {
    try {
        let response = await fetch('/fact-check', { method: 'GET' });
        let data = await response.json();

        console.log("Fact-Check Triggered:", data);

        setTimeout(updateFactStatus, 3000); // Wait & update status after checking
    } catch (error) {
        console.error("Error checking fact status:", error);
    }
}

async function updateFactStatus() {
    try {
        const response = await fetch('/fact-status');
        const data = await response.json();
        
        if (data.error) {
            document.getElementById("fact-status").innerHTML = "No status available.";
        } else {
            document.getElementById("fact-status").innerHTML = `
                <strong>Status:</strong> ${data.status} <br>
                <strong>Match Type:</strong> ${data.match_type} <br>
                <strong>Matched Fact:</strong> ${data.matched_fact || "N/A"}
            `;
        }
    } catch (error) {
        console.error("Error fetching fact status:", error);
    }
}

async function fetchAlerts() {
    const response = await fetch('/api/alerts');
    const alerts = await response.json();

    const alertsSection = document.getElementById('alerts-section');
    alertsSection.innerHTML = alerts.length ? '' : '<p>No alerts yet.</p>';

    alerts.forEach(alert => {
        if (alert.fact_status === "Unverified") { // Display only unverified facts
            const alertDiv = document.createElement('div');
            alertDiv.classList.add('alert-item');
            alertDiv.innerHTML = `
                <p><strong>${alert.full_text}</strong> - Status: ${alert.fact_status}</p>
                <button class="resolve-btn" onclick="resolveAlert('${alert._id}')">Resolve</button>
            `;
            alertsSection.appendChild(alertDiv);
        }
    });
}

async function resolveAlert(alertId) {
    try {
        const response = await fetch(`/api/resolve_alert/${alertId}`, { method: 'PUT' });
        if (response.ok) {
            fetchAlerts();
            fetchResolvedAlerts();
        } else {
            showNotification('Failed to resolve alert.', 'error');
        }
    } catch (error) {
        console.error('Error resolving alert:', error);
        showNotification('Error resolving alert.', 'error');
    }
}

async function fetchResolvedAlerts() {
    try {
        const response = await fetch('/api/resolved_alerts');
        const resolvedAlerts = await response.json();

        const resolvedSection = document.getElementById('resolved-alerts-list');
        resolvedSection.innerHTML = resolvedAlerts.length ? '' : '<p>No resolved alerts yet.</p>';

        resolvedAlerts.forEach(alert => {
            const alertItem = document.createElement('li');
            alertItem.innerHTML = `
                <p><strong>${alert.full_text}</strong></p>
                <p><strong>Resolved Type:</strong> ${alert.match_type}</p>
            `;
            resolvedSection.appendChild(alertItem);
        });
    } catch (error) {
        console.error('Error fetching resolved alerts:', error);
        showNotification('Error fetching resolved alerts.', 'error');
    }
}

async function fetchFacts() {
    const response = await fetch('/api/facts');
    const facts = await response.json();

    const factStatusDiv = document.getElementById('fact-status-list');
    factStatusDiv.innerHTML = facts.length ? '' : '<p>No facts available.</p>';

    facts.forEach(fact => {
        const factItem = document.createElement('li');
        factItem.innerHTML = `
            <p><strong>${fact.full_text}</strong></p>
            <p><strong>Status:</strong> ${fact.fact_status}</p>
            <p><strong>Resolved:</strong> ${fact.resolve}</p>
        `;
        factStatusDiv.appendChild(factItem);
    });
}

async function submitFact(event) {
    event.preventDefault();
    const factInput = document.getElementById('fact-input').value;

    try {
        const response = await fetch('/check-fact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fact: factInput })
        });

        if (response.ok) {
            const result = await response.json();
            showNotification(result.message, 'success');
            fetchAlerts();
            fetchResolvedAlerts();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to check fact.', 'error');
        }
    } catch (error) {
        console.error('Error checking fact:', error);
        showNotification('Error checking fact.', 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchAlerts();
    fetchResolvedAlerts();
    fetchFacts();
    fetchAllFacts(); // Fetch all facts on page load
});

function handlePanel1Click() {
    console.log("Panel 1 clicked");
    // Add your logic for Panel 1 click here
}

function redirectToTextFact() {
    window.location.href = "/text_fact";
}

function handlePanel2Click() {
    console.log("Panel 2 clicked");
    // Add your logic for Panel 2 click here
}

// 🔄 Refresh fact-check status every 5 seconds
setInterval(updateFactStatus, 5000);

async function uploadAudio(file) {
    const formData = new FormData();
    formData.append("audio", file);

    try {
        const response = await fetch('/upload-audio', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (response.ok) {
            console.log("Transcription:", data.transcription);
            displayTranscription(data.transcription); // Display the transcription
        } else {
            console.error("Error:", data.error);
            displayTranscription("⚠ Error: " + data.error);
        }
    } catch (error) {
        console.error("Error uploading audio:", error);
        displayTranscription("⚠ Error uploading audio");
    }
}

// Example usage: Call `uploadAudio` with an audio file
document.getElementById("audio-upload").addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (file) {
        uploadAudio(file);
    }
});

function showNotification(message, type = 'success') {
    const notificationContainer = document.getElementById('notification-container');
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerText = message;

    notificationContainer.appendChild(notification);

    // Automatically remove the notification after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

async function fetchVerifiedFacts() {
    try {
        console.log("🔹 Fetching verified facts..."); // Debugging: Log the start of the fetch
        const response = await fetch('/api/verified_facts');

        if (!response.ok) {
            console.error(`❌ Error: Received status ${response.status}`); // Debugging: Log HTTP status
            const error = await response.json();
            throw new Error(error.error || "Failed to fetch verified facts.");
        }

        const verifiedFacts = await response.json();
        console.log("🔹 Verified Facts Received:", verifiedFacts); // Debugging: Log the fetched data

        const verifiedFactsList = document.getElementById('verified-facts-list');
        verifiedFactsList.innerHTML = verifiedFacts.length ? '' : '<p>No verified facts available.</p>';

        verifiedFacts.forEach(fact => {
            const factItem = document.createElement('li');
            factItem.innerHTML = `
                <p><strong>Category:</strong> ${fact.category || 'N/A'}</p>
                <p><strong>Fact:</strong> ${fact.full_text || 'N/A'}</p>
                <p><strong>Timestamp:</strong> ${fact.timestamp ? new Date(fact.timestamp).toLocaleString() : 'N/A'}</p>
            `;
            verifiedFactsList.appendChild(factItem);
        });
    } catch (error) {
        console.error('❌ Error fetching verified facts:', error); // Debugging: Log any errors
        const verifiedFactsList = document.getElementById('verified-facts-list');
        verifiedFactsList.innerHTML = '<p>Error loading verified facts. Please try again later.</p>';
    }
}

async function fetchAllFacts() {
    try {
        console.log("🔹 Fetching all facts..."); // Debugging: Log the start of the fetch
        const response = await fetch('/api/all_facts');

        if (!response.ok) {
            console.error(`❌ Error: Received status ${response.status}`); // Debugging: Log HTTP status
            const error = await response.json();
            throw new Error(error.error || "Failed to fetch all facts.");
        }

        const allFacts = await response.json();
        console.log("🔹 All Facts Received:", allFacts); // Debugging: Log the fetched data

        const factsList = document.getElementById('all-facts-list');
        factsList.innerHTML = allFacts.length ? '' : '<p>No facts available.</p>';

        allFacts.forEach(fact => {
            const factItem = document.createElement('li');
            factItem.innerHTML = `
                <p><strong>Fact:</strong> ${fact.full_text || 'N/A'}</p>
                <p><strong>Status:</strong> ${fact.fact_status || 'Unverified'}</p>
                <p><strong>Timestamp:</strong> ${fact.timestamp ? new Date(fact.timestamp).toLocaleString() : 'N/A'}</p>
            `;
            factsList.appendChild(factItem);
        });
    } catch (error) {
        console.error('❌ Error fetching all facts:', error); // Debugging: Log any errors
        const factsList = document.getElementById('all-facts-list');
        factsList.innerHTML = '<p>Error loading facts. Please try again later.</p>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchAlerts();
    fetchResolvedAlerts();
    fetchFacts();
    fetchAllFacts(); // Fetch all facts on page load
});

// Initialize WebSocket connection
const socket = io();

// Listen for 'resolved_alerts_cleared' event
socket.on('resolved_alerts_cleared', (data) => {
    console.log("WebSocket Notification:", data.message);
    showNotification(data.message, 'success');
    fetchResolvedAlerts(); // Refresh the resolved alerts list
});

// Listen for 'new_fact_submitted' event
socket.on('new_fact_submitted', (data) => {
    console.log("WebSocket Notification:", data.message);
    showNotification(data.message, 'info');
});

// Listen for 'new_fact' event
socket.on('new_fact', (data) => {
    console.log("WebSocket Notification:", data.message);
    showNotification(data.message, 'info');
    fetchFacts(); // Refresh the facts list
});

// Listen for 'resolved_alert' event
socket.on('resolved_alert', (data) => {
    console.log("WebSocket Notification:", data.message);
    showNotification(data.message, 'success');
    fetchResolvedAlerts(); // Refresh the resolved alerts list
});

// Submit a fact using fetch
async function submitFact(event) {
    event.preventDefault();
    const factInput = document.getElementById('fact-input').value;

    try {
        const response = await fetch('/api/submit_fact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fact: factInput })
        });

        if (response.ok) {
            const result = await response.json();
            showNotification(result.message, 'success');
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to submit fact.', 'error');
        }
    } catch (error) {
        console.error('Error submitting fact:', error);
        showNotification('Error submitting fact.', 'error');
    }
}

// Fetch resolved alerts using fetch
async function fetchResolvedAlerts() {
    try {
        const response = await fetch('/api/resolved_alerts');
        const resolvedAlerts = await response.json();

        const resolvedSection = document.getElementById('resolved-alerts-list');
        resolvedSection.innerHTML = resolvedAlerts.length ? '' : '<p>No resolved alerts yet.</p>';

        resolvedAlerts.forEach(alert => {
            const alertItem = document.createElement('li');
            alertItem.innerHTML = `
                <p><strong>${alert.full_text}</strong></p>
                <p><strong>Resolved Type:</strong> ${alert.match_type}</p>
            `;
            resolvedSection.appendChild(alertItem);
        });
    } catch (error) {
        console.error('Error fetching resolved alerts:', error);
        showNotification('Error fetching resolved alerts.', 'error');
    }
}

function redirectToTextFact() {
    window.location.href = "/text_fact"; // Redirect to the Check Text page
}

function redirectToSearchPage() {
    window.location.href = "/search"; // Redirect to the Search page
}

async function updateTheme(theme) {
    try {
        const response = await fetch('/update-theme', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ theme })
        });

        if (response.ok) {
            const result = await response.json();
            console.log(result.message);
            document.body.className = theme; // Apply the new theme immediately
        } else {
            const error = await response.json();
            console.error(error.error || 'Failed to update theme.');
        }
    } catch (error) {
        console.error('Error updating theme:', error);
    }
}

// Example usage: Call `updateTheme('light')` or `updateTheme('dark')` when the user selects a theme.

async function clearAllFacts() {
    try {
        const response = await fetch('/api/clear_all_facts', { method: 'DELETE' });
        if (response.ok) {
            const result = await response.json();
            showNotification(result.message, 'success');
            fetchAllFacts(); // Refresh the facts list
        } else {
            const error = await response.json();
            showNotification(error.error || "Failed to delete facts.", "error");
        }
    } catch (error) {
        console.error("Error deleting facts:", error);
        showNotification("Error deleting facts.", "error");
    }
}

async function categorizeFact(fact) {
    try {
        const response = await fetch('/api/categorize-fact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fact })
        });
        const data = await response.json();
        if (response.ok) {
            showNotification(`Fact categorized as: ${data.category}`, 'success');
        } else {
            showNotification(data.error || 'Failed to categorize fact.', 'error');
        }
    } catch (error) {
        console.error('Error categorizing fact:', error);
        showNotification('Error categorizing fact.', 'error');
    }
}

async function transcribeAudio(file) {
    const formData = new FormData();
    formData.append("audio", file);

    try {
        const response = await fetch('/api/transcribe-audio', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (response.ok) {
            showNotification('Transcription completed!', 'success');
            displayTranscription(data.transcription);
        } else {
            showNotification(data.error || 'Failed to transcribe audio.', 'error');
        }
    } catch (error) {
        console.error('Error transcribing audio:', error);
        showNotification('Error transcribing audio.', 'error');
    }
}

function toggleTranscriptionMode() {
    const toggleBtn = document.getElementById("transcription-toggle");
    toggleBtn.classList.toggle("active");
    transcriptionMode = transcriptionMode === "mic" ? "system" : "mic"; // Toggle between mic and system
    document.getElementById("transcription-mode").innerText = transcriptionMode === "mic" ? "Microphone" : "System Sound";

    fetch('/toggle-transcription', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mode: transcriptionMode }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error("Error toggling transcription mode:", data.error);
        } else {
            console.log("Transcription mode toggled to:", transcriptionMode);
        }
    })
    .catch(error => console.error("Error:", error));
}