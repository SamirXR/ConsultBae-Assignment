// ConsultBae Audio App Frontend Engine

let currentSourceMode = 'record'; // 'record' or 'upload'
let mediaRecorder = null;
let audioChunks = [];
let recordedBlob = null;
let recordingInterval = null;
let recordSeconds = 0;
let audioContext = null;
let analyser = null;
let canvasAnimId = null;
let cachedSubmissions = [];

// Tab Switching
function switchTab(viewId) {
    document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

    document.getElementById(viewId).classList.add('active');
    
    if (viewId === 'submitView') {
        document.getElementById('tabSubmitBtn').classList.add('active');
    } else if (viewId === 'dashboardView') {
        document.getElementById('tabDashboardBtn').classList.add('active');
        loadSubmissions();
    }
}

// Input Source Mode Switching (Live Recording vs Upload File)
function selectSourceMode(mode) {
    currentSourceMode = mode;
    document.getElementById('optRecord').classList.toggle('active', mode === 'record');
    document.getElementById('optUpload').classList.toggle('active', mode === 'upload');

    document.getElementById('recorderPanel').style.display = mode === 'record' ? 'block' : 'none';
    document.getElementById('uploadPanel').style.display = mode === 'upload' ? 'block' : 'none';
}

// MediaRecorder Audio Capture
async function toggleRecording() {
    const recBtn = document.getElementById('recordBtn');
    const recIcon = document.getElementById('recIcon');
    const recText = document.getElementById('recText');

    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        // Start Recording
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];
            
            // Choose optimal mimeType supported by browser
            const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 
                             MediaRecorder.isTypeSupported('audio/ogg') ? 'audio/ogg' : 'audio/wav';

            mediaRecorder = new MediaRecorder(stream, { mimeType });

            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) audioChunks.push(event.data);
            };

            mediaRecorder.onstop = () => {
                recordedBlob = new Blob(audioChunks, { type: mimeType });
                const audioUrl = URL.createObjectURL(recordedBlob);
                const audioPreview = document.getElementById('recordedAudioPreview');
                audioPreview.src = audioUrl;
                audioPreview.style.display = 'block';
                document.getElementById('resetRecBtn').style.display = 'inline-flex';
                stopWaveform();
            };

            mediaRecorder.start();
            recordStartTime = Date.now();
            pausedTimeTotal = 0;
            pauseStartTime = 0;
            finalRecordedMs = null;
            
            clearInterval(recordingInterval);
            recordingInterval = setInterval(updateTimer, 100);

            recBtn.classList.add('recording');
            recIcon.className = 'fa-solid fa-square';
            recText.innerText = 'Stop Recording';

            document.getElementById('pauseBtn').style.display = 'inline-flex';
            document.getElementById('pauseIcon').className = 'fa-solid fa-pause';
            document.getElementById('pauseText').innerText = 'Pause';

            document.getElementById('studioDot').classList.add('live');
            document.getElementById('studioStatus').innerText = 'REC · FREQUENCY PROBE LIVE';
            document.getElementById('studioStatus').style.color = '#34d399';

            startWaveform(stream);
            showToast('Studio microphone input recording live...', 'info');

        } catch (err) {
            console.error('Microphone access error:', err);
            showToast('Microphone access error: ' + err.message, 'error');
        }
    } else if (mediaRecorder.state === 'recording' || mediaRecorder.state === 'paused') {
        // Calculate exact frozen recorded duration at this instant
        const now = pauseStartTime ? pauseStartTime : Date.now();
        finalRecordedMs = Math.max(0, now - recordStartTime - pausedTimeTotal);

        if (mediaRecorder.state === 'paused') {
            mediaRecorder.resume();
        }
        mediaRecorder.stop();
        if (mediaRecorder.stream) {
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
        clearInterval(recordingInterval);
        recordingInterval = null;
        recordStartTime = 0;
        pauseStartTime = 0;

        stopWaveform();
        updateTimer(); // Renders the exact frozen finalRecordedMs!

        recBtn.classList.remove('recording');
        recIcon.className = 'fa-solid fa-microphone';
        recText.innerText = 'Record Live Audio';

        document.getElementById('pauseBtn').style.display = 'none';
        document.getElementById('studioDot').classList.remove('live');
        document.getElementById('studioStatus').innerText = 'STUDIO INPUT · RECORDED';
        document.getElementById('studioStatus').style.color = 'var(--text-main)';

        showToast('Audio recording completed!', 'success');
    }
}

let recordStartTime = 0;
let pauseStartTime = 0;
let pausedTimeTotal = 0;
let finalRecordedMs = null;

function togglePauseRecording() {
    if (!mediaRecorder) return;

    const pauseBtn = document.getElementById('pauseBtn');
    const pauseIcon = document.getElementById('pauseIcon');
    const pauseText = document.getElementById('pauseText');
    const studioStatus = document.getElementById('studioStatus');

    if (mediaRecorder.state === 'recording') {
        mediaRecorder.pause();
        pauseStartTime = Date.now();

        pauseIcon.className = 'fa-solid fa-play';
        pauseText.innerText = 'Resume';

        document.getElementById('studioDot').classList.remove('live');
        studioStatus.innerText = 'PAUSED · STUDIO STANDBY';
        studioStatus.style.color = 'var(--accent-amber)';

        showToast('Recording paused', 'info');
    } else if (mediaRecorder.state === 'paused') {
        mediaRecorder.resume();
        if (pauseStartTime) {
            pausedTimeTotal += (Date.now() - pauseStartTime);
            pauseStartTime = 0;
        }

        pauseIcon.className = 'fa-solid fa-pause';
        pauseText.innerText = 'Pause';

        document.getElementById('studioDot').classList.add('live');
        studioStatus.innerText = 'REC · FREQUENCY PROBE LIVE';
        studioStatus.style.color = '#34d399';

        showToast('Recording resumed', 'info');
    }
}

function updateTimer() {
    let elapsedMs = 0;
    if (finalRecordedMs !== null) {
        elapsedMs = finalRecordedMs;
    } else if (recordStartTime) {
        let currentPaused = pausedTimeTotal;
        if (pauseStartTime) {
            currentPaused += (Date.now() - pauseStartTime);
        }
        elapsedMs = Math.max(0, Date.now() - recordStartTime - currentPaused);
    } else {
        document.getElementById('recordTimer').innerText = '00:00.0';
        return;
    }

    const totalSecs = elapsedMs / 1000;
    const mins = String(Math.floor(totalSecs / 60)).padStart(2, '0');
    const secs = String(Math.floor(totalSecs % 60)).padStart(2, '0');
    const tenths = String(Math.floor((elapsedMs % 1000) / 100));
    document.getElementById('recordTimer').innerText = `${mins}:${secs}.${tenths}`;
}

function resetRecording() {
    if (mediaRecorder && (mediaRecorder.state === 'recording' || mediaRecorder.state === 'paused')) {
        mediaRecorder.stop();
        if (mediaRecorder.stream) {
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
    }
    recordedBlob = null;
    audioChunks = [];
    recordStartTime = 0;
    pauseStartTime = 0;
    pausedTimeTotal = 0;
    finalRecordedMs = null;
    clearInterval(recordingInterval);
    recordingInterval = null;
    stopWaveform();

    updateTimer();
    document.getElementById('recordedAudioPreview').style.display = 'none';
    document.getElementById('pauseBtn').style.display = 'none';
    document.getElementById('resetRecBtn').style.display = 'none';
    document.getElementById('studioDot').classList.remove('live');
    document.getElementById('studioStatus').innerText = 'STUDIO INPUT · IDLE';
    document.getElementById('studioStatus').style.color = 'var(--text-dim)';

    const recBtn = document.getElementById('recordBtn');
    recBtn.classList.remove('recording');
    document.getElementById('recIcon').className = 'fa-solid fa-microphone';
    document.getElementById('recText').innerText = 'Record Live Audio';

    showToast('Recording reset', 'info');
}

// Waveform Audio Visualizer Canvas
function startWaveform(stream) {
    const canvas = document.getElementById('waveformCanvas');
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);
    analyser.fftSize = 128;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    recordStartTime = Date.now();
    recordingInterval = setInterval(updateTimer, 100);

    function draw() {
        canvasAnimId = requestAnimationFrame(draw);
        analyser.getByteFrequencyData(dataArray);

        ctx.fillStyle = 'rgba(10, 10, 10, 0.45)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw subtle grid line
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, canvas.height / 2);
        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();

        const numBars = 42;
        const barWidth = 5;
        const gap = (canvas.width - (numBars * barWidth)) / (numBars + 1);

        for (let i = 0; i < numBars; i++) {
            const dataIndex = Math.floor((i / numBars) * bufferLength);
            const val = dataArray[dataIndex] || 0;
            const barHeight = Math.max(6, (val / 255) * (canvas.height - 16));

            const x = gap + i * (barWidth + gap);
            const y = (canvas.height - barHeight) / 2;

            const gradient = ctx.createLinearGradient(0, y + barHeight, 0, y);
            gradient.addColorStop(0, '#064e3b');
            gradient.addColorStop(0.6, '#059669');
            gradient.addColorStop(1, '#34d399');

            ctx.fillStyle = gradient;
            ctx.beginPath();
            if (ctx.roundRect) {
                ctx.roundRect(x, y, barWidth, barHeight, 3);
            } else {
                ctx.rect(x, y, barWidth, barHeight);
            }
            ctx.fill();
        }
    }
    draw();
}

function stopWaveform() {
    if (canvasAnimId) cancelAnimationFrame(canvasAnimId);
    if (audioContext) audioContext.close();
    
    // Draw clean idle flat line canvas
    const canvas = document.getElementById('waveformCanvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#0d0d0d';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, canvas.height / 2);
        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();
    }
}

// File Upload Input Handler
function handleFileSelected(event) {
    const file = event.target.files[0];
    if (file) {
        document.getElementById('uploadStatusText').innerText = `Selected File: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
        showToast(`File selected: ${file.name}`, 'info');
    }
}

// Form Submission & API Processing
async function handleFormSubmit(event) {
    event.preventDefault();
    const name = document.getElementById('submitterName').value.trim();
    const phone = document.getElementById('phoneNumber').value.trim();

    if (!name || !phone) {
        showToast('Please enter both Name and Phone Number', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('submitter_name', name);
    formData.append('phone_number', phone);

    if (currentSourceMode === 'record') {
        if (!recordedBlob) {
            showToast('Please record audio before submitting!', 'error');
            return;
        }
        formData.append('audio_file', recordedBlob, `recording_${Date.now()}.webm`);
    } else {
        const fileInput = document.getElementById('audioFileInput');
        if (!fileInput.files || fileInput.files.length === 0) {
            showToast('Please select an audio file to upload!', 'error');
            return;
        }
        formData.append('audio_file', fileInput.files[0]);
    }

    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing Audio & Extracting Properties...';

    try {
        const response = await fetch('/api/submissions', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (response.ok && data.status === 'success') {
            showToast('✅ Audio saved & properties extracted!', 'success');
            // Reset form
            document.getElementById('audioForm').reset();
            resetRecording();
            document.getElementById('uploadStatusText').innerText = 'Click to select audio file (WAV, MP3, M4A, OGG)';
            
            // Switch to dashboard view to show result
            setTimeout(() => {
                switchTab('dashboardView');
            }, 800);
        } else {
            showToast(`Submission failed: ${data.message || 'Server error'}`, 'error');
        }
    } catch (err) {
        console.error('Submission error:', err);
        showToast('Network or server error during submission', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Extract Properties & Save to Database';
    }
}

// Load Submissions Dashboard
async function loadSubmissions() {
    const grid = document.getElementById('submissionsGrid');
    grid.innerHTML = '<div style="color: var(--text-muted); grid-column: 1/-1; text-align: center; padding: 2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Loading audio library...</div>';

    try {
        const response = await fetch('/api/submissions');
        cachedSubmissions = await response.json();
        document.getElementById('submissionCount').innerText = cachedSubmissions.length;
        renderSubmissions(cachedSubmissions);
    } catch (err) {
        console.error('Failed to load submissions:', err);
        grid.innerHTML = '<div style="color: var(--accent-rose); grid-column: 1/-1; text-align: center;">Error loading audio submissions.</div>';
    }
}

function filterSubmissions() {
    const search = document.getElementById('searchInput').value.toLowerCase().trim();
    const quality = document.getElementById('qualityFilter').value;

    const filtered = cachedSubmissions.filter(sub => {
        const nameMatch = (sub.submitter_name || '').toLowerCase().includes(search);
        const phoneMatch = (sub.phone_number || '').includes(search);
        const cityMatch = (sub.candidate_city || '').toLowerCase().includes(search);
        const matchesQuery = nameMatch || phoneMatch || cityMatch;

        let matchesQuality = true;
        if (quality !== 'ALL') {
            matchesQuality = (sub.noise_quality_estimate || '').includes(quality);
        }

        return matchesQuery && matchesQuality;
    });

    renderSubmissions(filtered);
}

function renderSubmissions(list) {
    const grid = document.getElementById('submissionsGrid');
    if (list.length === 0) {
        grid.innerHTML = '<div style="color: var(--text-muted); grid-column: 1/-1; text-align: center; padding: 3rem;">No matching audio submissions found.</div>';
        return;
    }

    grid.innerHTML = list.map(sub => `
        <div class="sub-card">
            <div class="sub-header">
                <div>
                    <div class="sub-name">${escapeHtml(sub.submitter_name)}</div>
                    <div class="sub-phone">${escapeHtml(sub.phone_number)} ${sub.candidate_city ? `· ${escapeHtml(sub.candidate_city)}` : ''}</div>
                </div>
                <span class="badge badge-blue">#${sub.id}</span>
            </div>

            <audio controls src="${sub.file_path}"></audio>

            <div class="meta-pills">
                <div class="meta-pill">
                    <span class="lbl">Duration</span>
                    <span class="val">${sub.duration_seconds}s</span>
                </div>
                <div class="meta-pill">
                    <span class="lbl">Sample</span>
                    <span class="val">${sub.sample_rate_khz} kHz</span>
                </div>
                <div class="meta-pill">
                    <span class="lbl">Bitrate</span>
                    <span class="val">${sub.bitrate_kbps} kbps</span>
                </div>
                <div class="meta-pill">
                    <span class="lbl">Loudness</span>
                    <span class="val">${sub.loudness_db} dB</span>
                </div>
            </div>

            <div style="margin-top: 0.6rem; display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0.6rem; background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 6px;">
                <div style="font-family: var(--font-mono); font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-dim);">
                    noise · ${escapeHtml(sub.noise_quality_estimate)}
                </div>
                <span class="badge ${sub.quality_score >= 80 ? 'badge-emerald' : sub.quality_score >= 60 ? 'badge-amber' : 'badge-rose'}">
                    ${sub.quality_score || 80}/100
                </span>
            </div>
        </div>
    `).join('');
}

// Utility Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast';
    
    let icon = 'fa-circle-info';
    if (type === 'success') icon = 'fa-circle-check';
    if (type === 'error') icon = 'fa-triangle-exclamation';

    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    loadSubmissions();
});
