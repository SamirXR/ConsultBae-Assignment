import os
import json
import subprocess
import re
import hashlib

def compute_file_hash(file_path):
    """Computes SHA-256 hash of file for duplicate audio submission detection."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def extract_audio_metadata(file_path):
    """
    Extracts audio metadata using ffprobe and ffmpeg CLI tools:
    - duration (seconds)
    - sample rate (kHz)
    - bitrate (kbps) & bitrate_is_derived flag
    - loudness (dB)
    - noise/quality estimate (SNR in dB)
    - quality_score (0-100)
    - file_hash (SHA-256)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    file_size_bytes = os.path.getsize(file_path)
    file_hash = compute_file_hash(file_path)

    # 1. Run ffprobe for format and stream metadata
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=sample_rate,bit_rate,channels,codec_name",
        "-show_entries", "format=duration,bit_rate,size",
        "-of", "json",
        file_path
    ]
    
    duration = 0.0
    sample_rate_khz = 0.0
    bitrate_kbps = 0.0
    bitrate_is_derived = 0
    loudness_db = -20.0
    snr_db = 25.0
    noise_quality = "Good Quality"

    try:
        res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        
        # Duration
        fmt = data.get("format", {})
        if "duration" in fmt and fmt["duration"] is not None:
            try:
                duration = round(float(fmt["duration"]), 2)
            except (ValueError, TypeError):
                duration = 0.0
        
        # Bitrate
        if "bit_rate" in fmt and fmt["bit_rate"] is not None:
            try:
                bitrate_kbps = round(float(fmt["bit_rate"]) / 1000.0, 1)
            except (ValueError, TypeError):
                bitrate_kbps = 0.0

        # Stream info (sample rate)
        streams = data.get("streams", [])
        if streams:
            st = streams[0]
            if "sample_rate" in st and st["sample_rate"] is not None:
                try:
                    sample_rate_khz = round(float(st["sample_rate"]) / 1000.0, 1)
                except (ValueError, TypeError):
                    sample_rate_khz = 0.0
            if bitrate_kbps == 0.0 and "bit_rate" in st and st["bit_rate"] is not None:
                try:
                    bitrate_kbps = round(float(st["bit_rate"]) / 1000.0, 1)
                except (ValueError, TypeError):
                    bitrate_kbps = 0.0

    except Exception as e:
        print(f"[Warning] ffprobe failed: {e}")

    # 2. Run ffmpeg volumedetect for Loudness & Duration Fallback
    vol_cmd = [
        "ffmpeg",
        "-i", file_path,
        "-af", "volumedetect",
        "-f", "null",
        "-"
    ]
    try:
        v_res = subprocess.run(vol_cmd, capture_output=True, text=True)
        output = v_res.stderr

        # Fallback Duration parsing from ffmpeg stderr time=00:00:05.42 if ffprobe returned 0
        if duration == 0.0:
            time_matches = re.findall(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", output)
            if time_matches:
                hrs, mins, secs = time_matches[-1]
                duration = round(int(hrs) * 3600 + int(mins) * 60 + float(secs), 2)

        m_mean = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", output)
        m_max = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", output)

        if m_mean:
            loudness_db = round(float(m_mean.group(1)), 1)
        
        if m_max and m_mean:
            max_v = float(m_max.group(1))
            mean_v = float(m_mean.group(1))
            # Dynamic Range / SNR proxy
            snr_db = round(max_v - mean_v + 15.0, 1)
    except Exception as e:
        print(f"[Warning] ffmpeg volumedetect failed: {e}")

    # Fallback for bitrate calculation if missing (e.g. MediaRecorder streaming webm)
    if bitrate_kbps == 0.0 and duration > 0:
        bitrate_kbps = round((file_size_bytes * 8) / (duration * 1000.0), 1)
        bitrate_is_derived = 1

    # 3. Quality Score (0-100) & Noise Classification based on SNR & Loudness
    score = 100
    if duration == 0.0:
        score -= 25
    elif duration < 3.0:
        score -= 15

    if sample_rate_khz > 0 and sample_rate_khz < 16.0:
        score -= 15
    if bitrate_kbps > 0 and bitrate_kbps < 48.0:
        score -= 15
    if loudness_db < -35.0:
        score -= 20  # Too quiet
    elif loudness_db > -3.0:
        score -= 20  # Distortion risk / Clipping

    if snr_db >= 28.0:
        noise_quality = f"Excellent (Low Noise, SNR {snr_db} dB)"
    elif snr_db >= 20.0:
        noise_quality = f"Good (Moderate Noise, SNR {snr_db} dB)"
    elif snr_db >= 12.0:
        noise_quality = f"Fair (Noticeable Background Noise, SNR {snr_db} dB)"
        score -= 15
    else:
        noise_quality = f"Poor (High Background Noise, SNR {snr_db} dB)"
        score -= 30

    quality_score = max(0, min(100, score))

    return {
        "file_hash": file_hash,
        "file_size_bytes": file_size_bytes,
        "duration_seconds": duration,
        "sample_rate_khz": sample_rate_khz,
        "bitrate_kbps": bitrate_kbps,
        "bitrate_is_derived": bitrate_is_derived,
        "loudness_db": loudness_db,
        "snr_db": snr_db,
        "noise_quality_estimate": noise_quality,
        "quality_score": quality_score
    }

