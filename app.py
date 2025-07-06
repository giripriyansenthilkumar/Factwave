from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from pymongo import MongoClient
from pymongo.collection import Collection
from bson.objectid import ObjectId
import bcrypt
from datetime import datetime, timezone
import mongo
from sentence_transformers import SentenceTransformer, util
import re
from thefuzz import fuzz
from flask import make_response
import os
from datetime import timedelta
import pyaudio
import wave
import numpy as np
import noisereduce as nr
import speech_recognition as sr
import random
import csv
from flask_socketio import SocketIO, emit
import pytz
import json
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'd:/factwave_working_prototype/factwave/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

utc_time = datetime.utcnow().replace(tzinfo=pytz.utc)

# Convert to IST
ist_time = pytz.timezone('Asia/Kolkata')
ist = utc_time.astimezone(ist_time)  # Convert to IST


app = Flask(__name__)

model = SentenceTransformer('all-MiniLM-L6-v2')

# Secret key for session management
app = Flask(__name__)
app.secret_key = os.urandom(24) 
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)  
app.config['MONGO_URI'] = 'mongodb+srv://ml_dept_project:ml_dept_project@ml-project.gkigx.mongodb.net/'  # Updated to point to the 'factwave' database
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

client = MongoClient(app.config['MONGO_URI'])


db = client['factwave']  

# Collection names
users_collection = db['users']  # 'users' collection
transcribed_collection=db['final_transcriptions']
facts_collection = db["verified_facts"]
status_collection = db["fact_status"]
alerts_collection = db['alerts']  # Define alerts_collection

def preprocess_text(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    return text


def get_latest_transcribed_text():
    # Check latest entry in 'final_transcriptions'
    latest_final_entry = db['final_transcriptions'].find_one(sort=[("_id", -1)])
    if (latest_final_entry and "full_text" in latest_final_entry):
        return latest_final_entry["full_text"]

    # If no final transcription, check 'transcribed_text'
    latest_entry = transcribed_collection.find_one(sort=[("_id", -1)])
    print("✅ Collections in DB:", db.list_collection_names())  

    return latest_entry["text"] if latest_entry and "text" in latest_entry else None



status_collection = db["fact_status"]  # ✅ Correct MongoDB collection reference

def check_fact_in_db(transcribed_text, threshold_fuzzy=80, threshold_bert=0.85):
    """Verify the transcribed fact against verified facts using semantic similarity and fuzzy matching."""
    transcribed_text = preprocess_text(transcribed_text)
    verified_facts = [fact["headline"] for fact in facts_collection.find()]
    
    # Exact match check
    if transcribed_text in verified_facts:
        return {"status": "Verified", "match_type": "Exact", "matched_fact": transcribed_text}

    # Fuzzy matching
    for fact in verified_facts:
        if fuzz.ratio(transcribed_text, preprocess_text(fact)) >= threshold_fuzzy:
            return {"status": "Verified", "match_type": "Fuzzy", "matched_fact": fact}

    # Semantic similarity using Sentence-BERT
    fact_embeddings = model.encode(verified_facts, convert_to_tensor=True)
    transcript_embedding = model.encode(transcribed_text, convert_to_tensor=True)
    similarities = util.pytorch_cos_sim(transcript_embedding, fact_embeddings)
    
    best_match_idx = similarities.argmax().item()
    best_match_score = similarities[0][best_match_idx].item()

    if best_match_score >= threshold_bert:
        return {"status": "Verified", "match_type": "Semantic", "matched_fact": verified_facts[best_match_idx]}

    # No match found
    return {"status": "Unverified", "match_type": "None", "matched_fact": None}

# 🔹 API Endpoint: Run Fact Check & Store Status
@app.route('/fact-check', methods=['GET'])
def fact_check():
    """Run fact verification on the latest transcribed text."""
    print("🔹 Fact Check API Called!")
    latest_transcription = get_latest_transcribed_text()
    print("Latest Transcription:", latest_transcription)  # Debugging step

    if not latest_transcription:
        print("❌ No transcribed text found.")
        return jsonify({"error": "No transcribed text found."}), 404

    result = check_fact_in_db(latest_transcription)
    print("✅ Fact Check Result:", result)  # Debugging step

    try:
        # Store result in 'fact_status' collection
        insert_result = status_collection.insert_one({
            "text": latest_transcription,
            "status": result["status"],
            "match_type": result["match_type"],
            "matched_fact": result["matched_fact"],
            "resolve": False,
            "timestamp": ist
        })
        print("✅ Status Inserted with ID:", insert_result.inserted_id)  # Debugging step

    except Exception as e:
        print("❌ Error inserting into MongoDB:", str(e))

    return jsonify(result)

# 🔹 API Endpoint: Get Latest Status for UI
@app.route('/fact-status', methods=['GET'])
def get_fact_status():
    latest_status = status_collection.find_one(sort=[("_id", -1)])  # ✅ Fetch latest status
    if not latest_status:
        return jsonify({"error": "No status available."}), 404

    return jsonify({
        "status": latest_status["status"],
        "match_type": latest_status["match_type"],
        "matched_fact": latest_status["matched_fact"]
    })

@app.route('/')
def home():
    return redirect(url_for('login'))  # If not logged in, redirect to the login page

# Route for Admin Dashboard
@app.route('/admin-dashboard')
def admin_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    return render_template('admin_dashboard.html')

@app.route('/user-dashboard')
def user_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    username = session['username']
    user = users_collection.find_one({'username': username})

    if user:
        user_id = user['user_id']  # Get the logged-in user's user_id

        # Fetch unverified alerts for the logged-in user
        alerts = list(transcribed_collection.find({
            "user_id": user_id,
            "fact_status": "Unverified",
            "resolve": False
        }))
        for alert in alerts:
            alert['_id'] = str(alert['_id'])  # Convert ObjectId to string

        # Fetch resolved alerts for the logged-in user
        resolved_alerts = list(transcribed_collection.find({
            "user_id": user_id,
            "resolve": True
        }))
        for resolved_alert in resolved_alerts:
            resolved_alert['_id'] = str(resolved_alert['_id'])  # Convert ObjectId to string

        # Fetch all facts for the logged-in user
        all_facts = list(transcribed_collection.find({"user_id": user_id}))

        return render_template('user_dashboard.html',
                               username=username,
                               alerts=alerts,
                               resolved_alerts=resolved_alerts,
                               all_facts=all_facts)
    else:
        return redirect(url_for('login'))  # If user is not found, redirect to login


# Route for Manage Users Page
@app.route('/manage-users')
def manage_users():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    
    users = users_collection.find()
    return render_template('manage-users.html', users=users)


@app.route('/add-user', methods=['GET', 'POST'])
def add_user():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']

        # Generate a unique six-digit user ID
        while True:
            user_id = random.randint(100000, 999999)
            if not users_collection.find_one({'user_id': user_id}):
                break

        # Add user to MongoDB
        users_collection.insert_one({
            'user_id': user_id,
            'username': username,
            'password': password,
            'role': role,
            'email': email
        })

        flash("User added successfully!", "success")
        return render_template('add_user.html')

    return render_template('add_user.html')


@app.route('/delete-user/<user_id>', methods=['GET'])
def delete_user(user_id):
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    users_collection.delete_one({'_id': ObjectId(user_id)})
    return redirect(url_for('manage_users'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if user exists in the database
        user = users_collection.find_one({'username': username})
        
        if user and user['password'] == password:
            session.clear()  # Clear any old session data
            session['username'] = username  # Store username in session
            session['role'] = user.get('role', 'user')  # Store user role
            session.permanent = True  # Enables session expiration
            
            # Redirect based on user role
            return redirect(url_for('admin_dashboard') if user['role'] == 'admin' else url_for('user_dashboard'))
        
        error_message = "Invalid username or password. Please try again."
        return render_template('login.html', error_message=error_message)

    # Prevent browser from caching login page
    response = make_response(render_template('login.html'))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' not in session:
        return redirect(url_for('login'))  

    user = db.users.find_one({"username": session['username']})  # Fetch user from DB

    if request.method == 'POST':
        update_data = {}
        
        if 'theme' in request.form:
            update_data['theme'] = request.form['theme']
            flash("Theme updated successfully", "success")
        
        if 'language' in request.form:
            update_data['language'] = request.form['language']
            flash("Language updated successfully", "success")
        
        if update_data:
            db.users.update_one({"username": session['username']}, {"$set": update_data})

    return render_template('settings.html', user=user)

@app.route('/profile')
def view_profile():
    if 'username' not in session:
        return redirect(url_for('login'))  

    username = session['username']
    user = users_collection.find_one({'username': username})
    return render_template('profile.html', user=user)

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))  

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        username = session['username']
        user = users_collection.find_one({'username': username})

        if not (current_password, user['password']):
            return render_template('change_password.html', error="Incorrect current password")

        if new_password != confirm_password:
            return render_template('change_password.html', error="New passwords do not match")

        users_collection.update_one({'username': username}, {'$set': {'password': new_password}})

        return redirect(url_for('view_profile'))

    return render_template('change_password.html')

@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('login'))  

    username = session['username']
    user = users_collection.find_one({'username': username})

    if request.method == 'POST':
        updated_email = request.form['email']
        users_collection.update_one(
            {'username': username},
            {'$set': {'email': updated_email}}
        )
        flash("Profile updated successfully!", "success")
        return render_template('edit_profile.html', user=user)

    return render_template('edit_profile.html', user=user)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/upload-profile-picture', methods=['POST'])
def upload_profile_picture():
    """Handle profile picture upload."""
    if 'profile_picture' not in request.files:
        return "No file part", 400
    file = request.files['profile_picture']
    if file.filename == '':
        return "No selected file", 400
    if file and allowed_file(file.filename):  # Ensure allowed_file is defined
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        users_collection.update_one(
            {'username': session['username']},
            {'$set': {'profile_picture': f'/static/uploads/{filename}'}}
        )
        return redirect('/profile')
    return "Invalid file type", 400

@app.route('/update-profile', methods=['POST'])
def update_profile():
    phone = request.form.get('phone')
    address = request.form.get('address')
    users_collection.update_one(
        {'username': session['username']},
        {'$set': {'phone': phone, 'address': address}}
    )
    return redirect('/profile')

@app.route('/logout')
def logout():
    session.pop('username', None)  
    return redirect(url_for('login'))


@app.route('/manage-facts', methods=['GET'])
def manage_facts():
    facts = list(facts_collection.find())
    return render_template('manage_facts.html', facts=facts)

@app.route('/add-fact', methods=['POST'])
def add_fact():
    category = request.form.get('category')
    headline = request.form.get('headline')
    if category and headline:
        facts_collection.insert_one({'category': category, 'headline': headline})
        #flash('Fact added successfully!', 'success')
    else:
        flash('Category and News are required.', 'error')
    return redirect(url_for('manage_facts'))

@app.route('/edit-fact', methods=['POST'])
def edit_fact():
    fact_id = request.form.get('fact_id')
    category = request.form.get('category')
    headline = request.form.get('headline')
    if fact_id and category and headline:
        facts_collection.update_one(
            {'_id': ObjectId(fact_id)},
            {'$set': {'category': category, 'headline': headline}}
        )
        #flash('Fact updated successfully!', 'success')
    else:
        flash('All fields are required.', 'error')
    return redirect(url_for('manage_facts'))

@app.route('/delete-fact/<fact_id>', methods=['POST'])
def delete_fact(fact_id):
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    if fact_id:
        facts_collection.delete_one({'_id': ObjectId(fact_id)})
        # flash('Fact deleted successfully!', 'success')
    return redirect(url_for('manage_facts'))

@app.route('/save_transcription', methods=['POST'])
def save_transcription():
    """Save the combined transcription."""
    data = request.json
    transcription_text = data.get("transcription")

    if transcription_text:
        transcription_entry = {
            "text": transcription_text,
            "timestamp": ist
        }
        transcribed_collection.insert_one(transcription_entry)
        return jsonify({"message": "Transcription saved successfully!"}), 201
    else:
        return jsonify({"error": "No transcription text provided"}), 400

@app.route('/store-final-transcription', methods=['POST'])
def store_final_transcription():
    """Save the final transcription and run fact check."""
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    transcription_text = data.get("transcription")

    if transcription_text:
        # Get the logged-in user's user_id
        username = session['username']
        user = users_collection.find_one({'username': username})
        user_id = user['user_id']

        print("🔹 Received Final Transcription:", transcription_text)  # Debugging

        # ✅ Run fact check
        fact_status = check_fact_in_db(transcription_text)
        print("✅ Fact Check Result:", fact_status)  # Debugging

        # Save the transcription with user_id and fact status
        transcription_entry = {
            "user_id": user_id,
            "full_text": transcription_text,
            "fact_status": fact_status["status"],
            "match_type": fact_status["match_type"],
            "matched_fact": fact_status["matched_fact"],
            "resolve": False,
            "deleted": False,  # Ensure the fact is not marked as deleted
            "timestamp": ist
        }
        db['final_transcriptions'].insert_one(transcription_entry)

        print("✅ Final Transcription Stored Successfully!")  # Debugging

        return jsonify({
            "message": "Final transcription saved!",
            "fact_status": fact_status
        }), 201
    else:
        print("❌ No transcription text provided!")  # Debugging
        return jsonify({"error": "No transcription text provided"}), 400

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # Get the logged-in user's user_id
    username = session['username']
    user = users_collection.find_one({'username': username})
    user_id = user['user_id']

    # Fetch only unverified facts for the logged-in user
    alerts = list(db.final_transcriptions.find({
        "user_id": user_id,
        "fact_status": "Unverified",
        "resolve": False
    }))
    for alert in alerts:
        alert['_id'] = str(alert['_id'])  # Convert ObjectId to string
    return jsonify(alerts)

@app.route('/api/resolve_alert/<alert_id>', methods=['PUT'])
def resolve_alert(alert_id):
    # Find the alert
    alert = db.final_transcriptions.find_one({"_id": ObjectId(alert_id)})
    
    if alert and alert["fact_status"] == "Unverified":  # Ensure only unverified facts are resolved
        # Update the resolve status
        db.final_transcriptions.update_one({"_id": ObjectId(alert_id)}, {"$set": {"resolve": True}})
        
        # Move to resolved collection
        db.resolved_alerts.insert_one(alert)
        
        # Delete from final_transcriptions
        db.final_transcriptions.delete_one({"_id": ObjectId(alert_id)})

        return jsonify({"message": "Alert resolved"})
    else:
        return jsonify({"error": "Alert not found or not unverified"}), 404

@app.route('/api/resolved_alerts', methods=['GET'])
def get_resolved_alerts():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # Get the logged-in user's user_id
    username = session['username']
    user = users_collection.find_one({'username': username})
    user_id = user['user_id']

    # Fetch only resolved alerts for the logged-in user
    resolved_alerts = list(db.resolved_alerts.find({"user_id": user_id}))
    for alert in resolved_alerts:
        alert['_id'] = str(alert['_id'])  # Convert ObjectId to string
    return jsonify(resolved_alerts)

@app.route('/process-audio', methods=['POST'])
def process_audio():
    """Capture audio, reduce noise, and convert speech to text."""
    CHUNK = 1024  # Buffer size
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = 5
    WAVE_OUTPUT_FILENAME = "output.wav"

    # Initialize PyAudio
    audio = pyaudio.PyAudio()

    # Start recording
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    print("Recording...")
    frames = []

    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("Recording finished.")

    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save the recorded audio to a file
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    # Load the audio file and reduce noise
    print("Reducing noise...")
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'rb')
    signal = np.frombuffer(wf.readframes(-1), dtype=np.int16)
    reduced_noise = nr.reduce_noise(y=signal, sr=RATE)
    wf.close()

    # Save the noise-reduced audio
    reduced_filename = "reduced_" + WAVE_OUTPUT_FILENAME
    wf = wave.open(reduced_filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(reduced_noise.tobytes())
    wf.close()

    # Convert speech to text
    recognizer = sr.Recognizer()
    with sr.AudioFile(reduced_filename) as source:
        print("Converting speech to text...")
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            print("Recognized Text:", text)
            return jsonify({"transcription": text}), 200
        except sr.UnknownValueError:
            return jsonify({"error": "Speech not recognized"}), 400
        except sr.RequestError as e:
            return jsonify({"error": f"Speech recognition error: {e}"}), 500

@app.route('/toggle-transcription', methods=['POST'])
def toggle_transcription():
    """Toggle between microphone and system sound for transcription."""
    data = request.json
    mode = data.get("mode")  # "mic" or "system"

    if mode not in ["mic", "system"]:
        return jsonify({"error": "Invalid mode. Use 'mic' or 'system'."}), 400

    def process_audio_stream():
        """Process audio chunks based on the selected mode."""
        recognizer = sr.Recognizer()
        audio = pyaudio.PyAudio()

        # Stop any previously active streams
        if hasattr(process_audio_stream, "stream") and process_audio_stream.stream.is_active():
            process_audio_stream.stream.stop_stream()
            process_audio_stream.stream.close()

        # Open the appropriate audio stream based on the mode
        if mode == "mic":
            process_audio_stream.stream = audio.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
        elif mode == "system":
            process_audio_stream.stream = audio.open(format=pyaudio.paInt16, channels=2, rate=44100, input=True, input_device_index=1, frames_per_buffer=1024)

        try:
            while True:
                data = process_audio_stream.stream.read(1024, exception_on_overflow=False)
                audio_data = sr.AudioData(data, 44100, 2 if mode == "system" else 1)
                try:
                    transcription = recognizer.recognize_google(audio_data)
                    fact_status = check_fact_in_db(transcription)
                    yield f"data: {json.dumps({'transcription': transcription, 'fact_status': fact_status})}\n\n"
                except sr.UnknownValueError:
                    yield f"data: {json.dumps({'error': 'Speech not recognized'})}\n\n"
                except sr.RequestError as e:
                    yield f"data: {json.dumps({'error': f'Speech recognition error: {e}'})}\n\n"
        finally:
            process_audio_stream.stream.stop_stream()
            process_audio_stream.stream.close()
            audio.terminate()

    return Response(process_audio_stream(), content_type='text/event-stream')

@app.route('/check-fact', methods=['POST'])
def check_fact():
    """Verify a manually entered fact and store it in the text_status collection."""
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    fact_text = data.get("fact")

    if not fact_text:
        return jsonify({"error": "No fact provided"}), 400

    # Get the logged-in user's user_id
    username = session['username']
    user = users_collection.find_one({'username': username})
    user_id = user['user_id']

    # Verify the fact
    fact_status = check_fact_in_db(fact_text)

    # Store the fact in the text_status collection
    fact_entry = {
        "user_id": user_id,
        "text": fact_text,
        "fact_status": fact_status["status"],
        "match_type": fact_status["match_type"],
        "matched_fact": fact_status["matched_fact"],
        "resolve": fact_status["status"] != "Unverified",  # Mark as resolved if verified
        "timestamp": ist
    }
    db['text_status'].insert_one(fact_entry)

    return jsonify({
        "message": "Fact checked and stored successfully!",
        "fact_status": fact_status
    }), 201

@app.route('/text_fact')
def text_fact():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    return render_template('text_fact.html')

@app.route('/api/text_status', methods=['GET'])
def get_text_status():
    """Fetch all facts from the text_status collection."""
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    username = session['username']
    user = users_collection.find_one({'username': username})
    user_id = user['user_id']

    facts = list(db['text_status'].find({"user_id": user_id}))
    for fact in facts:
        fact['_id'] = str(fact['_id'])  # Convert ObjectId to string
    return jsonify(facts)

@app.route('/upload-csv', methods=['POST'])
def upload_csv():
    if 'csv_file' not in request.files:
        flash("No file part in the request", "error")
        return redirect(url_for('manage_facts'))

    file = request.files['csv_file']
    if file.filename == '':
        flash("No file selected", "error")
        return redirect(url_for('manage_facts'))

    if not file.filename.endswith('.csv'):
        flash("Invalid file type. Please upload a CSV file.", "error")
        return redirect(url_for('manage_facts'))

    try:
        csv_data = csv.reader(file.stream.read().decode('utf-8').splitlines())
        for row in csv_data:
            if len(row) < 2:
                continue  # Skip rows with insufficient data
            category, headline = row[0].strip(), row[1].strip()
            if category and headline:
                facts_collection.insert_one({'category': category, 'headline': headline})
        flash("CSV uploaded and data stored successfully!", "success")
    except Exception as e:
        flash(f"Error processing CSV: {str(e)}", "error")
    return redirect(url_for('manage_facts'))

@app.route('/update-theme', methods=['POST'])
def update_theme():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    theme = data.get('theme')

    if theme not in ['light', 'dark']:
        return jsonify({"error": "Invalid theme"}), 400

    username = session['username']
    users_collection.update_one({'username': username}, {'$set': {'theme': theme}})
    session['theme'] = theme  # Update session to reflect the new theme
    return jsonify({"message": "Theme updated successfully!"}), 200

@app.route('/search', methods=['GET', 'POST'])
def search_facts():
    if request.method == 'GET':
        # Render the search page for GET requests
        return render_template('search.html')

    # Handle POST requests for searching facts
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    category = data.get('category', '').strip().lower()
    keywords = data.get('keywords', [])

    query = {}
    if (category):
        query["category"] = {"$regex": f"^{category}$", "$options": "i"}  # Case-insensitive exact match
    if keywords:
        query["headline"] = {"$regex": "|".join([re.escape(kw) for kw in keywords]), "$options": "i"}  # Case-insensitive keyword match

    print("🔹 Search Query:", query)  # Debugging: Log the query
    facts = list(facts_collection.find(query))
    print("🔹 Facts Found:", facts)  # Debugging: Log the results
    for fact in facts:
        fact['_id'] = str(fact['_id'])  # Convert ObjectId to string
    return jsonify(facts)

@app.route('/api/verified_facts', methods=['GET'])
def get_verified_facts():
    """Fetch all verified facts from the final_transcriptions collection."""
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        verified_facts = list(db['final_transcriptions'].find({"fact_status": "Verified"}))
        print(f"🔹 Number of Verified Facts Found: {len(verified_facts)}")  # Debugging: Log the count
        for fact in verified_facts:
            fact['_id'] = str(fact['_id'])  # Convert ObjectId to string
            fact['timestamp'] = fact['timestamp'].isoformat() if 'timestamp' in fact else None  # Convert timestamp to ISO format
        print("🔹 Verified Facts Sent:", verified_facts)  # Debugging: Log the data being sent
        return jsonify(verified_facts)
    except Exception as e:
        print(f"❌ Error fetching verified facts: {str(e)}")  # Debugging: Log any errors
        return jsonify({"error": "An error occurred while fetching verified facts."}), 500

@app.route('/api/all_facts', methods=['GET'])
def get_all_facts():
    """Fetch all facts excluding those marked as deleted."""
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        all_facts = list(db['final_transcriptions'].find({"deleted": {"$ne": True}}))
        for fact in all_facts:
            fact['_id'] = str(fact['_id'] ) # Convert ObjectId to string
            fact['timestamp'] = fact['timestamp'].isoformat() if 'timestamp' in fact else None  # Convert timestamp to ISO format
        return jsonify(all_facts)
    except Exception as e:
        print(f"Error fetching all facts: {str(e)}")
        return jsonify({"error": "An error occurred while fetching all facts."}), 500

@app.route('/api/user_facts', methods=['GET'])
def get_user_facts():
    """Fetch all facts for the user whose user_id matches the session's user_id."""
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        username = session['username']
        user = users_collection.find_one({'username': username})
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_id = user['user_id']
        user_facts = list(db['final_transcriptions'].find({"user_id": user_id}))
        for fact in user_facts:
            fact['_id'] = str(fact['_id'])  # Convert ObjectId to string
            fact['timestamp'] = fact['timestamp'].isoformat() if 'timestamp' in fact else None  # Convert timestamp to ISO format
        return jsonify(user_facts)
    except Exception as e:
        print(f"Error fetching user facts: {str(e)}")
        return jsonify({"error": "An error occurred while fetching user facts."}), 500

@app.route('/api/clear_user_facts', methods=['DELETE'])
def clear_user_facts():
    """Mark all facts for the user as deleted instead of removing them."""
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        username = session['username']
        user = users_collection.find_one({'username': username})
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_id = user['user_id']
        result = db['final_transcriptions'].update_many(
            {"user_id": user_id},
            {"$set": {"deleted": True}}
        )
        return jsonify({"message": f"Marked {result.modified_count} facts as deleted."}), 200
    except Exception as e:
        print(f"Error clearing user facts: {str(e)}")
        return jsonify({"error": "An error occurred while clearing user facts."}), 500

@app.route('/api/clear_resolved_alerts', methods=['DELETE'])
def clear_resolved_alerts():
    """Delete all resolved alerts for the user whose user_id matches the session's user_id."""
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        username = session['username']
        user = users_collection.find_one({'username': username})
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_id = user['user_id']
        result = db['resolved_alerts'].delete_many({"user_id": user_id})

        # Notify the client via WebSocket
        socketio.emit('resolved_alerts_cleared', {'message': f"Deleted {result.deleted_count} resolved alerts."}, room=user_id)
        return jsonify({"message": f"Deleted {result.deleted_count} resolved alerts."}), 200
    except Exception as e:
        print(f"Error clearing resolved alerts: {str(e)}")
        return jsonify({"error": "An error occurred while clearing resolved alerts."}), 500

@app.route('/api/clear_all_facts', methods=['DELETE'])
def clear_all_facts():
    """Delete all facts in the final_transcriptions collection for the logged-in user."""
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401


    try:
        username = session['username']
        user = users_collection.find_one({'username': username})
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_id = user['user_id']
        result = db['final_transcriptions'].delete_many({"user_id": user_id})
        return jsonify({"message": f"Deleted {result.deleted_count} facts."}), 200
    except Exception as e:
        print(f"Error deleting facts: {str(e)}")
        return jsonify({"error": "An error occurred while deleting facts."}), 500

@app.route('/api/submit_fact', methods=['POST'])
def submit_fact():
    """Submit a fact for verification."""
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    fact_text = data.get("fact")

    if not fact_text:
        return jsonify({"error": "No fact provided"}), 400

    username = session['username']
    user = users_collection.find_one({'username': username})
    user_id = user['user_id']

    # Save the fact in the database
    fact_entry = {
        "user_id": user_id,
        "text": fact_text,
        "fact_status": "Pending",
        "timestamp": datetime.now(ist)
    }
    db['final_transcriptions'].insert_one(fact_entry)

    return jsonify({"message": "Fact submitted successfully!"}), 201

@app.route('/live-transcription-page')
def live_transcription_page():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('live_transcription.html')

@app.route('/live-transcription', methods=['POST'])
def live_transcription():
    """Handle live transcription and dynamic fact-checking."""
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    def process_audio_stream():
        """Process audio chunks and yield transcription and fact-check results."""
        recognizer = sr.Recognizer()
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

        try:
            while True:
                data = stream.read(1024, exception_on_overflow=False)
                audio_data = sr.AudioData(data, 44100, 2)
                try:
                    transcription = recognizer.recognize_google(audio_data)
                    fact_status = check_fact_in_db(transcription)
                    yield f"data: {json.dumps({'transcription': transcription, 'fact_status': fact_status})}\n\n"
                except sr.UnknownValueError:
                    yield f"data: {json.dumps({'error': 'Speech not recognized'})}\n\n"
                except sr.RequestError as e:
                    yield f"data: {json.dumps({'error': f'Speech recognition error: {e}'})}\n\n"
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

    return Response(process_audio_stream(), content_type='text/event-stream')

@app.route('/api/analytics', methods=['GET'])
def get_analytics_data():
    """Provide analytics data for the dashboard."""
    verified_facts = facts_collection.count_documents({'fact_status': 'Verified'})
    unverified_facts = facts_collection.count_documents({'fact_status': 'Unverified'})
    resolved_alerts = alerts_collection.count_documents({'resolved': True})
    unresolved_alerts = alerts_collection.count_documents({'resolved': False})

    return jsonify({
        'facts': {
            'verified': verified_facts,
            'unverified': unverified_facts
        },
        'alerts': {
            'resolved': resolved_alerts,
            'unresolved': unresolved_alerts
        }
    })

@app.route('/example', methods=['GET'])
def example_route():
    value = 42
    return f"The value is {repr(value)}"  # Use repr() instead of backticks

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    if 'username' in session:
        user_id = users_collection.find_one({'username': session['username']})['user_id']
        socketio.join_room(user_id)
        print(f"User {session['username']} connected to WebSocket.")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    if 'username' in session:
        user_id = users_collection.find_one({'username': session['username']})['user_id']
        socketio.leave_room(user_id)
        print(f"User {session['username']} disconnected from WebSocket.")

def broadcast_new_fact(fact):
    """Broadcast a new fact to all connected clients."""
    socketio.emit('new_fact', {'message': f"New fact added: {fact}"}, broadcast=True)

def broadcast_resolved_alert(alert):
    """Broadcast a resolved alert to all connected clients."""
    socketio.emit('resolved_alert', {'message': f"Alert resolved: {alert}"}, broadcast=True)

if __name__ == '__main__':
    try:
        socketio.run(app, debug=True)
    except KeyboardInterrupt:
        print("Server stopped gracefully.")