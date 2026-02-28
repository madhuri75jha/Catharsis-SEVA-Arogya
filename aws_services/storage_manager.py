"""Storage Manager for AWS S3 Operations"""
import logging
import time
from datetime import datetime
from typing import Optional, BinaryIO
from botocore.exceptions import ClientError
from .base_client import BaseAWSClient

logger = logging.getLogger(__name__)


class StorageManager(BaseAWSClient):
    """Manages S3 storage operations for audio and PDF files"""
    
    # Supported audio formats
    SUPPORTED_AUDIO_FORMATS = ['wav', 'mp3', 'flac', 'mp4', 'm4a']
    
    # Maximum file size for audio uploads (16MB)
    MAX_AUDIO_SIZE_BYTES = 16 * 1024 * 1024
    
    def __init__(self, region: str, audio_bucket: str, pdf_bucket: str):
        """
        Initialize Storage Manager
        
        Args:
            region: AWS region
            audio_bucket: S3 bucket name for audio files
            pdf_bucket: S3 bucket name for PDF files
        """
        super().__init__('s3', region)
        self.audio_bucket = audio_bucket
        self.pdf_bucket = pdf_bucket
        logger.info(f"Storage manager initialized with audio_bucket={audio_bucket}, pdf_bucket={pdf_bucket}")
    
    def _validate_audio_file(self, filename: str, file_size: int) -> tuple[bool, Optional[str]]:
        """
        Validate audio file format and size
        
        Args:
            filename: Name of the file
            file_size: Size of the file in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file extension
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if file_ext not in self.SUPPORTED_AUDIO_FORMATS:
            return False, f"Unsupported file format. Supported formats: {', '.join(self.SUPPORTED_AUDIO_FORMATS)}"
        
        # Check file size
        if file_size > self.MAX_AUDIO_SIZE_BYTES:
            max_size_mb = self.MAX_AUDIO_SIZE_BYTES / (1024 * 1024)
            return False, f"File size exceeds maximum limit of {max_size_mb}MB"
        
        return True, None
    
    def upload_audio(self, file_data: BinaryIO, filename: str, user_id: str) -> Optional[str]:
        """
        Upload audio file to S3 with validation and encryption
        
        Args:
            file_data: File data stream
            filename: Original filename
            user_id: ID of the user uploading the file
            
        Returns:
            S3 object key if successful, None otherwise
        """
        start_time = time.time()
        
        try:
            # Read file data to check size
            file_content = file_data.read()
            file_size = len(file_content)
            
            # Validate file
            is_valid, error_msg = self._validate_audio_file(filename, file_size)
            if not is_valid:
                logger.warning(f"Audio file validation failed: {error_msg}")
                raise ValueError(error_msg)
            
            # Generate unique S3 key
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            file_ext = filename.split('.')[-1]
            s3_key = f"audio/{user_id}/{timestamp}_{filename}"
            
            self._log_operation('upload_audio', bucket=self.audio_bucket, key=s3_key)
            
            # Upload to S3 with server-side encryption
            self.client.put_object(
                Bucket=self.audio_bucket,
                Key=s3_key,
                Body=file_content,
                ServerSideEncryption='AES256',
                ContentType=f'audio/{file_ext}'
            )
            
            duration_ms = (time.time() - start_time) * 1000
            self._log_success('upload_audio', duration_ms=duration_ms, key=s3_key)
            
            return s3_key
            
        except ValueError as e:
            # Validation error - don't retry
            raise
        except ClientError as e:
            self._log_error('upload_audio', e)
            logger.error(f"Failed to upload audio file: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading audio file: {str(e)}")
            return None
    
    def upload_pdf(self, pdf_data: bytes, user_id: str, prescription_id: str) -> Optional[str]:
        """
        Upload prescription PDF to S3 with encryption
        
        Args:
            pdf_data: PDF file data as bytes
            user_id: ID of the user
            prescription_id: Prescription ID
            
        Returns:
            S3 object key if successful, None otherwise
        """
        start_time = time.time()
        
        try:
            # Generate structured S3 key
            s3_key = f"prescriptions/{user_id}/{prescription_id}.pdf"
            
            self._log_operation('upload_pdf', bucket=self.pdf_bucket, key=s3_key)
            
            # Upload to S3 with server-side encryption
            self.client.put_object(
                Bucket=self.pdf_bucket,
                Key=s3_key,
                Body=pdf_data,
                ServerSideEncryption='AES256',
                ContentType='application/pdf'
            )
            
            duration_ms = (time.time() - start_time) * 1000
            self._log_success('upload_pdf', duration_ms=duration_ms, key=s3_key)
            
            return s3_key
            
        except ClientError as e:
            self._log_error('upload_pdf', e)
            logger.error(f"Failed to upload PDF file: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading PDF file: {str(e)}")
            return None
    
    def generate_presigned_url(self, s3_key: str, bucket: Optional[str] = None, expiration: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for file download
        
        Args:
            s3_key: S3 object key
            bucket: S3 bucket name (defaults to pdf_bucket)
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL if successful, None otherwise
        """
        try:
            bucket_name = bucket or self.pdf_bucket
            
            self._log_operation('generate_presigned_url', bucket=bucket_name, key=s3_key)
            
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            
            self._log_success('generate_presigned_url', key=s3_key)
            
            return url
            
        except ClientError as e:
            self._log_error('generate_presigned_url', e)
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {str(e)}")
            return None
    
    def get_audio_uri(self, s3_key: str) -> str:
        """
        Get S3 URI for audio file (for Transcribe service)
        
        Args:
            s3_key: S3 object key
            
        Returns:
            S3 URI string
        """
        return f"s3://{self.audio_bucket}/{s3_key}"

    def upload_audio_bytes(self, audio_data: bytes, s3_key: str, content_type: str = 'audio/mpeg') -> bool:
        """
        Upload audio bytes directly to S3 (for streaming transcription)
        
        Args:
            audio_data: Audio file data as bytes
            s3_key: S3 object key (full path)
            content_type: MIME type (default: audio/mpeg for MP3)
            
        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                self._log_operation('upload_audio_bytes', bucket=self.audio_bucket, key=s3_key, attempt=attempt+1)
                
                # Upload to S3 with server-side encryption
                self.client.put_object(
                    Bucket=self.audio_bucket,
                    Key=s3_key,
                    Body=audio_data,
                    ServerSideEncryption='AES256',
                    ContentType=content_type
                )
                
                duration_ms = (time.time() - start_time) * 1000
                self._log_success('upload_audio_bytes', duration_ms=duration_ms, key=s3_key, size_bytes=len(audio_data))
                
                return True
                
            except ClientError as e:
                self._log_error('upload_audio_bytes', e, attempt=attempt+1)
                
                if attempt < max_retries:
                    # Exponential backoff: 2s, 4s
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(f"Upload failed, retrying in {wait_time}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to upload audio bytes after {max_retries+1} attempts: {str(e)}")
                    return False
                    
            except Exception as e:
                logger.error(f"Unexpected error uploading audio bytes: {str(e)}")
                return False
        
        return False
