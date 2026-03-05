"""Lambda handler for prescription PDF generation."""
import io
import json
import os
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


s3 = boto3.client("s3")
PDF_BUCKET = os.getenv("PDF_BUCKET", "")


def _http(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _section_order_from_config(hospital_config: Dict[str, Any]) -> List[str]:
    order: List[str] = []
    for section in hospital_config.get("sections", []):
        section_id = section.get("section_id")
        if section_id:
            # Supports ids like medications_1 in config by normalizing suffix
            order.append(str(section_id).split("_")[0])
    return order


def _normalize_sections(prescription: Dict[str, Any], hospital_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    sections = prescription.get("sections", [])
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except json.JSONDecodeError:
            sections = []

    if not isinstance(sections, list):
        sections = []

    section_by_key = {}
    for section in sections:
        if isinstance(section, dict):
            key = section.get("key")
            if key:
                section_by_key[str(key)] = section

    ordered = []
    seen = set()
    for key in _section_order_from_config(hospital_config):
        if key in section_by_key:
            ordered.append(section_by_key[key])
            seen.add(key)

    for section in sections:
        if not isinstance(section, dict):
            continue
        key = str(section.get("key", ""))
        if key and key not in seen:
            ordered.append(section)

    return ordered


def _build_pdf_bytes(prescription: Dict[str, Any], hospital: Dict[str, Any], hospital_config: Dict[str, Any]) -> bytes:
    styles = getSampleStyleSheet()
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading3"],
        textColor=colors.HexColor("#127ae2"),
        spaceBefore=8,
        spaceAfter=4,
    )
    normal = styles["Normal"]
    normal.leading = 14

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )

    story = []
    hospital_name = hospital.get("name") or hospital_config.get("hospital_name") or "Hospital"
    story.append(Paragraph(f"<b>{hospital_name}</b>", styles["Title"]))
    contact_line = " | ".join(
        [x for x in [hospital.get("address"), hospital.get("phone"), hospital.get("email")] if x]
    )
    if contact_line:
        story.append(Paragraph(contact_line, normal))
    story.append(Spacer(1, 0.2 * inch))

    meta = [
        ["Prescription ID", str(prescription.get("prescription_id", "N/A"))],
        ["Patient", str(prescription.get("patient_name", "N/A"))],
        ["Doctor", str(prescription.get("doctor_name", "N/A"))],
        ["Date", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")],
    ]
    meta_table = Table(meta, colWidths=[1.5 * inch, 4.8 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 0.2 * inch))

    for section in _normalize_sections(prescription, hospital_config):
        content = section.get("content")
        if not content:
            continue
        title = section.get("title") or section.get("key") or "Section"
        story.append(Paragraph(str(title), section_title))
        if isinstance(content, list):
            for item in content:
                story.append(Paragraph(f"- {str(item)}", normal))
        else:
            story.append(Paragraph(str(content).replace("\n", "<br/>"), normal))
        story.append(Spacer(1, 0.08 * inch))

    doc.build(story)
    return buffer.getvalue()


def _build_payload_hash(prescription: Dict[str, Any], hospital: Dict[str, Any], hospital_config: Dict[str, Any]) -> str:
    canonical = json.dumps(
        {
            "prescription": prescription,
            "hospital": hospital,
            "hospital_config": hospital_config,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _get_cached_pdf_url(s3_key: str, payload_hash: str) -> str:
    try:
        head = s3.head_object(Bucket=PDF_BUCKET, Key=s3_key)
        metadata = head.get("Metadata", {}) or {}
        existing_hash = metadata.get("payloadhash")
        if existing_hash and existing_hash == payload_hash:
            return s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": PDF_BUCKET, "Key": s3_key},
                ExpiresIn=3600,
            )
    except Exception:
        return ""
    return ""


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    try:
        payload = event
        if isinstance(event, dict) and isinstance(event.get("body"), str):
            payload = json.loads(event["body"] or "{}")

        prescription = payload.get("prescription", {})
        hospital = payload.get("hospital", {})
        hospital_config = payload.get("hospital_config", {})
        metadata = payload.get("metadata", {})

        prescription_id = str(metadata.get("prescription_id") or prescription.get("prescription_id") or "unknown")
        user_id = str(metadata.get("requested_by") or "system")
        if not PDF_BUCKET:
            return _http(500, {"success": False, "message": "PDF_BUCKET not configured"})

        s3_key = f"prescriptions/{user_id}/{prescription_id}.pdf"
        payload_hash = _build_payload_hash(prescription, hospital, hospital_config)

        cached_url = _get_cached_pdf_url(s3_key, payload_hash)
        if cached_url:
            return _http(
                200,
                {
                    "success": True,
                    "cached": True,
                    "s3_key": s3_key,
                    "download_url": cached_url,
                    "expires_in": 3600,
                },
            )

        pdf_bytes = _build_pdf_bytes(prescription, hospital, hospital_config)

        s3.put_object(
            Bucket=PDF_BUCKET,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
            ServerSideEncryption="AES256",
            Metadata={
                "payloadhash": payload_hash,
                "generatedat": datetime.now(timezone.utc).isoformat(),
            },
        )

        download_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": PDF_BUCKET, "Key": s3_key},
            ExpiresIn=3600,
        )

        return _http(
            200,
            {
                "success": True,
                "s3_key": s3_key,
                "download_url": download_url,
                "expires_in": 3600,
            },
        )
    except Exception as exc:
        return _http(500, {"success": False, "message": f"Lambda PDF generation failed: {str(exc)}"})
