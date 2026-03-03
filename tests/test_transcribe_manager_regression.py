"""Regression tests for TranscribeManager transcript retrieval error handling."""

from unittest.mock import Mock

import json
import urllib.error

from aws_services.transcribe_manager import TranscribeManager
import aws_services.transcribe_manager as transcribe_manager_module


def _make_manager():
    """Create a manager instance without calling BaseAWSClient init."""
    manager = object.__new__(TranscribeManager)
    manager._log_operation = Mock()
    manager._log_success = Mock()
    manager._log_error = Mock()
    manager.client = Mock()
    return manager


def test_get_transcript_handles_pre_requests_exception_without_unboundlocal():
    """
    Guard against UnboundLocalError from except requests.RequestException path.

    If get_job_status fails before any requests call, get_transcript should
    return None and not raise "cannot access local variable 'requests'".
    """
    manager = _make_manager()
    manager.get_job_status = Mock(side_effect=RuntimeError("status call failed"))

    result = manager.get_transcript("job-123")

    assert result is None


def test_get_transcript_handles_requests_exception():
    """If transcript download fails, method should safely return None."""
    manager = _make_manager()
    manager.get_job_status = Mock(
        return_value={
            "status": "COMPLETED",
            "transcript_uri": "https://example.invalid/transcript.json",
        }
    )

    original_urlopen = transcribe_manager_module.urlopen
    transcribe_manager_module.urlopen = Mock(
        side_effect=urllib.error.URLError("download failed")
    )
    try:
        result = manager.get_transcript("job-456")
        assert result is None
    finally:
        transcribe_manager_module.urlopen = original_urlopen


def test_get_transcript_parses_stdlib_response():
    """Ensure transcript retrieval works with urllib/json path."""
    manager = _make_manager()
    manager.get_job_status = Mock(
        return_value={
            "status": "COMPLETED",
            "transcript_uri": "https://example.invalid/transcript.json",
        }
    )

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            payload = {"results": {"transcripts": [{"transcript": "hello doctor"}]}}
            return json.dumps(payload).encode("utf-8")

    original_urlopen = transcribe_manager_module.urlopen
    transcribe_manager_module.urlopen = Mock(return_value=_FakeResponse())
    try:
        result = manager.get_transcript("job-789")
        assert result == "hello doctor"
    finally:
        transcribe_manager_module.urlopen = original_urlopen


def test_get_transcript_falls_back_to_s3_on_http_403():
    """If transcript URI fetch is forbidden, fallback to S3 SDK fetch should work."""
    manager = _make_manager()
    manager.region = "ap-south-1"
    manager.get_job_status = Mock(
        return_value={
            "status": "COMPLETED",
            "transcript_uri": "https://s3.ap-south-1.amazonaws.com/my-bucket/path/to/file.json",
        }
    )

    http_error = urllib.error.HTTPError(
        url="https://s3.ap-south-1.amazonaws.com/my-bucket/path/to/file.json",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=None,
    )

    class _FakeBody:
        def read(self):
            payload = {"results": {"transcripts": [{"transcript": "fallback transcript"}]}}
            return json.dumps(payload).encode("utf-8")

    fake_s3_client = Mock()
    fake_s3_client.get_object = Mock(return_value={"Body": _FakeBody()})

    original_urlopen = transcribe_manager_module.urlopen
    original_boto_client = transcribe_manager_module.boto3.client
    transcribe_manager_module.urlopen = Mock(side_effect=http_error)
    transcribe_manager_module.boto3.client = Mock(return_value=fake_s3_client)
    try:
        result = manager.get_transcript("job-999")
        assert result == "fallback transcript"
        fake_s3_client.get_object.assert_called_once_with(
            Bucket="my-bucket", Key="path/to/file.json"
        )
    finally:
        transcribe_manager_module.urlopen = original_urlopen
        transcribe_manager_module.boto3.client = original_boto_client
