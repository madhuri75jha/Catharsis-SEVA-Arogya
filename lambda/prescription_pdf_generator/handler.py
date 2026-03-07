"""Lambda handler for prescription PDF generation."""
import io
import json
import os
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from xml.sax.saxutils import escape

import boto3

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


s3 = boto3.client("s3")
translate = boto3.client("translate")
PDF_BUCKET = os.getenv("PDF_BUCKET", "")


def _normalize_section_key(section_key: Any) -> str:
    raw = str(section_key or "").strip().lower()
    if not raw:
        return ""
    # Normalize only numeric suffixes used for repeatable section instances (e.g., medications_1).
    return re.sub(r"_\d+$", "", raw)


def _resolve_doctor_display_name(prescription: Dict[str, Any]) -> str:
    doctor_name = str(prescription.get("doctor_name") or "").strip()
    if doctor_name and "@" not in doctor_name:
        return doctor_name
    return "Doctor"


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
            order.append(_normalize_section_key(section_id))
    return order


def _normalize_sections(prescription: Dict[str, Any], hospital_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    sections = prescription.get("sections", [])
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except json.JSONDecodeError:
            sections = []

    if isinstance(sections, dict):
        from_map: List[Dict[str, Any]] = []
        for index, (key, value) in enumerate(sections.items()):
            from_map.append(
                {
                    "key": str(key),
                    "title": str(key).replace("_", " ").title(),
                    "content": value,
                    "order": index + 1,
                }
            )
        sections = from_map

    if not isinstance(sections, list):
        sections = []

    section_by_key = {}
    for section in sections:
        if isinstance(section, dict):
            key = section.get("key")
            if key:
                section_by_key[_normalize_section_key(key)] = section

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


def _field_uses_vernacular(field: Dict[str, Any]) -> bool:
    return bool(field.get("vernacular_language") or field.get("response_language"))


def _section_config_map(hospital_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    section_map: Dict[str, Dict[str, Any]] = {}
    for section in hospital_config.get("sections", []) or []:
        section_id = str(section.get("section_id") or "").strip()
        if not section_id:
            continue
        base_id = _normalize_section_key(section_id)
        fields = section.get("fields", []) or []
        if isinstance(fields, list):
            fields = sorted(fields, key=lambda f: int(f.get("display_order", 999)))
        section_map[base_id] = {
            "repeatable": bool(section.get("repeatable")),
            "fields": fields,
        }
    return section_map


def _coerce_section_rows(content: Any, repeatable: bool) -> List[Dict[str, Any]]:
    if repeatable:
        if isinstance(content, list):
            return [item for item in content if isinstance(item, dict)]
        if isinstance(content, dict):
            return [content]
        return []

    if isinstance(content, dict):
        return [content]
    if isinstance(content, list):
        first_dict = next((item for item in content if isinstance(item, dict)), None)
        return [first_dict] if first_dict else []
    if isinstance(content, str) and content.strip():
        return [{"_raw_content": content.strip()}]
    return []


def _translate_text(text: str, target_language_code: str, translation_cache: Dict[str, str]) -> str:
    normalized = (text or "").strip()
    if not normalized:
        return ""
    if target_language_code.lower() == "en":
        return normalized

    cache_key = f"{target_language_code}:{normalized}"
    if cache_key in translation_cache:
        return translation_cache[cache_key]

    try:
        response = translate.translate_text(
            Text=normalized[:4500],
            SourceLanguageCode="en",
            TargetLanguageCode=target_language_code,
        )
        translated = str(response.get("TranslatedText") or "").strip() or normalized
        translation_cache[cache_key] = translated
        return translated
    except Exception:
        translation_cache[cache_key] = normalized
        return normalized


def _build_field_table_rows(
    section_content: Any,
    section_cfg: Dict[str, Any],
    target_language_code: str,
    translation_cache: Dict[str, str],
) -> List[List[Paragraph]]:
    fields = section_cfg.get("fields", []) or []
    if not fields:
        return []

    rows: List[List[Paragraph]] = []
    repeatable = bool(section_cfg.get("repeatable"))
    section_rows = _coerce_section_rows(section_content, repeatable)
    if not section_rows:
        section_rows = [{}]

    for idx, row_data in enumerate(section_rows):
        if repeatable and len(section_rows) > 1:
            item_label = Paragraph(f"<b>Item {idx + 1}</b>", getSampleStyleSheet()["Normal"])
            rows.append([item_label, Paragraph("", getSampleStyleSheet()["Normal"])])

        for field in fields:
            field_name = str(field.get("field_name") or "").strip()
            if not field_name:
                continue
            english_label = str(field.get("display_label") or field_name.replace("_", " ").title()).strip()
            translated_label = _translate_text(english_label, target_language_code, translation_cache)
            bilingual_label = f"{escape(english_label)} / {escape(translated_label)}"

            english_value = row_data.get(field_name, "")
            if not english_value and row_data.get("_raw_content") and len(fields) == 1:
                english_value = row_data.get("_raw_content")
            english_value_text = str(english_value or "").strip() or "-"

            if _field_uses_vernacular(field):
                translated_value = _translate_text(english_value_text, target_language_code, translation_cache)
                value_html = f"{escape(english_value_text)}<br/><font size='8' color='#475569'>{escape(translated_value)}</font>"
            else:
                value_html = escape(english_value_text)

            rows.append(
                [
                    Paragraph(f"<b>{bilingual_label}</b>", getSampleStyleSheet()["Normal"]),
                    Paragraph(value_html.replace("\n", "<br/>"), getSampleStyleSheet()["Normal"]),
                ]
            )

    return rows


def _build_pdf_bytes(
    prescription: Dict[str, Any],
    hospital: Dict[str, Any],
    hospital_config: Dict[str, Any],
    translation: Dict[str, Any],
) -> bytes:
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
        ["Doctor", _resolve_doctor_display_name(prescription)],
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

    target_language_code = str(translation.get("target_language_code") or "en").strip().lower() or "en"
    translation_cache: Dict[str, str] = {}
    section_cfg_map = _section_config_map(hospital_config)

    for section in _normalize_sections(prescription, hospital_config):
        content = section.get("content")
        if not content:
            continue
        title = section.get("title") or section.get("key") or "Section"
        story.append(Paragraph(str(title), section_title))
        section_key = _normalize_section_key(section.get("key"))
        section_cfg = section_cfg_map.get(section_key)

        if section_cfg and section_cfg.get("fields"):
            field_rows = _build_field_table_rows(content, section_cfg, target_language_code, translation_cache)
            if field_rows:
                table = Table(field_rows, colWidths=[2.4 * inch, 3.9 * inch])
                table.setStyle(
                    TableStyle(
                        [
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                story.append(table)
            else:
                story.append(Paragraph(str(content).replace("\n", "<br/>"), normal))
        elif isinstance(content, list):
            for item in content:
                story.append(Paragraph(f"- {str(item)}", normal))
        else:
            story.append(Paragraph(str(content).replace("\n", "<br/>"), normal))
        story.append(Spacer(1, 0.08 * inch))

    doc.build(story)
    return buffer.getvalue()


def _build_payload_hash(
    prescription: Dict[str, Any],
    hospital: Dict[str, Any],
    hospital_config: Dict[str, Any],
    translation: Dict[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "prescription": prescription,
            "hospital": hospital,
            "hospital_config": hospital_config,
            "translation": translation,
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
        translation = payload.get("translation", {}) if isinstance(payload.get("translation"), dict) else {}

        prescription_id = str(metadata.get("prescription_id") or prescription.get("prescription_id") or "unknown")
        user_id = str(metadata.get("requested_by") or "system")
        if not PDF_BUCKET:
            return _http(500, {"success": False, "message": "PDF_BUCKET not configured"})

        s3_key = f"prescriptions/{user_id}/{prescription_id}.pdf"
        payload_hash = _build_payload_hash(prescription, hospital, hospital_config, translation)

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

        pdf_bytes = _build_pdf_bytes(prescription, hospital, hospital_config, translation)

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
