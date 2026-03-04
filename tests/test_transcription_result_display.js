/**
 * Unit tests for TranscriptionResultDisplay component
 * 
 * Tests basic functionality:
 * - Adding clips in order
 * - Updating clip status
 * - Displaying partial and complete results
 * - Persisting to storage
 */

// Mock DOM environment for testing
class MockElement {
    constructor(tagName) {
        this.tagName = tagName;
        this.children = [];
        this.className = '';
        this.textContent = '';
        this.dataset = {};
        this.parentNode = null;
        this.innerHTML = '';
    }
    
    appendChild(child) {
        this.children.push(child);
        child.parentNode = this;
        return child;
    }
    
    insertBefore(newChild, refChild) {
        const index = this.children.indexOf(refChild);
        if (index >= 0) {
            this.children.splice(index, 0, newChild);
        } else {
            this.children.push(newChild);
        }
        newChild.parentNode = this;
        return newChild;
    }
    
    removeChild(child) {
        const index = this.children.indexOf(child);
        if (index >= 0) {
            this.children.splice(index, 1);
            child.parentNode = null;
        }
        return child;
    }
}

// Mock document
const mockDocument = {
    createElement: (tagName) => new MockElement(tagName),
    createTextNode: (text) => ({ textContent: text }),
    getElementById: () => null,
    head: new MockElement('head'),
    readyState: 'complete'
};

// Mock localStorage
const mockLocalStorage = {
    data: {},
    getItem(key) {
        return this.data[key] || null;
    },
    setItem(key, value) {
        this.data[key] = value;
    },
    removeItem(key) {
        delete this.data[key];
    },
    clear() {
        this.data = {};
    }
};

// Set up global mocks
global.document = mockDocument;
global.localStorage = mockLocalStorage;

// Load the component
const TranscriptionResultDisplay = require('../static/js/transcription-result-display.js');

// Test suite
describe('TranscriptionResultDisplay', () => {
    let container;
    let display;
    
    beforeEach(() => {
        // Reset mocks
        mockLocalStorage.clear();
        
        // Create container
        container = new MockElement('div');
        
        // Create display instance
        display = new TranscriptionResultDisplay(container, {
            animateText: false, // Disable animation for testing
            persistToStorage: false // Disable storage for most tests
        });
    });
    
    afterEach(() => {
        if (display) {
            display.clear();
        }
    });
    
    test('should create clip in correct order', () => {
        // Add clips out of order
        display.addOrUpdateClip({
            clipId: 'clip_2',
            clipOrder: 2,
            text: 'Second clip',
            status: 'completed'
        });
        
        display.addOrUpdateClip({
            clipId: 'clip_1',
            clipOrder: 1,
            text: 'First clip',
            status: 'completed'
        });
        
        display.addOrUpdateClip({
            clipId: 'clip_3',
            clipOrder: 3,
            text: 'Third clip',
            status: 'completed'
        });
        
        // Verify order
        const clips = display.getClipsOrdered();
        expect(clips.length).toBe(3);
        expect(clips[0].clipId).toBe('clip_1');
        expect(clips[1].clipId).toBe('clip_2');
        expect(clips[2].clipId).toBe('clip_3');
    });
    
    test('should update existing clip', () => {
        // Add initial clip
        display.addOrUpdateClip({
            clipId: 'clip_1',
            clipOrder: 1,
            text: 'Initial text',
            status: 'transcribing',
            isPartial: true
        });
        
        // Update clip
        display.addOrUpdateClip({
            clipId: 'clip_1',
            clipOrder: 1,
            text: 'Initial text updated',
            status: 'completed',
            isComplete: true
        });
        
        // Verify update
        const clips = display.getClipsOrdered();
        expect(clips.length).toBe(1);
        expect(clips[0].text).toBe('Initial text updated');
        expect(clips[0].status).toBe('completed');
        expect(clips[0].isComplete).toBe(true);
    });
    
    test('should display partial results with processing indicator', () => {
        // Add partial result
        display.addOrUpdateClip({
            clipId: 'clip_1',
            clipOrder: 1,
            text: 'Partial transcription',
            status: 'transcribing',
            isPartial: true,
            isComplete: false
        });
        
        // Verify clip data
        const clip = display.clips.get('clip_1');
        expect(clip).toBeDefined();
        expect(clip.isPartial).toBe(true);
        expect(clip.isComplete).toBe(false);
        expect(clip.status).toBe('transcribing');
    });
    
    test('should show final complete transcription', () => {
        // Add complete result
        display.addOrUpdateClip({
            clipId: 'clip_1',
            clipOrder: 1,
            text: 'Complete transcription',
            status: 'completed',
            isPartial: false,
            isComplete: true
        });
        
        // Verify clip data
        const clip = display.clips.get('clip_1');
        expect(clip).toBeDefined();
        expect(clip.isPartial).toBe(false);
        expect(clip.isComplete).toBe(true);
        expect(clip.status).toBe('completed');
    });
    
    test('should get full transcription text in order', () => {
        // Add multiple clips
        display.addOrUpdateClip({
            clipId: 'clip_1',
            clipOrder: 1,
            text: 'First clip text.',
            status: 'completed'
        });
        
        display.addOrUpdateClip({
            clipId: 'clip_2',
            clipOrder: 2,
            text: 'Second clip text.',
            status: 'completed'
        });
        
        display.addOrUpdateClip({
            clipId: 'clip_3',
            clipOrder: 3,
            text: 'Third clip text.',
            status: 'completed'
        });
        
        // Get full transcription
        const fullText = display.getFullTranscription();
        expect(fullText).toBe('First clip text. Second clip text. Third clip text.');
    });
    
    test('should persist transcriptions to storage', () => {
        // Create display with storage enabled
        const displayWithStorage = new TranscriptionResultDisplay(container, {
            animateText: false,
            persistToStorage: true,
            consultationId: 'test_consultation_123'
        });
        
        // Add clips
        displayWithStorage.addOrUpdateClip({
            clipId: 'clip_1',
            clipOrder: 1,
            text: 'Persisted clip',
            status: 'completed'
        });
        
        // Verify storage
        const stored = mockLocalStorage.getItem('transcription_results_test_consultation_123');
        expect(stored).toBeDefined();
        
        const data = JSON.parse(stored);
        expect(data.consultationId).toBe('test_consultation_123');
        expect(data.clips.length).toBe(1);
        expect(data.clips[0].text).toBe('Persisted clip');
        
        displayWithStorage.clear();
    });
    
    test('should load transcriptions from storage', () => {
        // Prepare storage data
        const storageData = {
            consultationId: 'test_consultation_456',
            clips: [
                {
                    clipId: 'clip_1',
                    clipOrder: 1,
                    text: 'Loaded clip 1',
                    status: 'completed',
                    isPartial: false,
                    isComplete: true
                },
                {
                    clipId: 'clip_2',
                    clipOrder: 2,
                    text: 'Loaded clip 2',
                    status: 'completed',
                    isPartial: false,
                    isComplete: true
                }
            ],
            timestamp: Date.now()
        };
        
        mockLocalStorage.setItem(
            'transcription_results_test_consultation_456',
            JSON.stringify(storageData)
        );
        
        // Create display with storage enabled
        const displayWithStorage = new TranscriptionResultDisplay(container, {
            animateText: false,
            persistToStorage: true,
            consultationId: 'test_consultation_456'
        });
        
        // Verify clips were loaded
        const clips = displayWithStorage.getClipsOrdered();
        expect(clips.length).toBe(2);
        expect(clips[0].text).toBe('Loaded clip 1');
        expect(clips[1].text).toBe('Loaded clip 2');
        
        displayWithStorage.clear();
    });
    
    test('should remove clip', () => {
        // Add clips
        display.addOrUpdateClip({
            clipId: 'clip_1',
            clipOrder: 1,
            text: 'First clip',
            status: 'completed'
        });
        
        display.addOrUpdateClip({
            clipId: 'clip_2',
            clipOrder: 2,
            text: 'Second clip',
            status: 'completed'
        });
        
        // Remove clip
        display.removeClip('clip_1');
        
        // Verify removal
        const clips = display.getClipsOrdered();
        expect(clips.length).toBe(1);
        expect(clips[0].clipId).toBe('clip_2');
    });
    
    test('should clear all clips', () => {
        // Add clips
        display.addOrUpdateClip({
            clipId: 'clip_1',
            clipOrder: 1,
            text: 'First clip',
            status: 'completed'
        });
        
        display.addOrUpdateClip({
            clipId: 'clip_2',
            clipOrder: 2,
            text: 'Second clip',
            status: 'completed'
        });
        
        // Clear
        display.clear();
        
        // Verify cleared
        const clips = display.getClipsOrdered();
        expect(clips.length).toBe(0);
    });
});

// Simple test runner
function runTests() {
    console.log('Running TranscriptionResultDisplay tests...\n');
    
    const tests = [
        'should create clip in correct order',
        'should update existing clip',
        'should display partial results with processing indicator',
        'should show final complete transcription',
        'should get full transcription text in order',
        'should persist transcriptions to storage',
        'should load transcriptions from storage',
        'should remove clip',
        'should clear all clips'
    ];
    
    let passed = 0;
    let failed = 0;
    
    tests.forEach(testName => {
        try {
            // Find and run test
            const testFn = global.tests[testName];
            if (testFn) {
                testFn();
                console.log(`✓ ${testName}`);
                passed++;
            } else {
                console.log(`✗ ${testName} - Test not found`);
                failed++;
            }
        } catch (error) {
            console.log(`✗ ${testName}`);
            console.log(`  Error: ${error.message}`);
            failed++;
        }
    });
    
    console.log(`\nResults: ${passed} passed, ${failed} failed`);
    return failed === 0;
}

// Test helpers
global.tests = {};

function describe(name, fn) {
    fn();
}

function test(name, fn) {
    global.tests[name] = fn;
}

function beforeEach(fn) {
    // Store setup function
    global.beforeEachFn = fn;
}

function afterEach(fn) {
    // Store teardown function
    global.afterEachFn = fn;
}

function expect(actual) {
    return {
        toBe(expected) {
            if (actual !== expected) {
                throw new Error(`Expected ${actual} to be ${expected}`);
            }
        },
        toBeDefined() {
            if (actual === undefined) {
                throw new Error('Expected value to be defined');
            }
        }
    };
}

// Run tests if executed directly
if (require.main === module) {
    const success = runTests();
    process.exit(success ? 0 : 1);
}

module.exports = { runTests };
