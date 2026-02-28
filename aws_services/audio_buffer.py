"""
Audio Buffer for Streaming Transcription

Accumulates audio chunks in memory during streaming, then converts to MP3 for storage.
"""

import io
from typing import List
from pydub import AudioSegment
from utils.logger import get_logger

logger = get_logger(__name__)


class AudioBuffer:
    """
    In-memory buffer for accumulating audio chunks during streaming
    
    Features:
    - Accumulates PCM audio chunks in order
    - Enforces maximum duration limit (30 minutes)
    - Converts PCM to MP3 on finalization
    - Calculates total audio duration
    """
    
    def __init__(self, sample_rate: int = 16000, max_duration_seconds: int = 1800):
        """
        Initialize AudioBuffer
        
        Args:
            sample_rate: Audio sample rate in Hz (8000, 16000, or 48000)
            max_duration_seconds: Maximum duration in seconds (default: 1800 = 30 minutes)
        """
        self._chunks: List[bytes] = []
        self._sample_rate = sample_rate
        self._max_duration_seconds = max_duration_seconds
        self._max_size_bytes = self._calculate_max_size(max_duration_seconds, sample_rate)
        self._total_bytes = 0
        
        logger.debug(f"AudioBuffer initialized: sample_rate={sample_rate}Hz, "
                    f"max_duration={max_duration_seconds}s, max_size={self._max_size_bytes} bytes")
    
    def _calculate_max_size(self, duration_seconds: int, sample_rate: int) -> int:
        """
        Calculate maximum buffer size in bytes
        
        PCM format: 16-bit (2 bytes) per sample, mono channel
        Size = duration * sample_rate * 2 bytes
        
        Args:
            duration_seconds: Maximum duration in seconds
            sample_rate: Sample rate in Hz
            
        Returns:
            Maximum size in bytes
        """
        return duration_seconds * sample_rate * 2  # 2 bytes per sample (16-bit)
    
    def append(self, chunk: bytes) -> None:
        """
        Append audio chunk to buffer
        
        Args:
            chunk: PCM audio data (16-bit signed integers, little-endian)
            
        Raises:
            RuntimeError: If adding chunk would exceed maximum size
        """
        chunk_size = len(chunk)
        
        if self._total_bytes + chunk_size > self._max_size_bytes:
            duration = self.get_total_duration()
            raise RuntimeError(
                f"Buffer overflow: Maximum recording duration reached "
                f"({self._max_duration_seconds}s / {duration:.1f}s recorded)"
            )
        
        self._chunks.append(chunk)
        self._total_bytes += chunk_size
        
        logger.debug(f"Audio chunk appended: {chunk_size} bytes "
                    f"(total={self._total_bytes} bytes, duration={self.get_total_duration():.1f}s)")
    
    def get_total_duration(self) -> float:
        """
        Calculate total duration of buffered audio
        
        Returns:
            Duration in seconds
        """
        if self._total_bytes == 0:
            return 0.0
        
        # PCM: 2 bytes per sample (16-bit)
        total_samples = self._total_bytes / 2
        duration = total_samples / self._sample_rate
        
        return duration
    
    def get_total_bytes(self) -> int:
        """
        Get total bytes buffered
        
        Returns:
            Total bytes
        """
        return self._total_bytes
    
    def get_chunk_count(self) -> int:
        """
        Get number of chunks buffered
        
        Returns:
            Chunk count
        """
        return len(self._chunks)
    
    def finalize_to_mp3(self, bitrate: int = 64) -> bytes:
        """
        Convert accumulated PCM audio to MP3 format
        
        Args:
            bitrate: MP3 bitrate in kbps (default: 64)
            
        Returns:
            MP3 audio data as bytes
            
        Raises:
            RuntimeError: If buffer is empty or conversion fails
        """
        if not self._chunks:
            raise RuntimeError("Cannot finalize empty buffer")
        
        try:
            # Combine all chunks into single PCM data
            pcm_data = b''.join(self._chunks)
            
            logger.info(f"Converting PCM to MP3: {len(pcm_data)} bytes, "
                       f"{self.get_total_duration():.1f}s, {self._sample_rate}Hz")
            
            # Create AudioSegment from raw PCM data
            audio = AudioSegment(
                data=pcm_data,
                sample_width=2,  # 16-bit = 2 bytes
                frame_rate=self._sample_rate,
                channels=1  # Mono
            )
            
            # Export as MP3
            mp3_buffer = io.BytesIO()
            audio.export(
                mp3_buffer,
                format='mp3',
                bitrate=f'{bitrate}k',
                parameters=['-ac', '1']  # Force mono
            )
            
            mp3_data = mp3_buffer.getvalue()
            
            logger.info(f"MP3 conversion complete: {len(mp3_data)} bytes "
                       f"(compression ratio: {len(pcm_data)/len(mp3_data):.1f}x)")
            
            return mp3_data
            
        except Exception as e:
            logger.error(f"Failed to convert PCM to MP3: {str(e)}")
            raise RuntimeError(f"Audio conversion failed: {str(e)}")
    
    def clear(self) -> None:
        """Clear buffer and free memory"""
        chunk_count = len(self._chunks)
        total_bytes = self._total_bytes
        
        self._chunks.clear()
        self._total_bytes = 0
        
        logger.debug(f"Buffer cleared: {chunk_count} chunks, {total_bytes} bytes freed")
    
    def __len__(self) -> int:
        """Return number of chunks in buffer"""
        return len(self._chunks)
    
    def __repr__(self) -> str:
        """String representation"""
        return (f"AudioBuffer(chunks={len(self._chunks)}, "
                f"bytes={self._total_bytes}, "
                f"duration={self.get_total_duration():.1f}s, "
                f"sample_rate={self._sample_rate}Hz)")
