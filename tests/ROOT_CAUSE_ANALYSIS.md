# Root Cause Analysis: Duplicate Audio Chunks

## Summary

**Bug Location**: `static/js/websocket-client.js` - `sendAudioChunk()` and `_flushBuffer()` methods

**Root Cause**: Recursive infinite loop causing each audio chunk to be sent multiple times

## The Bug

In `websocket-client.js`, the `sendAudioChunk()` method has this code:

```javascript
sendAudioChunk(audioData) {
    // ... send the chunk ...
    this.socket.emit('audio_chunk', chunkData);

    // Send any buffered audio
    if (this.audioBuffer.length > 0) {
        this._flushBuffer();  // <-- PROBLEM: Calls _flushBuffer
    }
}
```

And `_flushBuffer()` does this:

```javascript
_flushBuffer() {
    console.log(`Flushing ${this.audioBuffer.length} buffered chunks`);
    
    while (this.audioBuffer.length > 0) {
        const chunk = this.audioBuffer.shift();
        this.sendAudioChunk(chunk);  // <-- PROBLEM: Calls sendAudioChunk again!
    }
}
```

## The Problem

1. `sendAudioChunk(chunk1)` is called with a new audio chunk
2. It sends `chunk1` via WebSocket
3. It checks if there are buffered chunks
4. If yes, it calls `_flushBuffer()`
5. `_flushBuffer()` calls `sendAudioChunk(bufferedChunk)`
6. `sendAudioChunk(bufferedChunk)` sends the buffered chunk
7. **BUG**: It checks if there are MORE buffered chunks and calls `_flushBuffer()` AGAIN
8. This creates a recursive loop where chunks get re-sent multiple times

## Why This Happens

The buffering logic was designed for handling temporary disconnections:
- When disconnected, chunks are buffered in `this.audioBuffer`
- When reconnected, buffered chunks should be flushed

However, the implementation has a flaw:
- `sendAudioChunk()` always checks for buffered chunks after sending
- `_flushBuffer()` calls `sendAudioChunk()` for each buffered chunk
- This creates recursion: send → flush → send → flush → ...

## The Fix

The fix is simple: **Don't check for buffered chunks when flushing**

We need to add a parameter to `sendAudioChunk()` to indicate whether it's being called from `_flushBuffer()`:

```javascript
sendAudioChunk(audioData, isFlushingBuffer = false) {
    // ... send the chunk ...
    this.socket.emit('audio_chunk', chunkData);

    // Only flush buffer if NOT already flushing
    if (!isFlushingBuffer && this.audioBuffer.length > 0) {
        this._flushBuffer();
    }
}
```

And update `_flushBuffer()`:

```javascript
_flushBuffer() {
    console.log(`Flushing ${this.audioBuffer.length} buffered chunks`);
    
    while (this.audioBuffer.length > 0) {
        const chunk = this.audioBuffer.shift();
        this.sendAudioChunk(chunk, true);  // Pass true to prevent recursion
    }
}
```

## Impact

This bug causes:
- Each audio chunk to be sent multiple times to AWS Transcribe
- Duplicate transcription output
- Increased network bandwidth usage
- Increased AWS Transcribe costs
- Confusing transcription results with repeated phrases

## Verification

After the fix:
- Each chunk should be sent exactly once
- No recursive calls to `_flushBuffer()`
- Buffered chunks (from disconnections) should still be flushed correctly
- No duplicate transcription output
