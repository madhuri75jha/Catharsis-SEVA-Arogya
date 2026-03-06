"""Unit tests for LambdaPDFService."""
import base64
import io
import json
from unittest.mock import Mock, patch

from services.lambda_pdf_service import LambdaPDFService


def _mock_lambda_stream(payload):
    return io.BytesIO(json.dumps(payload).encode("utf-8"))


def test_generate_pdf_returns_data_for_success_response():
    mock_client = Mock()
    mock_client.invoke.return_value = {
        "StatusCode": 200,
        "Payload": _mock_lambda_stream({"success": True, "s3_key": "prescriptions/u/rx.pdf"}),
    }

    with patch("services.lambda_pdf_service.boto3.client", return_value=mock_client):
        svc = LambdaPDFService(region="ap-south-1", function_name="pdf-lambda")
        result = svc.generate_pdf({"prescription": {"prescription_id": "rx"}})

    assert result["success"] is True
    assert result["s3_key"] == "prescriptions/u/rx.pdf"


def test_generate_pdf_unwraps_apigw_body():
    mock_client = Mock()
    mock_client.invoke.return_value = {
        "StatusCode": 200,
        "Payload": _mock_lambda_stream(
            {"statusCode": 200, "body": json.dumps({"success": True, "cached": True})}
        ),
    }

    with patch("services.lambda_pdf_service.boto3.client", return_value=mock_client):
        svc = LambdaPDFService(region="ap-south-1", function_name="pdf-lambda")
        result = svc.generate_pdf({"x": 1})

    assert result == {"success": True, "cached": True}


def test_generate_pdf_returns_failure_payload_when_lambda_reports_failure():
    mock_client = Mock()
    mock_client.invoke.return_value = {
        "StatusCode": 200,
        "Payload": _mock_lambda_stream({"success": False, "message": "validation failed"}),
    }

    with patch("services.lambda_pdf_service.boto3.client", return_value=mock_client):
        svc = LambdaPDFService(region="ap-south-1", function_name="pdf-lambda")
        result = svc.generate_pdf({"x": 1})

    assert result["success"] is False
    assert result["message"] == "validation failed"


def test_generate_pdf_returns_none_for_non_200_invoke_status():
    mock_client = Mock()
    mock_client.invoke.return_value = {"StatusCode": 500, "Payload": _mock_lambda_stream({})}

    with patch("services.lambda_pdf_service.boto3.client", return_value=mock_client):
        svc = LambdaPDFService(region="ap-south-1", function_name="pdf-lambda")
        result = svc.generate_pdf({"x": 1})

    assert result is None


def test_generate_pdf_returns_none_when_payload_missing():
    mock_client = Mock()
    mock_client.invoke.return_value = {"StatusCode": 200}

    with patch("services.lambda_pdf_service.boto3.client", return_value=mock_client):
        svc = LambdaPDFService(region="ap-south-1", function_name="pdf-lambda")
        result = svc.generate_pdf({"x": 1})

    assert result is None


def test_generate_pdf_returns_none_for_invalid_json():
    mock_client = Mock()
    mock_client.invoke.return_value = {"StatusCode": 200, "Payload": io.BytesIO(b"not-json")}

    with patch("services.lambda_pdf_service.boto3.client", return_value=mock_client):
        svc = LambdaPDFService(region="ap-south-1", function_name="pdf-lambda")
        result = svc.generate_pdf({"x": 1})

    assert result is None


def test_decode_pdf_base64_success():
    raw = b"%PDF-1.4 test"
    encoded = base64.b64encode(raw).decode("utf-8")

    decoded = LambdaPDFService.decode_pdf_base64(encoded)

    assert decoded == raw


def test_decode_pdf_base64_failure_returns_none():
    decoded = LambdaPDFService.decode_pdf_base64("%%%invalid-base64%%%")

    assert decoded is None
