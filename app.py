import streamlit as st
import sqlite3
import os
import numpy as np
import soundfile as sf
from datetime import datetime

DB_PATH = "consultbae.db"
AUDIO_DIR = "audio_submissions"
os.makedirs(AUDIO_DIR, exist_ok=True)

# ---------- Setup: make sure the audio_submissions table exists ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audio_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            file_path TEXT,
            duration_sec REAL,
            sample_rate_khz REAL,
            bitrate_kbps REAL,
            loudness_db REAL,
            submitted_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# ---------- Extract audio properties ----------
def analyze_audio(file_path):
    data, sample_rate = sf.read(file_path)
    if data.ndim > 1:
        data = data.mean(axis=1)  # convert stereo to mono for loudness calc

    duration_sec = len(data) / sample_rate
    sample_rate_khz = sample_rate / 1000

    # bitrate estimate (uncompressed PCM): sample_rate * bits_per_sample * channels / 1000
    info = sf.info(file_path)
    bits_per_sample = 16  # most WAV recordings are 16-bit
    bitrate_kbps = (sample_rate * bits_per_sample * info.channels) / 1000

    # loudness: RMS in dBFS (rough loudness estimate)
    rms = np.sqrt(np.mean(data**2)) if len(data) > 0 else 0
    loudness_db = 20 * np.log10(rms) if rms > 0 else -100.0

    return round(duration_sec, 2), round(sample_rate_khz, 2), round(bitrate_kbps, 2), round(loudness_db, 2)

def save_submission(name, phone, uploaded_file):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in name if c.isalnum()) or "user"
    file_path = os.path.join(AUDIO_DIR, f"{safe_name}_{timestamp}.wav")

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    duration, sr_khz, bitrate, loudness = analyze_audio(file_path)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO audio_submissions (name, phone, file_path, duration_sec, sample_rate_khz, bitrate_kbps, loudness_db, submitted_at) VALUES (?,?,?,?,?,?,?,?)",
        (name, phone, file_path, duration, sr_khz, bitrate, loudness, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return duration, sr_khz, bitrate, loudness

# ---------- Streamlit UI ----------
init_db()
st.title("ConsultBae — Audio Collection App")

page = st.sidebar.radio("Go to", ["Submit Audio", "View All Submissions"])

if page == "Submit Audio":
    st.header("Submit your recording")
    name = st.text_input("Name")
    phone = st.text_input("Phone Number")

    st.write("Record audio:")
    recorded_audio = st.audio_input("Record")

    st.write("OR upload an audio file:")
    uploaded_audio = st.file_uploader("Upload", type=["wav", "mp3"])

    audio_file = recorded_audio if recorded_audio is not None else uploaded_audio

    if st.button("Submit"):
        if not name or not phone:
            st.error("Please enter both name and phone number.")
        elif audio_file is None:
            st.error("Please record or upload an audio file.")
        else:
            duration, sr_khz, bitrate, loudness = save_submission(name, phone, audio_file)
            st.success("Submitted successfully!")
            st.write(f"**Duration:** {duration} sec")
            st.write(f"**Sample Rate:** {sr_khz} kHz")
            st.write(f"**Bitrate:** {bitrate} kbps")
            st.write(f"**Loudness:** {loudness} dB")

elif page == "View All Submissions":
    st.header("All Submissions")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, phone, file_path, duration_sec, sample_rate_khz, bitrate_kbps, loudness_db, submitted_at FROM audio_submissions ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        st.info("No submissions yet.")
    for r in rows:
        name, phone, file_path, duration, sr_khz, bitrate, loudness, submitted_at = r
        st.subheader(f"{name} ({phone})")
        st.write(f"Duration: {duration}s | Sample Rate: {sr_khz}kHz | Bitrate: {bitrate}kbps | Loudness: {loudness}dB")
        if os.path.exists(file_path):
            st.audio(file_path)
        st.caption(f"Submitted: {submitted_at}")
        st.divider()
