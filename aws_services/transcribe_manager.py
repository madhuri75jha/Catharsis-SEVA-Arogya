"""Transcription Manager for AWS Transcribe Medical"""
import logging
import time
import uuid
import json
from typing import Optional, Dict, Any
from urllib.parse import urlparse, unquote
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import boto3
from botocore.exceptions import ClientError
from .base_client import BaseAWSClient

logger = logging.getLogger(__name__)


class TranscribeManager(BaseAWSClient):
    """Manages AWS Transcribe Medical operations for audio transcription"""
    
    def __init__(self, region: str):
        """
        Initialize Transcribe Manager
        
        Args:
            region: AWS region
        """
        super().__init__('transcribe', region)
        logger.info("Transcribe manager initialized")
    
    def start_transcription(self, audio_s3_uri: str, language_code: str = 'en-US', 
                          specialty: str = 'PRIMARYCARE', media_format: str = 'mp3') -> Optional[str]:
        """
        Start medical transcription job
        
        Args:
            audio_s3_uri: S3 URI of the audio file (s3://bucket/key)
            language_code: Language code (default: en-US)
            specialty: Medical specialty (PRIMARYCARE, CARDIOLOGY, NEUROLOGY, etc.)
            media_format: Audio format (mp3, mp4, wav, flac)
            
        Returns:
            Transcription job ID if successful, None otherwise
        """
        start_time = time.time()
        
        try:
            # Generate unique job name
            job_name = f"medical-transcription-{uuid.uuid4()}"
            
            self._log_operation('start_transcription', job_name=job_name, audio_uri=audio_s3_uri)
            
            # Start medical transcription job
            response = self.client.start_medical_transcription_job(
                MedicalTranscriptionJobName=job_name,
                LanguageCode=language_code,
                MediaFormat=media_format,
                Media={'MediaFileUri': audio_s3_uri},
                OutputBucketName=audio_s3_uri.split('/')[2],  # Extract bucket name from S3 URI
                Specialty=specialty,
                Type='DICTATION'
            )
            
            job_id = response['MedicalTranscriptionJob']['MedicalTranscriptionJobName']
            
            duration_ms = (time.time() - start_time) * 1000
            self._log_success('start_transcription', duration_ms=duration_ms, job_id=job_id)
            logger.info(f"Transcription job started: {job_id}")
            
            return job_id
            
        except ClientError as e:
            self._log_error('start_transcription', e)
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to start transcription job: {error_code}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error starting transcription job: {str(e)}")
            return None
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get transcription job status
        
        Args:
            job_id: Transcription job ID
            
        Returns:
            Dictionary with job status information or None
        """
        try:
            self._log_operation('get_job_status', job_id=job_id)
            
            response = self.client.get_medical_transcription_job(
                MedicalTranscriptionJobName=job_id
            )
            
            job = response['MedicalTranscriptionJob']
            status_info = {
                'job_id': job['MedicalTranscriptionJobName'],
                'status': job['TranscriptionJobStatus'],
                'creation_time': job.get('CreationTime'),
                'completion_time': job.get('CompletionTime'),
                'failure_reason': job.get('FailureReason')
            }
            
            if job['TranscriptionJobStatus'] == 'COMPLETED':
                status_info['transcript_uri'] = job.get('Transcript', {}).get('TranscriptFileUri')
            
            self._log_success('get_job_status', job_id=job_id, status=status_info['status'])
            
            return status_info
            
        except ClientError as e:
            self._log_error('get_job_status', e, job_id=job_id)
            error_code = e.response['Error']['Code']
            
            if error_code == 'BadRequestException':
                logger.warning(f"Transcription job not found: {job_id}")
            else:
                logger.error(f"Failed to get job status: {error_code}")
            
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting job status: {str(e)}")
            return None
    
    def get_transcript(self, job_id: str) -> Optional[str]:
        """
        Get completed transcript text
        
        Args:
            job_id: Transcription job ID
            
        Returns:
            Transcript text if successful, None otherwise
        """
        try:
            self._log_operation('get_transcript', job_id=job_id)
            
            # Get job status first
            status_info = self.get_job_status(job_id)
            
            if not status_info:
                logger.error(f"Failed to get job status for transcript retrieval: {job_id}")
                return None
            
            if status_info['status'] != 'COMPLETED':
                logger.warning(f"Transcription job not completed: {job_id} (status: {status_info['status']})")
                return None
            
            # Get transcript URI
            transcript_uri = status_info.get('transcript_uri')
            if not transcript_uri:
                logger.error(f"Transcript URI not found for job: {job_id}")
                return None
            
            transcript_data = self._download_transcript_json(transcript_uri)
            
            # Extract transcript text
            transcript_text = transcript_data.get('results', {}).get('transcripts', [{}])[0].get('transcript', '')
            
            if transcript_text:
                self._log_success('get_transcript', job_id=job_id)
                logger.info(f"Transcript retrieved successfully for job: {job_id}")
                return transcript_text
            else:
                logger.warning(f"Transcript text is empty for job: {job_id}")
                return None
            
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
            logger.error(f"Failed to download transcript from S3: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting transcript: {str(e)}")
            return None

    def _download_transcript_json(self, transcript_uri: str) -> Dict[str, Any]:
        """
        Download transcript JSON from transcript URI.

        Primary path uses direct URL fetch. For environments where the URL is not
        anonymously accessible (HTTP 403/404), fallback to AWS SDK S3 get_object
        using task role credentials.
        """
        try:
            with urlopen(transcript_uri, timeout=20) as response:
                body = response.read()
            return json.loads(body.decode('utf-8'))
        except HTTPError as e:
            if e.code not in (403, 404):
                raise
            bucket, key = self._extract_s3_bucket_key(transcript_uri)
            if not bucket or not key:
                raise
            s3_client = boto3.client('s3', region_name=self.region)
            obj = s3_client.get_object(Bucket=bucket, Key=key)
            body = obj['Body'].read()
            return json.loads(body.decode('utf-8'))

    @staticmethod
    def _extract_s3_bucket_key(uri: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extract (bucket, key) from s3:// or S3 https URL formats.
        """
        parsed = urlparse(uri)
        host = (parsed.netloc or '').lower()
        path = parsed.path or ''

        if parsed.scheme == 's3':
            bucket = parsed.netloc
            key = path.lstrip('/')
            return bucket or None, unquote(key) or None

        if parsed.scheme in ('http', 'https'):
            # Virtual-hosted style: bucket.s3.region.amazonaws.com/key
            if '.s3.' in host or host.endswith('.s3.amazonaws.com'):
                bucket = host.split('.s3')[0]
                key = path.lstrip('/')
                return bucket or None, unquote(key) or None

            # Path style: s3.region.amazonaws.com/bucket/key
            if host.startswith('s3.') or host == 's3.amazonaws.com':
                parts = path.lstrip('/').split('/', 1)
                if len(parts) == 2:
                    return parts[0], unquote(parts[1])

        return None, None
