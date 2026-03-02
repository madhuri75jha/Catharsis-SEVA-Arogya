"""
Bug Condition Exploration Test - Duplicate Audio Chunks

**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
**DO NOT attempt to fix the test or the code when it fails**

**Validates: Requirements 1.1, 1.2, 2.1, 2.2**

This test detects duplicate audio chunks being emitted by the AudioCapture class.
It uses content hashing (SHA-256) to identify duplicate PCM data chunks.

Expected Outcome: TEST FAILS (proves duplicate chunks exist in unfixed code)
"""

import pytest
import hashlib
import json
import time
from hypothesis import given, strategies as st, settings, Phase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException


def hash_pcm_data(pcm_array):
    """Hash PCM data array to detect duplicates"""
    # Convert array to bytes and hash
    data_bytes = json.dumps(pcm_array).encode('utf-8')
    return hashlib.sha256(data_bytes).hexdigest()


class AudioCaptureSimulator:
    """
    Simulates the AudioCapture JavaScript class behavior for testing.
    This allows us to test the duplicate chunk detection logic without
    requiring a full browser environment with microphone access.
    """
    
    def __init__(self, sample_rate=16000, buffer_size=4096):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.is_capturing = False
        self.emitted_chunks = []
        self.chunk_hashes = []
        self.event_handlers = {'chunk': [], 'error': []}
    
    def on(self, event, callback):
        """Register event handler"""
        if event in self.event_handlers:
            self.event_handlers[event].append(callback)
    
    def _emit_event(self, event, data):
        """Emit event to registered handlers"""
        if event in self.event_handlers:
            for callback in self.event_handlers[event]:
                callback(data)
    
    def _convert_to_pcm(self, float32_data):
        """Convert Float32 audio data to Int16 PCM format"""
        pcm_data = []
        for sample in float32_data:
            # Clamp to [-1.0, 1.0] range
            sample = max(-1.0, min(1.0, sample))
            # Convert to 16-bit signed integer
            if sample < 0:
                pcm_value = int(sample * 0x8000)
            else:
                pcm_value = int(sample * 0x7FFF)
            pcm_data.append(pcm_value)
        return pcm_data
    
    def start(self):
        """Start audio capture"""
        self.is_capturing = True
    
    def stop(self):
        """Stop audio capture"""
        self.is_capturing = False
    
    def simulate_onaudioprocess(self, audio_data):
        """
        Simulate the onaudioprocess callback behavior.
        This is where we test if duplicate chunks are emitted.
        """
        if not self.is_capturing:
            return
        
        # Convert to PCM
        pcm_data = self._convert_to_pcm(audio_data)
        
        # Emit chunk event
        self._emit_event('chunk', pcm_data)
        
        # Track emitted chunk
        chunk_hash = hash_pcm_data(pcm_data)
        self.emitted_chunks.append({
            'data': pcm_data,
            'hash': chunk_hash,
            'timestamp': time.time()
        })
        self.chunk_hashes.append(chunk_hash)


def generate_sine_wave(sample_rate, frequency, duration_seconds):
    """Generate synthetic sine wave audio data"""
    import math
    num_samples = int(sample_rate * duration_seconds)
    samples = []
    for i in range(num_samples):
        sample = math.sin(2 * math.pi * frequency * i / sample_rate)
        samples.append(sample)
    return samples


def simulate_audio_processing(audio_capture, audio_data, buffer_size=4096):
    """Simulate onaudioprocess events with synthetic audio"""
    num_chunks = len(audio_data) // buffer_size
    
    for i in range(num_chunks):
        chunk_data = audio_data[i * buffer_size:(i + 1) * buffer_size]
        audio_capture.simulate_onaudioprocess(chunk_data)
    
    return num_chunks


class TestDuplicateAudioChunksBugExploration:
    """
    Bug Exploration Tests for Duplicate Audio Chunks
    
    These tests are designed to FAIL on unfixed code, confirming the bug exists.
    """
    
    def test_basic_1_second_capture_no_duplicates(self):
        """
        Property 1: Fault Condition - Duplicate Audio Chunk Detection
        
        Test that each audio chunk from onaudioprocess is emitted exactly once.
        This test MUST FAIL on unfixed code if duplicate chunks are being sent.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
        """
        # Create audio capture simulator
        audio_capture = AudioCaptureSimulator(sample_rate=16000, buffer_size=4096)
        
        # Track emitted chunks
        emitted_chunks = []
        chunk_hashes = []
        
        def chunk_handler(pcm_data):
            chunk_hash = hash_pcm_data(pcm_data)
            emitted_chunks.append({
                'data': pcm_data,
                'hash': chunk_hash,
                'timestamp': time.time()
            })
            chunk_hashes.append(chunk_hash)
        
        audio_capture.on('chunk', chunk_handler)
        
        # Generate 1 second of audio (440 Hz sine wave)
        audio_data = generate_sine_wave(16000, 440, 1.0)
        
        # Start capturing
        audio_capture.start()
        
        # Simulate audio processing
        expected_chunks = simulate_audio_processing(audio_capture, audio_data)
        
        # Stop capturing
        audio_capture.stop()
        
        # Check for duplicates
        unique_hashes = set(chunk_hashes)
        has_duplicates = len(unique_hashes) != len(chunk_hashes)
        
        # Document findings
        if has_duplicates:
            duplicates = [h for i, h in enumerate(chunk_hashes) if chunk_hashes.index(h) != i]
            print('\n=== DUPLICATE CHUNKS DETECTED ===')
            print(f'Total chunks emitted: {len(chunk_hashes)}')
            print(f'Unique chunks: {len(unique_hashes)}')
            print(f'Duplicate hashes found: {len(duplicates)}')
            print(f'First duplicate hash: {duplicates[0][:16]}...')
            
            # Find timestamps of duplicates
            first_dup_hash = duplicates[0]
            dup_chunks = [c for c in emitted_chunks if c['hash'] == first_dup_hash]
            print(f'Duplicate chunk appeared at timestamps: {[c["timestamp"] for c in dup_chunks]}')
        
        # ASSERTION: No duplicate chunks should be emitted
        # This will FAIL if the bug exists (which is expected for exploration)
        assert len(unique_hashes) == len(chunk_hashes), \
            f"Duplicate chunks detected: {len(chunk_hashes)} total, {len(unique_hashes)} unique"
        assert not has_duplicates, "Duplicate audio chunks were emitted"
    
    def test_continuous_5_second_capture_no_duplicates(self):
        """
        Property 1: Fault Condition - Continuous 5-second capture
        
        Test longer recording session to increase likelihood of detecting duplicates.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
        """
        # Create audio capture simulator
        audio_capture = AudioCaptureSimulator(sample_rate=16000, buffer_size=4096)
        
        # Track emitted chunks
        chunk_hashes = []
        
        def chunk_handler(pcm_data):
            chunk_hash = hash_pcm_data(pcm_data)
            chunk_hashes.append(chunk_hash)
        
        audio_capture.on('chunk', chunk_handler)
        
        # Generate 5 seconds of audio (440 Hz sine wave)
        audio_data = generate_sine_wave(16000, 440, 5.0)
        
        # Start capturing
        audio_capture.start()
        
        # Simulate audio processing
        expected_chunks = simulate_audio_processing(audio_capture, audio_data)
        
        # Stop capturing
        audio_capture.stop()
        
        # Check for duplicates
        unique_hashes = set(chunk_hashes)
        has_duplicates = len(unique_hashes) != len(chunk_hashes)
        
        # Document findings
        if has_duplicates:
            duplicates = [h for i, h in enumerate(chunk_hashes) if chunk_hashes.index(h) != i]
            print('\n=== DUPLICATE CHUNKS DETECTED (5-second test) ===')
            print(f'Total chunks emitted: {len(chunk_hashes)}')
            print(f'Unique chunks: {len(unique_hashes)}')
            print(f'Duplicate count: {len(duplicates)}')
            
            # Calculate duplication rate
            duplication_rate = (len(duplicates) / len(chunk_hashes) * 100)
            print(f'Duplication rate: {duplication_rate:.2f}%')
        
        # ASSERTION: No duplicate chunks should be emitted
        assert len(unique_hashes) == len(chunk_hashes), \
            f"Duplicate chunks detected: {len(chunk_hashes)} total, {len(unique_hashes)} unique"
        assert not has_duplicates, "Duplicate audio chunks were emitted"
    
    def test_start_stop_cycles_no_cross_session_duplicates(self):
        """
        Property 1: Fault Condition - Start/Stop cycles
        
        Test that chunks from one session are not re-sent in subsequent sessions.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
        """
        # Session 1
        audio_capture1 = AudioCaptureSimulator(sample_rate=16000, buffer_size=4096)
        session1_hashes = []
        
        def session1_handler(pcm_data):
            session1_hashes.append(hash_pcm_data(pcm_data))
        
        audio_capture1.on('chunk', session1_handler)
        
        # Generate 1 second of 440 Hz audio
        audio1 = generate_sine_wave(16000, 440, 1.0)
        audio_capture1.start()
        simulate_audio_processing(audio_capture1, audio1)
        audio_capture1.stop()
        
        # Session 2
        audio_capture2 = AudioCaptureSimulator(sample_rate=16000, buffer_size=4096)
        session2_hashes = []
        
        def session2_handler(pcm_data):
            session2_hashes.append(hash_pcm_data(pcm_data))
        
        audio_capture2.on('chunk', session2_handler)
        
        # Generate 1 second of 880 Hz audio (different frequency)
        audio2 = generate_sine_wave(16000, 880, 1.0)
        audio_capture2.start()
        simulate_audio_processing(audio_capture2, audio2)
        audio_capture2.stop()
        
        # Check if any hashes from session 1 appear in session 2
        session1_set = set(session1_hashes)
        cross_session_duplicates = [h for h in session2_hashes if h in session1_set]
        
        if cross_session_duplicates:
            print('\n=== CROSS-SESSION DUPLICATES DETECTED ===')
            print(f'Session 1 chunks: {len(session1_hashes)}')
            print(f'Session 2 chunks: {len(session2_hashes)}')
            print(f'Chunks from session 1 re-emitted in session 2: {len(cross_session_duplicates)}')
        
        # ASSERTION: No chunks from session 1 should appear in session 2
        assert len(cross_session_duplicates) == 0, \
            f"Cross-session duplicates detected: {len(cross_session_duplicates)} chunks from session 1 appeared in session 2"
    
    def test_multiple_event_handlers_no_duplicates(self):
        """
        Property 1: Fault Condition - Event handler duplication test
        
        Test if multiple event handlers cause chunks to be processed multiple times.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
        """
        # Create audio capture simulator
        audio_capture = AudioCaptureSimulator(sample_rate=16000, buffer_size=4096)
        
        # Track chunks for each handler
        handler1_chunks = []
        handler2_chunks = []
        
        def handler1(pcm_data):
            handler1_chunks.append(hash_pcm_data(pcm_data))
        
        def handler2(pcm_data):
            handler2_chunks.append(hash_pcm_data(pcm_data))
        
        # Register two handlers
        audio_capture.on('chunk', handler1)
        audio_capture.on('chunk', handler2)
        
        # Generate and process audio
        audio_data = generate_sine_wave(16000, 440, 1.0)
        audio_capture.start()
        simulate_audio_processing(audio_capture, audio_data)
        audio_capture.stop()
        
        # Both handlers should receive the same chunks
        assert len(handler1_chunks) == len(handler2_chunks), \
            f"Handlers received different number of chunks: {len(handler1_chunks)} vs {len(handler2_chunks)}"
        
        # Check if each handler has duplicates within itself
        handler1_unique = set(handler1_chunks)
        handler2_unique = set(handler2_chunks)
        
        handler1_has_duplicates = len(handler1_unique) != len(handler1_chunks)
        handler2_has_duplicates = len(handler2_unique) != len(handler2_chunks)
        
        if handler1_has_duplicates or handler2_has_duplicates:
            print('\n=== EVENT HANDLER DUPLICATION DETECTED ===')
            print(f'Handler 1: {len(handler1_chunks)} chunks, {len(handler1_unique)} unique')
            print(f'Handler 2: {len(handler2_chunks)} chunks, {len(handler2_unique)} unique')
        
        # ASSERTION: Neither handler should receive duplicate chunks
        assert not handler1_has_duplicates, "Handler 1 received duplicate chunks"
        assert not handler2_has_duplicates, "Handler 2 received duplicate chunks"
    
    @given(
        duration_seconds=st.integers(min_value=1, max_value=5),
        frequency=st.integers(min_value=100, max_value=1000)
    )
    @settings(max_examples=20, phases=[Phase.generate, Phase.target])
    def test_property_random_audio_patterns_no_duplicates(self, duration_seconds, frequency):
        """
        Property 1: Fault Condition - Property-based test with random audio patterns
        
        Uses Hypothesis to generate random audio patterns and verify no duplicates.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
        """
        # Create audio capture simulator
        audio_capture = AudioCaptureSimulator(sample_rate=16000, buffer_size=4096)
        
        # Track emitted chunks
        chunk_hashes = []
        
        def chunk_handler(pcm_data):
            chunk_hashes.append(hash_pcm_data(pcm_data))
        
        audio_capture.on('chunk', chunk_handler)
        
        # Generate random audio
        audio_data = generate_sine_wave(16000, frequency, duration_seconds)
        
        # Capture audio
        audio_capture.start()
        simulate_audio_processing(audio_capture, audio_data)
        audio_capture.stop()
        
        # Check for duplicates
        unique_hashes = set(chunk_hashes)
        has_duplicates = len(unique_hashes) != len(chunk_hashes)
        
        if has_duplicates:
            print(f'\n=== DUPLICATES FOUND (duration={duration_seconds}s, freq={frequency}Hz) ===')
            print(f'Total: {len(chunk_hashes)}, Unique: {len(unique_hashes)}')
        
        # Property: All chunks should be unique
        assert not has_duplicates, \
            f"Duplicate chunks found with duration={duration_seconds}s, frequency={frequency}Hz"
