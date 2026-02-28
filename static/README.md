# Static Assets

This directory contains frontend JavaScript files for the SEVA Arogya application.

## JavaScript Dependencies

### Socket.IO Client
The application uses Socket.IO for real-time WebSocket communication. The client library is loaded via CDN in HTML templates:

```html
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
```

**Version**: 4.7.2  
**Purpose**: Real-time bidirectional communication for audio streaming and transcription results  
**Documentation**: https://socket.io/docs/v4/client-api/

### Web Audio API
The application uses the browser's native Web Audio API for microphone access and audio processing. No external library is required.

**Browser Compatibility**:
- Chrome 25+
- Firefox 25+
- Safari 14.1+
- Edge 79+

## Directory Structure

```
static/
├── js/
│   ├── audio-capture.js          # Microphone audio capture and PCM encoding
│   ├── websocket-client.js       # Socket.IO WebSocket client wrapper
│   ├── transcription-display.js  # Real-time transcription UI rendering
│   └── transcription-controller.js # Main application controller
└── README.md
```

## Development

All JavaScript files use vanilla ES6+ JavaScript with no build step required. Files are loaded directly in HTML templates.
