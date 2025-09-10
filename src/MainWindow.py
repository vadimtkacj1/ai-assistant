import sys
import os
import time
import threading
import speech_recognition as sr
import pyttsx3
from gtts import gTTS
import google.generativeai as genai
import json
import pvporcupine
import pyaudio
import struct
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                           QVBoxLayout, QFrame,
                           QHBoxLayout, QPushButton, QLabel,
                           QMessageBox)
from PyQt6.QtCore import (Qt, QTimer)
import pygame
from GlowingLabel import GlowingLabel
from SignalEmitter import SignalEmitter
from DynamicIsland import DynamicIsland
from ChatArea import ChatArea
from AnimatedButton import AnimatedButton
from GemminiManager import GeminiManager
from VADManager import VADManager
from dotenv import load_dotenv
import os
os.chdir('..')

load_dotenv()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Initialize variables
        self.is_suspended = False
        self.is_speaking = False
        self.speech_queue = []
        self.speech_lock = threading.Lock()
        self.speech_event = threading.Event()
        self.stop_speech = threading.Event()
        self.stop_wake_word = threading.Event()
        self._welcome_shown = False
        self.settings = {}
        
        # Window dragging variables
        self.old_pos = None
        self.start_resize = False
        self.edge = None
        self.start_pos = None
        self.start_geometry = None
        self.resize_margin = 5
        
        # Initialize audio resources to None
        self.porcupine = None
        self.wake_word_stream = None
        self.audio = None
        self.wake_word_thread = None
        self.listening_thread = None
        
        # Load settings
        self.load_settings()
        
        # Create signal emitter
        self.signal_emitter = SignalEmitter()
        
        # Create main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create content widget
        self.content_widget = QWidget()
        self.content_widget.setObjectName("mainContent")
        
        # Create content layout
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
                
        self.main_layout.addWidget(self.content_widget)
        
        # Initialize UI
        self.initUI()
        
        # Initialize speech components and start threads
        self.initialize_speech_components()
        self.start_threads()
        
        # Schedule welcome message
        QTimer.singleShot(2000, self._show_welcome)
        
    def _show_welcome(self):
        """Show welcome message when app starts"""
        if not self._welcome_shown:  
            welcome_msg = "Hi, your assistant is ready!"
            self.signal_emitter.new_message.emit(welcome_msg, False)
            self.speak(welcome_msg)
            self._welcome_shown = True

    def initUI(self):
        self.setWindowTitle('AI Assistant')
        # Set minimum and default size
        self.setMinimumSize(1024, 768)
        self.resize(1280, 800)
        
        # Create main background frame with simplified styling
        background_frame = QFrame(self.content_widget)
        background_frame.setObjectName("mainBackground")
        
        # Simplified CSS without unsupported properties
        background_frame.setStyleSheet("""
            QFrame#mainBackground {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(17, 24, 39, 240),
                    stop:0.25 rgba(30, 41, 59, 240),
                    stop:0.5 rgba(15, 23, 42, 240),
                    stop:0.75 rgba(17, 24, 39, 240),
                    stop:1 rgba(8, 8, 23, 240));
                border-radius: 32px;
                border: 2px solid rgba(147, 51, 234, 77);
                margin: 0px;
                padding: 0px;
            }
        """)
        
        # Create layout for background frame
        bg_layout = QVBoxLayout(background_frame)
        bg_layout.setContentsMargins(20, 20, 20, 20)  # Изменено с 32,32,32,32
        bg_layout.setSpacing(24)
        
        # Add background frame to content layout
        self.content_layout.addWidget(background_frame)
        self.content_layout.setContentsMargins(20, 20, 20, 20)  # Изменено с -20,0,0,0
        
        # Top controls with floating glass design
        top_controls = QHBoxLayout()
        top_controls.setSpacing(20)
        top_controls.setContentsMargins(12, 12, 12, 20)
        
        # Window control buttons
        window_controls = QHBoxLayout()
        window_controls.setSpacing(16)
        
        button_size = 40
        close_btn = QPushButton("✕")
        maximize_btn = QPushButton("⬜")
        minimize_btn = QPushButton("➖")
        
        # Simplified button styling without unsupported properties
        button_style = f"""
            QPushButton {{
                background: rgba(255, 255, 255, 25);
                color: rgba(255, 255, 255, 242);
                border: 1px solid rgba(255, 255, 255, 51);
                border-radius: {button_size//2}px;
                font-size: 14px;
                font-weight: 600;
                margin: 0px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 38);
                border: 1px solid rgba(147, 51, 234, 128);
                color: white;
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 20);
            }}
        """
        
        for btn in [close_btn, maximize_btn, minimize_btn]:
            btn.setFixedSize(button_size, button_size)
            btn.setStyleSheet(button_style)
        
        # Special styling for close button
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(251, 113, 133, 64),
                    stop:1 rgba(239, 68, 68, 64));
                color: white;
                border: 1px solid rgba(251, 113, 133, 102);
                border-radius: {button_size//2}px;
                font-size: 14px;
                font-weight: 600;
                margin: 0px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(251, 113, 133, 102),
                    stop:1 rgba(239, 68, 68, 102));
                border: 1px solid rgba(251, 113, 133, 153);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(251, 113, 133, 128),
                    stop:1 rgba(239, 68, 68, 128));
            }}
        """)
        
        close_btn.clicked.connect(self.close)
        maximize_btn.clicked.connect(self.toggle_maximize)
        minimize_btn.clicked.connect(self.showMinimized)
        
        window_controls.addWidget(minimize_btn)
        window_controls.addWidget(maximize_btn)
        window_controls.addWidget(close_btn)
        window_controls.addStretch()
        
        self.suspend_btn = AnimatedButton("🎙️")
        self.suspend_btn.setFixedSize(64, 64)
        self.suspend_btn.setCheckable(True)

        # Simplified control styling
        control_style = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(139, 92, 246, 64),
                    stop:0.5 rgba(79, 70, 229, 64),
                    stop:1 rgba(67, 56, 202, 64));
                color: white;
                border: 2px solid rgba(139, 92, 246, 102);
                border-radius: 32px;
                font-size: 28px;
                font-weight: 600;
                padding: 0px;
                margin: 0 12px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(139, 92, 246, 102),
                    stop:0.5 rgba(79, 70, 229, 102),
                    stop:1 rgba(67, 56, 202, 102));
                border: 2px solid rgba(139, 92, 246, 153);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(139, 92, 246, 128),
                    stop:0.5 rgba(79, 70, 229, 128),
                    stop:1 rgba(67, 56, 202, 128));
            }}
        """

        checked_style = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(16, 185, 129, 64),
                    stop:0.5 rgba(5, 150, 105, 64),
                    stop:1 rgba(4, 120, 87, 64));
                color: white;
                border: 2px solid rgba(16, 185, 129, 102);
                border-radius: 32px;
                font-size: 28px;
                font-weight: 600;
                padding: 0px;
                margin: 0 12px;
            }}
            QPushButton:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(245, 101, 101, 77),
                    stop:1 rgba(220, 38, 127, 77));
                border: 2px solid rgba(245, 101, 101, 153);
            }}
            QPushButton:hover {{
                border: 2px solid rgba(16, 185, 129, 153);
            }}
        """

        self.suspend_btn.setStyleSheets(checked_style, checked_style)
        self.suspend_btn.clicked.connect(self.toggle_suspension)
        
        top_controls.addLayout(window_controls)
        top_controls.addStretch()
        top_controls.addWidget(self.suspend_btn)
        bg_layout.addLayout(top_controls)
        
        # Status label with simplified styling
        self.status_label = GlowingLabel("Ready to assist you ✨")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 25),
                    stop:1 rgba(255, 255, 255, 13));
                color: rgba(255, 255, 255, 242);
                font-size: 18px;
                font-weight: 600;
                padding: 20px 40px;
                border-radius: 28px;
                border: 1px solid rgba(147, 51, 234, 77);
            }
        """)
        self.status_label.glow_animation.start()
        bg_layout.addWidget(self.status_label)
        
        # Dynamic Island
        self.dynamic_island = DynamicIsland()
        bg_layout.addWidget(self.dynamic_island, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Connect animation trigger signal
        self.signal_emitter.animation_trigger.connect(self.dynamic_island.animate)
        
        # Chat area
        self.chat_area = ChatArea()
        bg_layout.addWidget(self.chat_area)
        
        # Connect chat area command processor
        self.chat_area.set_command_processor(self.process_text_command)
        
        # Connect signal emitter to chat area
        self.signal_emitter.new_message.connect(self.chat_area.add_message)
        
        # Set window style with transparent background
        self.setStyleSheet("""
            QMainWindow {
                background: transparent;
            }
        """)

    def initialize_speech_components(self):
        """Initialize speech recognition and TTS components with improved error handling"""
        print("\nInitializing speech components...")
        
        # Clean up existing resources
        self.cleanup_audio_resources()
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 100
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5
        
        # Initialize VAD with improved error handling
        print("\nSetting up noise reduction...")
        try:
            vad_level = self.settings.get('vad_aggressiveness', 1)
            self.vad_manager = VADManager(aggressiveness=vad_level, signal_emitter=self.signal_emitter)
            print("Voice activity detection system is ready")
        except Exception as e:
            print(f"Warning: Could not initialize noise reduction: {str(e)}")
            self.vad_manager = None
            if hasattr(self, 'signal_emitter'):
                self.signal_emitter.status_changed.emit("⚠ Using basic voice detection")
        
        self.initialize_tts_engine()
        
        # Initialize wake word detection
        print("\nInitializing wake word detection...")
        try:
            porcupine_key = self.settings.get('porcupine_key', '').strip()
            if not porcupine_key:
                print("No Porcupine key found in settings")
                if hasattr(self, 'signal_emitter'):
                    self.signal_emitter.new_message.emit("Please add your Porcupine key in settings to enable wake word detection", False)
                self.porcupine = None
                return

            self.porcupine = pvporcupine.create(
                access_key=porcupine_key,
                keywords=['jarvis']  # Use lowercase to match available keywords
            )
            
            self.audio = pyaudio.PyAudio()
            
            # Find input device
            input_device_info = None
            for i in range(self.audio.get_device_count()):
                device_info = self.audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    print(f"Found input device: {device_info['name']}")
                    input_device_info = device_info
                    break
            
            if not input_device_info:
                raise Exception("No input device found")
                
            print(f"Using audio device: {input_device_info['name']}")
            print("Wake word detection initialized successfully")
            
            # Set initial status
            status_text = "Waiting for 'Jarvis' (Noise reduction active)" if self.vad_manager else "Waiting for 'Jarvis'"
            if hasattr(self, 'status_label'):
                self.status_label.setText(status_text)
                
            if hasattr(self, 'signal_emitter'):
                self.signal_emitter.new_message.emit("Wake word detection is active. Say 'Jarvis' to start.", False)
            self.base_status = status_text
            
        except Exception as e:
            print(f"Error initializing wake word detection: {str(e)}")
            self.porcupine = None
            if hasattr(self, 'signal_emitter'):
                self.signal_emitter.status_changed.emit("⚠ Wake word detection failed")
            
    def start_threads(self):
        """Start all background threads with better error handling"""
        print("\nStarting background threads...")
        
        # Initialize stop flags
        self.stop_wake_word = threading.Event()
        self.stop_speech = threading.Event()
        
        # Start speech processing thread
        try:
            self.speech_thread = threading.Thread(target=self.speech_worker, daemon=True)
            self.speech_thread.start()
            print("Speech processing thread started")
        except Exception as e:
            print(f"Error starting speech thread: {str(e)}")
        
        # Check API key and initialize Gemini
        api_key = self.settings.get('gemini_api_key', '').strip()
        gemmini_manager = GeminiManager.get_instance()
        
        if api_key:
            if gemmini_manager.initialize(api_key):
                print("API key validated, starting voice features...")
                
                # Start appropriate listening thread based on wake word availability
                if self.porcupine:
                    print("Starting wake word detection thread...")
                    try:
                        self.wake_word_thread = threading.Thread(target=self.wake_word_listener, daemon=True)
                        self.wake_word_thread.start()
                        print("Wake word detection thread started")
                    except Exception as e:
                        print(f"Error starting wake word thread: {str(e)}")
                else:
                    print("Starting fallback listening thread...")
                    try:
                        self.listening_thread = threading.Thread(target=self.background_listening, daemon=True)
                        self.listening_thread.start()
                        print("Fallback listening thread started")
                    except Exception as e:
                        print(f"Error starting listening thread: {str(e)}")
                
                if hasattr(self, 'signal_emitter'):
                    self.signal_emitter.new_message.emit("✓ Voice features are now enabled and ready to use.", False)
                    
                if hasattr(self, 'status_label'):
                    if self.vad_manager:
                        self.status_label.setText("Waiting for 'Jarvis' (Noise reduction active)")
                    else:
                        self.status_label.setText("Waiting for 'Jarvis'")
            else:
                print("Voice features disabled - invalid API key")
                if hasattr(self, 'signal_emitter'):
                    self.signal_emitter.new_message.emit("⚠️ Voice features are disabled. The provided API key appears to be invalid.", False)
        else:
            print("Voice features disabled - no API key configured")
            if hasattr(self, 'signal_emitter'):
                self.signal_emitter.new_message.emit("⚠️ Voice features are disabled. Please configure your API key in Settings to enable all features.", False)
            
        print("All background threads initialized")

    def cleanup_audio_resources(self):
        """Clean up audio resources efficiently"""
        resources = [
            ('porcupine', 'delete'),
            ('wake_word_stream', 'close'),
            ('audio', 'terminate')
        ]
        
        for attr_name, cleanup_method in resources:
            if hasattr(self, attr_name):
                try:
                    resource = getattr(self, attr_name)
                    if resource:
                        if hasattr(resource, cleanup_method):
                            getattr(resource, cleanup_method)()
                        setattr(self, attr_name, None)
                except Exception as e:
                    print(f"Error cleaning up {attr_name}: {str(e)}")
            
        # Stop threads safely
        if hasattr(self, 'stop_wake_word'):
            self.stop_wake_word.set()
            
        # Wait for threads to stop
        for thread_name in ['wake_word_thread', 'listening_thread']:
            if hasattr(self, thread_name):
                thread = getattr(self, thread_name)
                if thread and thread.is_alive():
                    try:
                        thread.join(timeout=1.0)
                    except Exception as e:
                        print(f"Error stopping {thread_name}: {str(e)}")

    def closeEvent(self, event):
        """Clean shutdown when window is closed"""
        print("Shutting down application...")
        
        # Set stop flags
        if hasattr(self, 'stop_wake_word'):
            self.stop_wake_word.set()
        if hasattr(self, 'stop_speech'):
            self.stop_speech.set()
            
        # Clean up audio resources
        self.cleanup_audio_resources()
        
        # Accept the close event
        event.accept()

    # ... (rest of the methods remain the same as in your original code)
    
    def speech_worker(self):
        """Dedicated thread for handling speech output"""
        while not self.stop_speech.is_set():
            try:
                # Wait for speech to be queued or stop signal
                if self.speech_event.wait(timeout=1.0):
                    with self.speech_lock:
                        if self.speech_queue:
                            speech_type, content = self.speech_queue.pop(0)
                        else:
                            self.speech_event.clear()
                            # Reset to idle when queue is empty
                            try:
                                if not self.is_suspended and hasattr(self, 'signal_emitter'):
                                    self.signal_emitter.animation_trigger.emit("idle")
                            except:
                                pass
                            continue
                    
                    if not self.is_suspended and not self.stop_speech.is_set():
                        self.is_speaking = True
                        try:
                            if hasattr(self, 'signal_emitter'):
                                self.signal_emitter.animation_trigger.emit("speaking")
                        except:
                            pass
                            
                        try:
                            if speech_type == 'file':
                                # Play MP3 file using system default player
                                if sys.platform == 'win32':
                                    abs_path = os.path.abspath(content)
                                    os.system(f'powershell -c "(New-Object Media.SoundPlayer \'{abs_path}\').PlaySync()"')
                                elif sys.platform == 'darwin':
                                    os.system(f'afplay "{content}"')
                                else:
                                    os.system(f'mpg123 "{content}"')
                                # Clean up temp file
                                try:
                                    if os.path.exists(content):
                                        os.remove(content)
                                except:
                                    pass
                            else:
                                if hasattr(self, 'engine'):
                                    self.engine.say(content)
                                    self.engine.runAndWait()
                        except Exception as e:
                            print(f"Error in speech output: {str(e)}")
                        finally:
                            self.is_speaking = False
                            
                            # Reset to idle after speaking
                            if not self.speech_queue:
                                try:
                                    if not self.is_suspended and hasattr(self, 'signal_emitter'):
                                        self.signal_emitter.animation_trigger.emit("idle")
                                except:
                                    pass
            except Exception as e:
                print(f"Error in speech worker: {str(e)}")
                time.sleep(0.1)  # Prevent tight loop on error
                
    def wake_word_listener(self):
        """Background thread for wake word detection using Porcupine"""
        try:
            if not self.porcupine or not self.audio:
                print("Wake word detection not properly initialized")
                return
                
            self.wake_word_stream = self.audio.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length,
                stream_callback=None
            )
            
            while not self.stop_wake_word.is_set():
                if self.is_suspended:
                    time.sleep(0.1)
                    continue
                
                try:
                    pcm = self.wake_word_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                    pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                    
                    result = self.porcupine.process(pcm)
                    if result >= 0:  # Wake word detected
                        print("Wake word detected!")
                        
                        # Stop current speech if any
                        self.stop_speaking()
                        
                        # Update UI and play acknowledgment
                        if hasattr(self, 'status_label'):
                            self.status_label.setText("Listening...")
                        self.speak("Yes?")
                        
                        time.sleep(0.5)  # Wait for acknowledgment
                        
                        # Temporarily stop wake word detection
                        self.wake_word_stream.stop_stream()
                        
                        # Listen for command using Google Speech Recognition
                        with sr.Microphone() as source:
                            try:
                                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                                
                                # Recognize command in English only
                                command = self.recognizer.recognize_google(
                                    audio,
                                    language="en-US",
                                    show_all=False
                                )
                                
                                print(f"Received command: {command}")
                                if hasattr(self, 'signal_emitter'):
                                    self.signal_emitter.animation_trigger.emit("listening")
                                    # Add user message to chat
                                    self.signal_emitter.new_message.emit(command, True)
                                
                                # Process command through existing logic
                                self.process_text_command(command)
                            
                            except sr.UnknownValueError:
                                error_msg = "Sorry, I didn't catch that. Could you please repeat?"
                                if hasattr(self, 'signal_emitter'):
                                    self.signal_emitter.new_message.emit(error_msg, False)
                                self.speak(error_msg)
                            except sr.RequestError as e:
                                error_msg = f"Sorry, there was an error with the speech recognition service: {str(e)}"
                                if hasattr(self, 'signal_emitter'):
                                    self.signal_emitter.new_message.emit(error_msg, False)
                                self.speak(error_msg)
                            finally:
                                # Resume wake word detection
                                if hasattr(self, 'wake_word_stream') and self.wake_word_stream:
                                    self.wake_word_stream.start_stream()
                                if hasattr(self, 'signal_emitter'):
                                    self.signal_emitter.animation_trigger.emit("idle")
                                
                                # Reset UI state
                                if hasattr(self, 'status_label'):
                                    if self.vad_manager:
                                        status_msg = "Waiting for 'Jarvis' (Noise reduction active)"
                                    else:
                                        status_msg = "Waiting for 'Jarvis'"
                                    self.status_label.setText(status_msg)
                except Exception as e:
                    if not self.stop_wake_word.is_set():
                        print(f"Error in wake word processing: {str(e)}")
                    time.sleep(0.1)
                    continue
                    
        except Exception as e:
            print(f"Error in wake word listener: {str(e)}")
        finally:
            if hasattr(self, 'wake_word_stream') and self.wake_word_stream:
                try:
                    self.wake_word_stream.stop_stream()
                    self.wake_word_stream.close()
                    self.wake_word_stream = None
                except:
                    pass

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def stop_speaking(self):
        """Stop any ongoing speech and clear the queue"""
        try:
            # Stop any ongoing speech
            if hasattr(self, 'engine'):
                self.engine.stop()
            
            # Stop any playing audio
            if sys.platform == 'win32':
                os.system('taskkill /F /IM wmplayer.exe 2>NUL')
            elif sys.platform == 'darwin':
                os.system('killall afplay 2>/dev/null')
            else:
                os.system('killall mpg123 2>/dev/null')
            
            # Clear the speech queue
            with self.speech_lock:
                self.speech_queue.clear()
                self.speech_event.clear()
            
            # Reset speaking state
            self.is_speaking = False
            self.signal_emitter.animation_trigger.emit("idle")
            
        except Exception as e:
            print(f"Error stopping speech: {str(e)}")

    def toggle_suspension(self):
        """Toggle voice recognition suspension"""
        self.is_suspended = self.suspend_btn.isChecked()
        
        if self.is_suspended:
            self.suspend_btn.setText("🔇")
            self.status_label.setText("Assistant is suspended")
            self.dynamic_island.animate("idle")
            self.stop_speaking()
        else:
            if self.initialize_tts_engine():
                self.suspend_btn.setText("🎤")
                self.status_label.setText("Waiting for 'Jarvis'...")
                self.speak("Assistant ready")
            else:
                self.is_suspended = True
                self.suspend_btn.setChecked(True)
                self.status_label.setText("Error: Could not initialize speech. Please try again.")

    def background_listening(self):
        """Basic listening method when wake word detection is not available"""
        print("Starting basic listening mode...")
        
        while not self.stop_wake_word.is_set():
            if self.is_suspended:
                time.sleep(0.1)
                continue
                
            try:
                with sr.Microphone() as source:
                    print("Listening for commands...")
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    
                    try:
                        # Recognize command in English only
                        command = self.recognizer.recognize_google(
                            audio,
                            language="en-US",
                            show_all=False
                        )
                        
                        print(f"Received command: {command}")
                        self.signal_emitter.animation_trigger.emit("listening")
                        
                        # Add user message to chat
                        self.signal_emitter.new_message.emit(command, True)
                        
                        # Process command through existing logic
                        self.process_text_command(command)
                        
                    except sr.UnknownValueError:
                        # No speech detected, continue listening
                        pass
                    except sr.RequestError as e:
                        error_msg = f"Sorry, there was an error with the speech recognition service: {str(e)}"
                        self.signal_emitter.new_message.emit(error_msg, False)
                        self.speak(error_msg)
                        time.sleep(2)  # Wait before retrying
                        
            except Exception as e:
                print(f"Error in background listening: {str(e)}")
                time.sleep(0.1)  # Prevent tight loop on error
                
        print("Background listening stopped")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Get the position of the mouse relative to the window
            self.edge = self.get_edge(event.position().toPoint())
            if self.edge:
                # If on an edge, start resize
                self.start_resize = True
                self.start_pos = event.globalPosition().toPoint()
                self.start_geometry = self.geometry()
            elif event.position().y() < 50:  # Top area for moving
                self.old_pos = event.globalPosition().toPoint()
            else:
                self.old_pos = None
                self.start_resize = False

    def mouseMoveEvent(self, event):
        if hasattr(self, 'start_resize') and self.start_resize:
            # Handle resizing
            delta = event.globalPosition().toPoint() - self.start_pos
            new_geometry = self.start_geometry
            
            if self.edge & Qt.Edge.LeftEdge:
                new_geometry.setLeft(new_geometry.left() + delta.x())
            if self.edge & Qt.Edge.RightEdge:
                new_geometry.setRight(new_geometry.right() + delta.x())
            if self.edge & Qt.Edge.TopEdge:
                new_geometry.setTop(new_geometry.top() + delta.y())
            if self.edge & Qt.Edge.BottomEdge:
                new_geometry.setBottom(new_geometry.bottom() + delta.y())
                
            # Ensure minimum size
            if new_geometry.width() >= self.minimumWidth() and new_geometry.height() >= self.minimumHeight():
                self.setGeometry(new_geometry)
        
        elif self.old_pos and not self.isMaximized():
            # Handle window dragging
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()
        else:
            # Update cursor based on position
            edge = self.get_edge(event.position().toPoint())
            if edge & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif edge & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif edge & (Qt.Edge.TopEdge | Qt.Edge.LeftEdge) or edge & (Qt.Edge.BottomEdge | Qt.Edge.RightEdge):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif edge & (Qt.Edge.TopEdge | Qt.Edge.RightEdge) or edge & (Qt.Edge.BottomEdge | Qt.Edge.LeftEdge):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self.start_resize = False
        self.old_pos = None
        self.edge = 0

    def get_edge(self, pos):
        margin = self.resize_margin
        width = self.width()
        height = self.height()
        
        # Determine which edge the cursor is near
        edge = Qt.Edge(0)
        
        if pos.x() <= margin:
            edge |= Qt.Edge.LeftEdge
        if pos.x() >= width - margin:
            edge |= Qt.Edge.RightEdge
        if pos.y() <= margin:
            edge |= Qt.Edge.TopEdge
        if pos.y() >= height - margin:
            edge |= Qt.Edge.BottomEdge
            
        return edge

    def mouseDoubleClickEvent(self, event):
        if event.position().y() < 50:  # Top area
            self.toggle_maximize()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def initialize_tts_engine(self):
        """Initialize or reinitialize the text-to-speech engine"""
        try:
            if hasattr(self, 'engine'):
                self.engine.stop()
                del self.engine
            self.engine = pyttsx3.init()
            
            # Configure engine properties
            self.engine.setProperty('rate', 150)  # Speed of speech
            self.engine.setProperty('volume', 1.0)  # Volume level
            
            # Set voice gender based on settings
            voices = self.engine.getProperty('voices')
            voice_gender = self.settings.get('voice_gender', 'male')
            speech_language = self.settings.get('speech_language', 'en-US')
            
            # Find appropriate voice based on gender and language
            selected_voice = None
            for voice in voices:
                # Check if voice name or ID contains gender indicator and language
                voice_info = voice.name.lower() + ' ' + voice.id.lower()
                if speech_language.startswith('ar'):
                    # For Arabic, prioritize Arabic voices
                    if 'arabic' in voice_info or 'ar' in voice_info:
                        selected_voice = voice
                        break
                else:
                    # For other languages, match gender
                    if voice_gender == 'male' and ('male' in voice_info or 'david' in voice_info):
                        selected_voice = voice
                        break
                    elif voice_gender == 'female' and ('female' in voice_info or 'zira' in voice_info):
                        selected_voice = voice
                        break
            
            # If we found a matching voice, use it
            if selected_voice:
                self.engine.setProperty('voice', selected_voice.id)
            # If no matching voice found, use first available voice
            elif voices:
                self.engine.setProperty('voice', voices[0].id)
                print(f"Warning: No matching voice found for {voice_gender} gender and {speech_language} language")
            
            return True
        except Exception as e:
            print(f"Error initializing TTS engine: {str(e)}")
            return False

    def cleanup_audio_resources(self):
        """Clean up audio resources efficiently"""
        resources = [
            ('porcupine', 'delete'),
            ('wake_word_stream', 'close'),
            ('audio', 'terminate')
        ]
        
        for attr_name, cleanup_method in resources:
            if hasattr(self, attr_name):
                try:
                    resource = getattr(self, attr_name)
                    if resource:
                        getattr(resource, cleanup_method)()
                        setattr(self, attr_name, None)
                except Exception as e:
                    print(f"Error cleaning up {attr_name}: {str(e)}")
            
        # Ensure PyAudio instance is clean
        if hasattr(self, 'audio'):
            try:
                self.audio.terminate()
                self.audio = pyaudio.PyAudio()
            except Exception as e:
                print(f"Error resetting PyAudio: {str(e)}")

    def resume_wake_word_detection(self):
        """Resume wake word detection after command processing"""
        try:
            # Clean up any existing stream
            if hasattr(self, 'wake_word_stream') and self.wake_word_stream:
                if self.wake_word_stream.is_active():
                    self.wake_word_stream.stop_stream()
                self.wake_word_stream.close()
                self.wake_word_stream = None
            
            # Ensure we have a fresh PyAudio instance
            if not hasattr(self, 'audio') or self.audio is None:
                self.audio = pyaudio.PyAudio()
            
            # Create new stream
            self.wake_word_stream = self.audio.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length,
                stream_callback=None
            )
            
            # Start the stream
            self.wake_word_stream.start_stream()
            
        except Exception as e:
            print(f"Error resuming wake word detection: {str(e)}")
            # If we fail to resume, try to reinitialize everything
            try:
                self.initialize_speech_components()
            except Exception as e2:
                print(f"Error reinitializing speech components: {str(e2)}")

    def load_settings(self):
        """Load settings from file and environment variables"""
        try:
            print("Debug: Starting to load settings")
            
            # Load from environment variables first
            gemini_key = os.getenv('GEMINI_API_KEY', '')
            porcupine_key = os.getenv('PORCUPINE_API_KEY', '')

            # Override with environment variables if they exist
            if gemini_key:
                self.settings['gemini_api_key'] = gemini_key
                print("Debug: Using Gemini API key from environment")
            elif 'gemini_api_key' not in self.settings:
                self.settings['gemini_api_key'] = ''
                
            if porcupine_key:
                self.settings['porcupine_key'] = porcupine_key
                print("Debug: Using Porcupine API key from environment")
            elif 'porcupine_key' not in self.settings:
                self.settings['porcupine_key'] = ''
            
            # Set other defaults
            self.settings.setdefault('gemini_model', 'gemini-2.0-flash')
            self.settings.setdefault('voice_gender', 'male')
            self.settings.setdefault('vad_aggressiveness', 3)
            
            print(f"Debug: API key present: {bool(self.settings.get('gemini_api_key', '').strip())}")
            print(f"Debug: Porcupine key present: {bool(self.settings.get('porcupine_key', '').strip())}")
            
        except Exception as e:
            print(f"Debug: Error loading settings: {str(e)}")
            # Initialize with default settings if loading fails
            self.settings = {
                'gemini_api_key': os.getenv('GEMINI_API_KEY', ''),
                'gemini_model': 'gemini-2.0-flash',
                'porcupine_key': os.getenv('PORCUPINE_API_KEY', ''),
                'voice_gender': 'male',
                'vad_aggressiveness': 3
            }

    def save_settings(self):
        """Save settings to file and update main window"""
        try:
            # Get new API keys and compare with old ones
            new_api_key = self.gemini_key_input.text().strip()
            old_api_key = self.settings.get('gemini_api_key', '')
            new_porcupine_key = self.porcupine_key_input.text().strip()
            old_porcupine_key = self.settings.get('porcupine_key', '')
            
            # Update settings from UI
            self.settings['gemini_api_key'] = new_api_key
            self.settings['gemini_model'] = self.model_selector.currentData()
            self.settings['porcupine_key'] = new_porcupine_key
            self.settings['voice_gender'] = 'male' if self.voice_gender_selector.currentText() == "Male Voice" else 'female'
            
            # Get language setting
            language_text = self.language_selector.currentText()
            if language_text == "English":
                self.settings['speech_language'] = 'en-US'
            elif language_text == "Arabic":
                self.settings['speech_language'] = 'ar-SA'
            else:  # English & Arabic
                self.settings['speech_language'] = 'bilingual'
                
            # Handle API key changes
            restart_required = False
            gemmini_manager = GeminiManager.get_instance()

            if new_api_key != old_api_key:
                if gemmini_manager.initialize(new_api_key):
                    if not old_api_key:
                        # Find the MainWindow
                        main_window = self
                        while main_window and not isinstance(main_window, MainWindow):
                            main_window = main_window.parent()
                            
                        if main_window:
                            # Stop any existing threads
                            if hasattr(main_window, 'wake_word_thread') and main_window.wake_word_thread:
                                main_window.stop_wake_word.set()
                                main_window.wake_word_thread.join(timeout=1)
                            if hasattr(main_window, 'listening_thread') and main_window.listening_thread:
                                main_window.stop_wake_word.set()
                                main_window.listening_thread.join(timeout=1)
                            
                            # Reset stop flag
                            main_window.stop_wake_word.clear()
                            
                            # Initialize speech components and start threads
                            main_window.initialize_speech_components()
                            main_window.start_threads()
                            QMessageBox.information(self, "Success", "API key configured successfully. Voice features have been enabled.")
                        else:
                            QMessageBox.information(self, "Success", "API key configured successfully. Please restart to enable voice features.")
                            restart_required = True
                    else:
                        QMessageBox.information(self, "Success", "API key updated successfully.")
                else:
                    if new_api_key:
                        QMessageBox.warning(self, "Warning", "Invalid API key. Voice features will remain disabled.")
                    else:
                        QMessageBox.warning(self, "Warning", "No API key provided. Voice features will be disabled.")
                        
            # Handle Porcupine key changes
            if new_porcupine_key != old_porcupine_key:
                if new_porcupine_key:
                    restart_required = True
                    QMessageBox.information(self, "Success", "Wake word detection will be enabled after restart.")
                else:
                    QMessageBox.warning(self, "Notice", "Wake word detection will be disabled.")
            
            # Save to file
            with open('settings.json', 'w') as f:
                json.dump(self.settings, f, indent=4)
            
            # Find the MainWindow by traversing up the widget hierarchy
            parent = self.parent()
            while parent and not isinstance(parent, QMainWindow):
                parent = parent.parent()
            
            # Update main window if found
            if parent:
                # Reinitialize TTS engine with new voice settings
                if parent.initialize_tts_engine():
                    parent.speak("Settings saved successfully")
            
            if restart_required:
                response = QMessageBox.question(
                    self, 
                    "Restart Required",
                    "Some changes require a restart to take effect. Would you like to restart now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if response == QMessageBox.StandardButton.Yes:
                    QApplication.quit()
                    os.execl(sys.executable, sys.executable, *sys.argv)
            else:
                QMessageBox.information(self, "Success", "Settings saved successfully!")
                
        except Exception as e:
            print(f"Debug: Error saving settings: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def process_text_command(self, command):
        """Process commands from text input"""
        try:    
            # If it's not a device, camera, app, or code command, process with Gemini
            try:
                self.signal_emitter.status_changed.emit("Processing your request...")
                # Configure Gemini with API key from settings
                api_key = self.settings.get('gemini_api_key', '').strip()
                gemmini_manager = GeminiManager.get_instance()
                if gemmini_manager.initialize(api_key):
                    # Get validated model name
                    print(self.settings.get('gemini_model'))
                    model_name = gemmini_manager.get_valid_model_name(self.settings.get('gemini_model'))
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(command)
                    response_text = response.text if response and hasattr(response, 'text') else "Sorry, I couldn't process that request."
                    
                    # Add assistant message to chat
                    self.signal_emitter.new_message.emit(str(response_text), False)
                    self.speak(response_text)
                else:
                    error_msg = "Gemini API key not configured. Please add your API key in settings."
                    self.signal_emitter.new_message.emit(error_msg, False)
                    self.speak(error_msg)
            except Exception as e:
                error_msg = f"Error processing with Gemini: {str(e)}"
                print(error_msg)
                self.signal_emitter.new_message.emit("Sorry, I encountered an error processing your request.", False)
                self.speak("Sorry, I encountered an error processing your request.")
            
        except Exception as e:
            print(f"Error processing text command: {str(e)}")
            self.signal_emitter.new_message.emit(f"Error: {str(e)}", False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Get the position of the mouse relative to the window
            self.edge = self.get_edge(event.position().toPoint())
            if self.edge:
                # If on an edge, start resize
                self.start_resize = True
                self.start_pos = event.globalPosition().toPoint()
                self.start_geometry = self.geometry()
            elif event.position().y() < 50:  # Top area for moving
                self.old_pos = event.globalPosition().toPoint()
            else:
                self.old_pos = None
                self.start_resize = False

    def clean_text_for_tts(self, text):
        """Clean text before sending to TTS engine by removing special characters and formatting"""
        import re
        
        # Replace common special characters and formatting
        replacements = {
            '\n': ' ',          # Replace newlines with spaces
            '\t': ' ',          # Replace tabs with spaces
            '•': '',            # Remove bullet points
            '*': '',            # Remove asterisks
            '`': '',            # Remove backticks
            '|': ',',           # Replace pipes with commas
            '_': ' ',           # Replace underscores with spaces
            '...': ',',         # Replace ellipsis with comma
            '---': ',',         # Replace em dashes with comma
            '--': ',',          # Replace en dashes with comma
            '~': '',            # Remove tildes
            '>': '',            # Remove quote markers
            '<': '',            # Remove quote markers
            '[]': '',           # Remove empty brackets
            '()': '',           # Remove empty parentheses
            '{}': '',           # Remove empty braces
        }
        
        # Apply all replacements
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove spaces before punctuation
        text = re.sub(r'\s+([,.!?])', r'\1', text)
        
        # Clean up multiple commas
        text = re.sub(r',\s*,', ',', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text

    def speak(self, text):
        """Queue text for speaking after cleaning"""
        if not self.is_suspended:
            # Clean the text before queuing
            cleaned_text = self.clean_text_for_tts(text)
            
            # Check if text contains Arabic characters
            if any(ord(char) in range(0x0600, 0x06FF) for char in cleaned_text):
                def tts_worker():
                    temp_file = None
                    mixer_initialized = False
                    try:
                        import tempfile
                        import time
                        
                        # Create a temporary file with proper permissions
                        temp_dir = tempfile.gettempdir()
                        temp_file = os.path.join(temp_dir, f'arabic_speech_{int(time.time())}.mp3')
                        
                        # Use gTTS for Arabic text
                        tts = gTTS(text=cleaned_text, lang='ar')
                        tts.save(temp_file)
                        
                        # Make sure pygame is not initialized
                        try:
                            pygame.mixer.quit()
                            time.sleep(0.1)  # Give time for resources to be released
                        except:
                            pass
                            
                        # Initialize pygame with proper settings
                        try:
                            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                            mixer_initialized = True
                            
                            pygame.mixer.music.load(temp_file)
                            self.signal_emitter.animation_trigger.emit("speaking")
                            pygame.mixer.music.play()
                            
                            # Wait for playback to complete
                            while pygame.mixer.music.get_busy():
                                pygame.time.Clock().tick(10)
                                
                        except Exception as e:
                            print(f"Pygame error: {str(e)}, falling back to system audio")
                            # Fallback to system audio player if pygame fails
                            if sys.platform == 'win32':
                                os.system(f'powershell -c "(New-Object Media.SoundPlayer \'{temp_file}\').PlaySync()"')
                            elif sys.platform == 'darwin':
                                os.system(f'afplay "{temp_file}"')
                            else:
                                os.system(f'mpg123 "{temp_file}"')
                                
                    except Exception as e:
                        print(f"TTS error: {str(e)}")
                        self.signal_emitter.animation_trigger.emit("idle")
                        
                        # Fallback to regular TTS
                        with self.speech_lock:
                            self.speech_queue.append(('text', cleaned_text))
                            self.speech_event.set()
                        
                    finally:
                        # Clean up pygame
                        if mixer_initialized:
                            try:
                                pygame.mixer.music.stop()
                                pygame.mixer.quit()
                            except:
                                pass
                                
                        # Clean up the temporary file
                        if temp_file and os.path.exists(temp_file):
                            try:
                                os.remove(temp_file)
                            except Exception as e:
                                print(f"Error removing temporary file: {str(e)}")
                        
                        self.signal_emitter.animation_trigger.emit("idle")
                
                # Start TTS generation and playback in a thread
                tts_thread = threading.Thread(target=tts_worker)
                tts_thread.daemon = True
                tts_thread.start()
            else:
                # Use pyttsx3 for non-Arabic text
                with self.speech_lock:
                    self.speech_queue.append(('text', cleaned_text))
                    self.speech_event.set()
                    
                # Trigger speaking animation
                self.signal_emitter.animation_trigger.emit("speaking")

    def stop_speaking(self):
        """Stop any ongoing speech and clear the queue"""
        try:
            # Stop any ongoing speech
            if hasattr(self, 'engine'):
                self.engine.stop()
            
            # Stop any playing audio
            if sys.platform == 'win32':
                os.system('taskkill /F /IM wmplayer.exe 2>NUL')
            elif sys.platform == 'darwin':
                os.system('killall afplay 2>/dev/null')
            else:
                os.system('killall mpg123 2>/dev/null')
            
            # Clear the speech queue
            with self.speech_lock:
                self.speech_queue.clear()
                self.speech_event.clear()
            
            # Reset speaking state
            self.is_speaking = False
            self.signal_emitter.animation_trigger.emit("idle")
            
        except Exception as e:
            print(f"Error stopping speech: {str(e)}")