import webrtcvad
import collections

class VADManager:
    def __init__(self, aggressiveness=3, sample_rate=16000, frame_duration=30, signal_emitter=None):
        print("Initializing WebRTC Voice Activity Detection...")
        try:
            self.vad = webrtcvad.Vad(aggressiveness)
            self.sample_rate = sample_rate
            self.frame_duration = frame_duration  # in milliseconds
            self.frame_size = int(sample_rate * frame_duration / 1000)  # samples per frame
            self.ring_buffer = collections.deque(maxlen=8)  # Buffer for voice frames
            self.triggered = False
            self.voiced_frames = []
            self.signal_emitter = signal_emitter
            
            print(f"WebRTC VAD initialized successfully (Aggressiveness Level: {aggressiveness})")
            print("Noise reduction is now active and ready")
            if self.signal_emitter:
                self.signal_emitter.status_changed.emit("✓ Noise reduction active")
                self.signal_emitter.new_message.emit("Noise reduction system is now active and ready", False)
        except Exception as e:
            print(f"Error initializing WebRTC VAD: {str(e)}")
            if self.signal_emitter:
                self.signal_emitter.status_changed.emit("⚠ Noise reduction failed")
                self.signal_emitter.new_message.emit(f"Could not initialize noise reduction: {str(e)}", False)
            raise

    def process_audio(self, audio_chunk):
        """Process audio chunk and determine if speech is present"""
        try:
            is_speech = self.vad.is_speech(audio_chunk, self.sample_rate)
            
            if not self.triggered:
                self.ring_buffer.append((audio_chunk, is_speech))
                num_voiced = len([f for f, speech in self.ring_buffer if speech])
                
                # Start collecting audio when enough voiced frames are detected
                if num_voiced > 0.5 * self.ring_buffer.maxlen:
                    self.triggered = True
                    self.voiced_frames = [f[0] for f in self.ring_buffer]
                    self.ring_buffer.clear()
                    return True, self.voiced_frames
            else:
                # Keep collecting audio until enough silence is detected
                self.voiced_frames.append(audio_chunk)
                self.ring_buffer.append((audio_chunk, is_speech))
                num_unvoiced = len([f for f, speech in self.ring_buffer if not speech])
                
                if num_unvoiced > 0.9 * self.ring_buffer.maxlen:
                    self.triggered = False
                    return False, self.voiced_frames
            
            return None, []
        except Exception as e:
            print(f"Error processing audio in VAD: {str(e)}")
            if self.signal_emitter:
                self.signal_emitter.status_changed.emit("⚠ Noise reduction error")
            return None, []

    def reset(self):
        """Reset the VAD state"""
        self.triggered = False
        self.ring_buffer.clear()
        self.voiced_frames = []
        if self.signal_emitter:
            self.signal_emitter.status_changed.emit("✓ Noise reduction active")