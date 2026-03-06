"""Unit tests for Lambda-based prescription PDF generator handler."""
import importlib
import importlib.util
import json
import sys
import types
from unittest.mock import Mock


def _install_reportlab_stub():
    reportlab = types.ModuleType("reportlab")
    reportlab.lib = types.ModuleType("reportlab.lib")
    reportlab.lib.colors = types.ModuleType("reportlab.lib.colors")
    reportlab.lib.colors.HexColor = lambda _value: "#127ae2"
    reportlab.lib.pagesizes = types.ModuleType("reportlab.lib.pagesizes")
    reportlab.lib.pagesizes.A4 = (595, 842)
    reportlab.lib.styles = types.ModuleType("reportlab.lib.styles")
    reportlab.lib.styles.ParagraphStyle = lambda *args, **kwargs: {"args": args, "kwargs": kwargs}
    reportlab.lib.styles.getSampleStyleSheet = lambda: {
        "Heading3": object(),
        "Normal": types.SimpleNamespace(leading=12),
        "Title": object(),
    }
    reportlab.lib.units = types.ModuleType("reportlab.lib.units")
    reportlab.lib.units.inch = 72
    reportlab.platypus = types.ModuleType("reportlab.platypus")

    class _SimpleDocTemplate:
        def __init__(self, buffer, **_kwargs):
            self._buffer = buffer

        def build(self, _story):
            self._buffer.write(b"%PDF-FAKE")

    reportlab.platypus.Paragraph = lambda *args, **kwargs: ("Paragraph", args, kwargs)
    reportlab.platypus.SimpleDocTemplate = _SimpleDocTemplate
    reportlab.platypus.Spacer = lambda *args, **kwargs: ("Spacer", args, kwargs)
    reportlab.platypus.Table = lambda *args, **kwargs: types.SimpleNamespace(setStyle=lambda *_: None)
    reportlab.platypus.TableStyle = lambda *args, **kwargs: ("TableStyle", args, kwargs)

    sys.modules["reportlab"] = reportlab
    sys.modules["reportlab.lib"] = reportlab.lib
    sys.modules["reportlab.lib.colors"] = reportlab.lib.colors
    sys.modules["reportlab.lib.pagesizes"] = reportlab.lib.pagesizes
    sys.modules["reportlab.lib.styles"] = reportlab.lib.styles
    sys.modules["reportlab.lib.units"] = reportlab.lib.units
    sys.modules["reportlab.platypus"] = reportlab.platypus


if importlib.util.find_spec("reportlab") is None:
    _install_reportlab_stub()

handler = importlib.import_module("lambda.prescription_pdf_generator.handler")


def _base_payload():
    return {
        "prescription": {
            "prescription_id": "rx-123",
            "patient_name": "Ravi Kumar",
            "doctor_name": "Ananya Shah",
            "sections": [
                {"key": "diagnosis", "title": "Diagnosis", "content": "Viral fever"},
                {
                    "key": "medications",
                    "title": "Medications",
                    "content": ["Paracetamol 650mg - SOS", "Hydration advised"],
                },
                {"key": "followup", "title": "Follow Up", "content": "Review in 3 days"},
            ],
        },
        "hospital": {
            "name": "City Care Hospital",
            "address": "MG Road, Bengaluru",
            "phone": "+91-80-1234-5678",
            "email": "info@citycare.test",
        },
        "hospital_config": {
            "sections": [
                {"section_id": "medications_1"},
                {"section_id": "diagnosis_1"},
                {"section_id": "followup_1"},
            ]
        },
        "translation": {"target_language_code": "en", "target_language_name": "English"},
        "metadata": {"requested_by": "doctor-777", "prescription_id": "rx-123"},
    }


def _response_body(resp):
    return json.loads(resp["body"])


def test_lambda_handler_returns_500_when_pdf_bucket_missing(monkeypatch):
    payload = _base_payload()
    monkeypatch.setattr(handler, "PDF_BUCKET", "")

    resp = handler.lambda_handler(payload, None)

    assert resp["statusCode"] == 500
    assert _response_body(resp)["success"] is False
    assert "PDF_BUCKET not configured" in _response_body(resp)["message"]


def test_lambda_handler_returns_cached_pdf_when_payload_hash_matches(monkeypatch):
    payload = _base_payload()
    s3_mock = Mock()
    s3_mock.head_object.return_value = {"Metadata": {"payloadhash": "same-hash"}}
    s3_mock.generate_presigned_url.return_value = "https://cached-url"
    monkeypatch.setattr(handler, "PDF_BUCKET", "test-pdf-bucket")
    monkeypatch.setattr(handler, "s3", s3_mock)
    monkeypatch.setattr(handler, "_build_payload_hash", lambda *args, **kwargs: "same-hash")

    resp = handler.lambda_handler(payload, None)
    body = _response_body(resp)

    assert resp["statusCode"] == 200
    assert body["success"] is True
    assert body["cached"] is True
    assert body["s3_key"] == "prescriptions/doctor-777/rx-123.pdf"
    s3_mock.put_object.assert_not_called()


def test_lambda_handler_generates_and_uploads_pdf_when_cache_miss(monkeypatch):
    payload = _base_payload()
    s3_mock = Mock()
    s3_mock.head_object.side_effect = Exception("No object")
    s3_mock.generate_presigned_url.return_value = "https://new-url"
    monkeypatch.setattr(handler, "PDF_BUCKET", "test-pdf-bucket")
    monkeypatch.setattr(handler, "s3", s3_mock)

    resp = handler.lambda_handler(payload, None)
    body = _response_body(resp)

    assert resp["statusCode"] == 200
    assert body["success"] is True
    assert body["s3_key"] == "prescriptions/doctor-777/rx-123.pdf"
    s3_mock.put_object.assert_called_once()
    put_kwargs = s3_mock.put_object.call_args.kwargs
    assert put_kwargs["Bucket"] == "test-pdf-bucket"
    assert put_kwargs["Key"] == "prescriptions/doctor-777/rx-123.pdf"
    assert put_kwargs["ContentType"] == "application/pdf"
    assert isinstance(put_kwargs["Body"], (bytes, bytearray))
    assert put_kwargs["Body"].startswith(b"%PDF")


def test_lambda_handler_accepts_apigw_body_string(monkeypatch):
    payload = _base_payload()
    event = {"body": json.dumps(payload)}
    s3_mock = Mock()
    s3_mock.head_object.side_effect = Exception("miss")
    s3_mock.generate_presigned_url.return_value = "https://new-url"
    monkeypatch.setattr(handler, "PDF_BUCKET", "test-pdf-bucket")
    monkeypatch.setattr(handler, "s3", s3_mock)

    resp = handler.lambda_handler(event, None)

    assert resp["statusCode"] == 200
    assert _response_body(resp)["success"] is True


def test_section_normalization_honors_hospital_order_and_json_sections():
    prescription = {
        "sections": json.dumps(
            [
                {"key": "followup", "title": "Follow Up", "content": "3 days"},
                {"key": "diagnosis", "title": "Diagnosis", "content": "Migraine"},
                {"key": "medications", "title": "Medications", "content": ["Sumatriptan"]},
            ]
        )
    }
    hospital_config = {
        "sections": [
            {"section_id": "medications_1"},
            {"section_id": "diagnosis_1"},
            {"section_id": "followup_1"},
        ]
    }

    normalized = handler._normalize_sections(prescription, hospital_config)

    assert [section["key"] for section in normalized] == ["medications", "diagnosis", "followup"]


def test_build_pdf_bytes_handles_missing_fields_with_defaults():
    prescription = {"sections": [{"key": "notes", "title": "Notes", "content": "Observation"}]}
    hospital = {}
    hospital_config = {}

    pdf_bytes = handler._build_pdf_bytes(
        prescription,
        hospital,
        hospital_config,
        {"target_language_code": "en", "target_language_name": "English"},
    )

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 5


def test_section_normalization_supports_dictionary_sections():
    prescription = {
        "sections": {
            "diagnosis": {"diagnosis": "Migraine"},
            "vitals": {"temperature": "99F"},
        }
    }
    hospital_config = {"sections": [{"section_id": "vitals"}, {"section_id": "diagnosis"}]}

    normalized = handler._normalize_sections(prescription, hospital_config)

    assert [section["key"] for section in normalized] == ["vitals", "diagnosis"]
