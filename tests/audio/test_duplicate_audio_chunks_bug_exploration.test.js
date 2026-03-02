/**
 * Bug Condition Exploration Test - Duplicate Audio Chunks
 * 
 * **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
 * **DO NOT attempt to fix the test or the code when it fails**
 * 
 * **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
 * 
 * This test detects duplicate audio chunks being emitted by the AudioCapture class.
 * It uses content hashing (SHA-256) to identify duplicate PCM data chunks.
 * 
 * Expected Outcome: TEST FAILS (proves duplicate chunks exist in unfixed code)
 */

import { describe, test, expect, beforeEach, afterEach, jest } from '@jest/globals';
import fc from 'fast-check';
import crypto from 'crypto';

// Mock Web Audio API
class MockAudioContext {
    constructor(options = {}) {
        this.sampleRate = options.sampleRate || 16000;
        this.state = 'running';
        this.destination = {};
    }

    createMediaStreamSource(stream) {
        return {
            connect: jest.fn(),
            disconnect: jest.fn()
        };
    }

    createScriptProcessor(bufferSize, inputChannels, outputChannels) {
        return {
            bufferSize,
            onaudioprocess: null,
            connect: jest.fn(),
            disconnect: jest.fn()
        };
    }

    close() {
        this.state = 'closed';
        return Promise.resolve();
    }

    resume() {
        this.state = 'running';
        return Promise.resolve();
    }
}

class MockMediaStream {
    constructor() {
        this.tracks = [{ stop: jest.fn() }];
    }

    getTracks() {
        return this.tracks;
    }
}

// Setup global mocks
global.AudioContext = MockAudioContext;
global.window = {
    AudioContext: MockAudioContext,
    isSecureContext: true
};
global.navigator = {
    mediaDevices: {
        getUserMedia: jest.fn().mockResolvedValue(new MockMediaStream())
    }
};
global.document = {
    addEventListener: jest.fn()
};

// Import AudioCapture after mocks are set up
const AudioCapture = (await import('../../static/js/audio-capture.js')).default;

/**
 * Hash PCM data to detect duplicates
 */
function hashPCMData(pcmData) {
    const buffer = Buffer.from(pcmData.buffer);
    return crypto.createHash('sha256').update(buffer).digest('hex');
}

/**
 * Generate synthetic audio data (sine wave)
 */
function generateSineWave(sampleRate, frequency, durationSeconds) {
    const numSamples = Math.floor(sampleRate * durationSeconds);
    const samples = new Float32Array(numSamples);
    
    for (let i = 0; i < numSamples; i++) {
        samples[i] = Math.sin(2 * Math.PI * frequency * i / sampleRate);
    }
    
    return samples;
}

/**
 * Simulate onaudioprocess events with synthetic audio
 */
function simulateAudioProcessing(audioCapture, audioData, bufferSize = 4096) {
    const chunks = [];
    const numChunks = Math.floor(audioData.length / bufferSize);
    
    for (let i = 0; i < numChunks; i++) {
        const chunkData = audioData.slice(i * bufferSize, (i + 1) * bufferSize);
        
        // Create mock audio processing event
        const event = {
            inputBuffer: {
                getChannelData: (channel) => chunkData
            }
        };
        
        // Trigger the onaudioprocess callback
        if (audioCapture.processorNode && audioCapture.processorNode.onaudioprocess) {
            audioCapture.processorNode.onaudioprocess(event);
        }
    }
    
    return numChunks;
}

describe('Bug Exploration: Duplicate Audio Chunks', () => {
    let audioCapture;
    let emittedChunks;
    let chunkHashes;

    beforeEach(async () => {
        // Reset mocks
        jest.clearAllMocks();
        
        // Create AudioCapture instance
        audioCapture = new AudioCapture(16000, 250);
        
        // Track emitted chunks
        emittedChunks = [];
        chunkHashes = [];
        
        // Register chunk event handler
        audioCapture.on('chunk', (pcmData) => {
            const hash = hashPCMData(pcmData);
            emittedChunks.push({
                data: pcmData,
                hash: hash,
                timestamp: Date.now()
            });
            chunkHashes.push(hash);
        });
        
        // Initialize audio capture
        await audioCapture.initialize();
    });

    afterEach(() => {
        if (audioCapture && audioCapture.isActive()) {
            audioCapture.stop();
        }
    });

    /**
     * Property 1: Fault Condition - Duplicate Audio Chunk Detection
     * 
     * Test that each audio chunk from onaudioprocess is emitted exactly once.
     * This test MUST FAIL on unfixed code if duplicate chunks are being sent.
     */
    test('EXPLORATION: Basic 1-second capture should not emit duplicate chunks', () => {
        // Generate 1 second of audio (440 Hz sine wave)
        const audioData = generateSineWave(16000, 440, 1.0);
        
        // Start capturing
        audioCapture.start();
        
        // Simulate audio processing
        const expectedChunks = simulateAudioProcessing(audioCapture, audioData);
        
        // Stop capturing
        audioCapture.stop();
        
        // Check for duplicates
        const uniqueHashes = new Set(chunkHashes);
        const hasDuplicates = uniqueHashes.size !== chunkHashes.length;
        
        // Document findings
        if (hasDuplicates) {
            const duplicates = chunkHashes.filter((hash, index) => 
                chunkHashes.indexOf(hash) !== index
            );
            console.log('\n=== DUPLICATE CHUNKS DETECTED ===');
            console.log(`Total chunks emitted: ${chunkHashes.length}`);
            console.log(`Unique chunks: ${uniqueHashes.size}`);
            console.log(`Duplicate hashes found: ${duplicates.length}`);
            console.log(`First duplicate hash: ${duplicates[0]}`);
            
            // Find timestamps of duplicates
            const firstDupHash = duplicates[0];
            const dupChunks = emittedChunks.filter(c => c.hash === firstDupHash);
            console.log(`Duplicate chunk appeared at timestamps:`, 
                dupChunks.map(c => c.timestamp));
        }
        
        // ASSERTION: No duplicate chunks should be emitted
        // This will FAIL if the bug exists (which is expected for exploration)
        expect(uniqueHashes.size).toBe(chunkHashes.length);
        expect(hasDuplicates).toBe(false);
    });

    /**
     * Property 1: Fault Condition - Continuous 5-second capture
     * 
     * Test longer recording session to increase likelihood of detecting duplicates
     */
    test('EXPLORATION: Continuous 5-second capture should not emit duplicate chunks', () => {
        // Generate 5 seconds of audio (440 Hz sine wave)
        const audioData = generateSineWave(16000, 440, 5.0);
        
        // Start capturing
        audioCapture.start();
        
        // Simulate audio processing
        const expectedChunks = simulateAudioProcessing(audioCapture, audioData);
        
        // Stop capturing
        audioCapture.stop();
        
        // Check for duplicates
        const uniqueHashes = new Set(chunkHashes);
        const hasDuplicates = uniqueHashes.size !== chunkHashes.length;
        
        // Document findings
        if (hasDuplicates) {
            const duplicates = chunkHashes.filter((hash, index) => 
                chunkHashes.indexOf(hash) !== index
            );
            console.log('\n=== DUPLICATE CHUNKS DETECTED (5-second test) ===');
            console.log(`Total chunks emitted: ${chunkHashes.length}`);
            console.log(`Unique chunks: ${uniqueHashes.size}`);
            console.log(`Duplicate count: ${duplicates.length}`);
            
            // Calculate duplication rate
            const duplicationRate = (duplicates.length / chunkHashes.length * 100).toFixed(2);
            console.log(`Duplication rate: ${duplicationRate}%`);
        }
        
        // ASSERTION: No duplicate chunks should be emitted
        expect(uniqueHashes.size).toBe(chunkHashes.length);
        expect(hasDuplicates).toBe(false);
    });

    /**
     * Property 1: Fault Condition - Start/Stop cycles
     * 
     * Test that chunks from one session are not re-sent in subsequent sessions
     */
    test('EXPLORATION: Start/Stop cycles should not re-emit chunks from previous sessions', () => {
        const allSessionHashes = [];
        
        // Session 1: 1 second of 440 Hz
        const audio1 = generateSineWave(16000, 440, 1.0);
        audioCapture.start();
        simulateAudioProcessing(audioCapture, audio1);
        audioCapture.stop();
        
        const session1Hashes = [...chunkHashes];
        allSessionHashes.push(...session1Hashes);
        
        // Reset tracking for session 2
        emittedChunks = [];
        chunkHashes.length = 0;
        
        // Re-initialize for session 2
        audioCapture = new AudioCapture(16000, 250);
        audioCapture.on('chunk', (pcmData) => {
            const hash = hashPCMData(pcmData);
            emittedChunks.push({ data: pcmData, hash: hash, timestamp: Date.now() });
            chunkHashes.push(hash);
        });
        
        // Session 2: 1 second of 880 Hz (different audio)
        const audio2 = generateSineWave(16000, 880, 1.0);
        audioCapture.initialize().then(() => {
            audioCapture.start();
            simulateAudioProcessing(audioCapture, audio2);
            audioCapture.stop();
        });
        
        const session2Hashes = [...chunkHashes];
        allSessionHashes.push(...session2Hashes);
        
        // Check if any hashes from session 1 appear in session 2
        const session1Set = new Set(session1Hashes);
        const crossSessionDuplicates = session2Hashes.filter(hash => session1Set.has(hash));
        
        if (crossSessionDuplicates.length > 0) {
            console.log('\n=== CROSS-SESSION DUPLICATES DETECTED ===');
            console.log(`Session 1 chunks: ${session1Hashes.length}`);
            console.log(`Session 2 chunks: ${session2Hashes.length}`);
            console.log(`Chunks from session 1 re-emitted in session 2: ${crossSessionDuplicates.length}`);
        }
        
        // ASSERTION: No chunks from session 1 should appear in session 2
        expect(crossSessionDuplicates.length).toBe(0);
    });

    /**
     * Property 1: Fault Condition - Property-based test with random audio patterns
     * 
     * Uses fast-check to generate random audio patterns and verify no duplicates
     */
    test('EXPLORATION: Property-based test - random audio patterns should not produce duplicates', () => {
        fc.assert(
            fc.property(
                fc.integer({ min: 1, max: 5 }), // duration in seconds
                fc.integer({ min: 100, max: 1000 }), // frequency in Hz
                (durationSeconds, frequency) => {
                    // Reset tracking
                    emittedChunks = [];
                    chunkHashes.length = 0;
                    
                    // Generate random audio
                    const audioData = generateSineWave(16000, frequency, durationSeconds);
                    
                    // Capture audio
                    audioCapture.start();
                    simulateAudioProcessing(audioCapture, audioData);
                    audioCapture.stop();
                    
                    // Check for duplicates
                    const uniqueHashes = new Set(chunkHashes);
                    const hasDuplicates = uniqueHashes.size !== chunkHashes.length;
                    
                    if (hasDuplicates) {
                        console.log(`\n=== DUPLICATES FOUND (duration=${durationSeconds}s, freq=${frequency}Hz) ===`);
                        console.log(`Total: ${chunkHashes.length}, Unique: ${uniqueHashes.size}`);
                    }
                    
                    // Property: All chunks should be unique
                    return !hasDuplicates;
                }
            ),
            { numRuns: 20, verbose: true }
        );
    });

    /**
     * Property 1: Fault Condition - Event handler duplication test
     * 
     * Test if multiple event handlers cause chunks to be processed multiple times
     */
    test('EXPLORATION: Multiple event handlers should each receive chunks exactly once', () => {
        const handler1Chunks = [];
        const handler2Chunks = [];
        
        // Register two handlers
        audioCapture.on('chunk', (pcmData) => {
            handler1Chunks.push(hashPCMData(pcmData));
        });
        
        audioCapture.on('chunk', (pcmData) => {
            handler2Chunks.push(hashPCMData(pcmData));
        });
        
        // Generate and process audio
        const audioData = generateSineWave(16000, 440, 1.0);
        audioCapture.start();
        simulateAudioProcessing(audioCapture, audioData);
        audioCapture.stop();
        
        // Both handlers should receive the same chunks
        expect(handler1Chunks.length).toBe(handler2Chunks.length);
        
        // Check if each handler has duplicates within itself
        const handler1Unique = new Set(handler1Chunks);
        const handler2Unique = new Set(handler2Chunks);
        
        const handler1HasDuplicates = handler1Unique.size !== handler1Chunks.length;
        const handler2HasDuplicates = handler2Unique.size !== handler2Chunks.length;
        
        if (handler1HasDuplicates || handler2HasDuplicates) {
            console.log('\n=== EVENT HANDLER DUPLICATION DETECTED ===');
            console.log(`Handler 1: ${handler1Chunks.length} chunks, ${handler1Unique.size} unique`);
            console.log(`Handler 2: ${handler2Chunks.length} chunks, ${handler2Unique.size} unique`);
        }
        
        // ASSERTION: Neither handler should receive duplicate chunks
        expect(handler1HasDuplicates).toBe(false);
        expect(handler2HasDuplicates).toBe(false);
    });
});
