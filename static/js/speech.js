/**
 * Speech-to-text module for Chat Arena
 * Uses Web Speech API as primary, with Whisper API fallback
 */
const Speech = {
    recognition: null,
    mediaRecorder: null,
    audioChunks: [],
    isRecording: false,
    currentTarget: null,
    useWhisper: false,

    /**
     * Initialize speech recognition
     */
    init() {
        // Check for Web Speech API support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (SpeechRecognition) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';

            this.recognition.onresult = (event) => {
                const transcript = Array.from(event.results)
                    .map(result => result[0].transcript)
                    .join('');

                if (this.currentTarget) {
                    this.currentTarget.value = transcript;
                    this.currentTarget.dispatchEvent(new Event('input'));
                }
            };

            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.stopRecording();

                // Fall back to Whisper on certain errors
                if (event.error === 'not-allowed' || event.error === 'service-not-available') {
                    this.useWhisper = true;
                }
            };

            this.recognition.onend = () => {
                this.stopRecording();
            };
        } else {
            console.log('Web Speech API not supported, using Whisper fallback');
            this.useWhisper = true;
        }

        this.setupButtons();
    },

    /**
     * Setup microphone button event listeners
     */
    setupButtons() {
        const thinkMicBtn = document.getElementById('think-mic-btn');
        const speechMicBtn = document.getElementById('speech-mic-btn');
        const thinkInput = document.getElementById('think-input');
        const speechInput = document.getElementById('speech-input');

        if (thinkMicBtn) {
            thinkMicBtn.addEventListener('click', () => {
                this.toggleRecording(thinkInput, thinkMicBtn);
            });
        }

        if (speechMicBtn) {
            speechMicBtn.addEventListener('click', () => {
                if (!speechMicBtn.disabled) {
                    this.toggleRecording(speechInput, speechMicBtn);
                }
            });
        }
    },

    /**
     * Toggle recording state
     */
    toggleRecording(targetInput, button) {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            this.startRecording(targetInput, button);
        }
    },

    /**
     * Start recording/recognition
     */
    async startRecording(targetInput, button) {
        this.currentTarget = targetInput;
        this.isRecording = true;
        button.classList.add('recording');

        if (this.useWhisper) {
            await this.startWhisperRecording();
        } else {
            try {
                this.recognition.start();
            } catch (e) {
                console.error('Failed to start recognition:', e);
                this.useWhisper = true;
                await this.startWhisperRecording();
            }
        }
    },

    /**
     * Stop recording/recognition
     */
    stopRecording() {
        this.isRecording = false;

        // Remove recording class from all mic buttons
        document.querySelectorAll('.btn-mic').forEach(btn => {
            btn.classList.remove('recording');
        });

        if (this.recognition && !this.useWhisper) {
            try {
                this.recognition.stop();
            } catch (e) {
                // Ignore errors when stopping
            }
        }

        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
        }
    },

    /**
     * Start Whisper-based recording
     */
    async startWhisperRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.audioChunks = [];

            this.mediaRecorder = new MediaRecorder(stream);

            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = async () => {
                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());

                // Create audio blob
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                await this.transcribeWithWhisper(audioBlob);
            };

            this.mediaRecorder.start();
        } catch (e) {
            console.error('Failed to access microphone:', e);
            this.stopRecording();
            UI.showError('Microphone access denied. Please enable microphone permissions.');
        }
    },

    /**
     * Send audio to Whisper API for transcription
     */
    async transcribeWithWhisper(audioBlob) {
        try {
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');

            const response = await fetch('/api/transcribe', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Transcription failed');
            }

            const result = await response.json();

            if (this.currentTarget && result.text) {
                // Append to existing text
                const existingText = this.currentTarget.value;
                this.currentTarget.value = existingText + (existingText ? ' ' : '') + result.text;
                this.currentTarget.dispatchEvent(new Event('input'));
            }
        } catch (e) {
            console.error('Whisper transcription failed:', e);
            UI.showError('Speech-to-text failed. Please try again or type manually.');
        }
    },

    /**
     * Check if speech recognition is available
     */
    isAvailable() {
        return !!(window.SpeechRecognition || window.webkitSpeechRecognition) || this.useWhisper;
    }
};

// Export
window.Speech = Speech;
