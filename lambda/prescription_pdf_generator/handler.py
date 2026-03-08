"""Lambda handler for prescription PDF generation."""
import io
import json
import os
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
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
FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
DEFAULT_FONT_FILE = "NotoSans-Regular.ttf"
LANGUAGE_FONT_FILES = {
    # Indic
    "hi": "NotoSansDevanagari-Regular.ttf",
    "mr": "NotoSansDevanagari-Regular.ttf",
    "ne": "NotoSansDevanagari-Regular.ttf",
    "bn": "NotoSansBengali-Regular.ttf",
    "gu": "NotoSansGujarati-Regular.ttf",
    "pa": "NotoSansGurmukhi-Regular.ttf",
    "ta": "NotoSansTamil-Regular.ttf",
    "te": "NotoSansTelugu-Regular.ttf",
    "kn": "NotoSansKannada-Regular.ttf",
    "ml": "NotoSansMalayalam-Regular.ttf",
    "or": "NotoSansOriya-Regular.ttf",
    "si": "NotoSansSinhala-Regular.ttf",
    # Other scripts
    "ar": "NotoSansArabic-Regular.ttf",
    "he": "NotoSansHebrew-Regular.ttf",
    "th": "NotoSansThai-Regular.ttf",
    "lo": "NotoSansLao-Regular.ttf",
    "my": "NotoSansMyanmar-Regular.ttf",
    "km": "NotoSansKhmer-Regular.ttf",
}


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


def _extract_s3_bucket_key_from_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lstrip("/")

    if parsed.scheme == "s3":
        return parsed.netloc, unquote(path)

    if ".s3." in host and not host.startswith("s3."):
        bucket = host.split(".s3.", 1)[0]
        return bucket, unquote(path)

    if host.startswith("s3.") and path:
        parts = path.split("/", 1)
        if len(parts) == 2:
            return parts[0], unquote(parts[1])

    return "", ""


def _download_url_bytes(url: str, timeout_seconds: int = 6) -> bytes:
    req = Request(url, headers={"User-Agent": "seva-arogya-pdf/1.0"})
    with urlopen(req, timeout=timeout_seconds) as resp:  # nosec B310 - controlled logo URL fetch
        return resp.read()


def _load_logo_bytes(hospital: Dict[str, Any]) -> bytes:
    logo_url = str(hospital.get("logo_url") or "").strip()
    if not logo_url:
        return b""

    # Prefer direct URL fetch first (supports public and pre-signed URLs).
    if logo_url.startswith("http://") or logo_url.startswith("https://"):
        try:
            payload = _download_url_bytes(logo_url)
            if payload:
                return payload
        except Exception:
            pass

        # Fallback: parse S3-style URL and fetch via IAM credentials.
        try:
            bucket, key = _extract_s3_bucket_key_from_url(logo_url)
            if bucket and key:
                obj = s3.get_object(Bucket=bucket, Key=key)
                return obj["Body"].read()
        except Exception:
            return b""

    if logo_url.startswith("s3://"):
        try:
            bucket, key = _extract_s3_bucket_key_from_url(logo_url)
            if bucket and key:
                obj = s3.get_object(Bucket=bucket, Key=key)
                return obj["Body"].read()
        except Exception:
            return b""

    return b""


def _build_logo_flowable(hospital: Dict[str, Any]):
    logo_bytes = _load_logo_bytes(hospital)
    if not logo_bytes:
        return None
    try:
        from reportlab.platypus import Image

        logo = Image(io.BytesIO(logo_bytes))
        logo._restrictSize(1.1 * inch, 1.1 * inch)
        logo.hAlign = "CENTER"
        return logo
    except Exception:
        return None


def _section_order_from_config(hospital_config: Dict[str, Any]) -> List[str]:
    config_sections = sorted(
        hospital_config.get("sections", []) or [],
        key=lambda s: int(s.get("display_order", 999) or 999),
    )
    order: List[str] = []
    for section in config_sections:
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
        key = _normalize_section_key(section.get("key", ""))
        if key and key not in seen:
            ordered.append(section)

    return ordered


def _field_uses_vernacular(field: Dict[str, Any]) -> bool:
    return bool(field.get("vernacular_language") or field.get("response_language"))


def _section_config_map(hospital_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    section_map: Dict[str, Dict[str, Any]] = {}
    sorted_sections = sorted(
        hospital_config.get("sections", []) or [],
        key=lambda s: int(s.get("display_order", 999) or 999),
    )
    for section in sorted_sections:
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


def _same_text(a: str, b: str) -> bool:
    norm_a = " ".join(str(a or "").strip().lower().split())
    norm_b = " ".join(str(b or "").strip().lower().split())
    return bool(norm_a) and norm_a == norm_b


def _register_multilingual_font(target_language_code: str) -> str:
    """Register bundled font for selected language when present."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except Exception:
        return ""

    font_file = LANGUAGE_FONT_FILES.get(target_language_code, DEFAULT_FONT_FILE)
    font_path = os.path.join(FONTS_DIR, font_file)
    font_name = os.path.splitext(font_file)[0]

    try:
        if pdfmetrics.getFont(font_name):
            return font_name
    except Exception:
        pass

    if not os.path.exists(font_path):
        return ""

    try:
        pdfmetrics.registerFont(TTFont(font_name, font_path))
        return font_name
    except Exception:
        return ""


def _build_field_table_rows(
    section_content: Any,
    section_cfg: Dict[str, Any],
    target_language_code: str,
    translation_cache: Dict[str, str],
    multilingual_font_name: str = "",
) -> List[List[Paragraph]]:
    fields = section_cfg.get("fields", []) or []
    if not fields:
        return []

    repeatable = bool(section_cfg.get("repeatable"))
    section_rows = _coerce_section_rows(section_content, repeatable)
    if not section_rows:
        section_rows = [{}]

    usable_fields = [field for field in fields if str(field.get("field_name") or "").strip()]
    if not usable_fields:
        return []

    table_rows: List[List[Paragraph]] = []

    # Header row (horizontal): one column per field.
    header_row: List[Paragraph] = []
    for field in usable_fields:
        field_name = str(field.get("field_name") or "").strip()
        english_label = str(field.get("display_label") or field_name.replace("_", " ").title()).strip()
        translated_label = _translate_text(english_label, target_language_code, translation_cache)
        if target_language_code == "en" or _same_text(english_label, translated_label):
            bilingual_label = escape(english_label)
        else:
            if multilingual_font_name and translated_label:
                translated_label_html = f"<font name='{multilingual_font_name}'>{escape(translated_label)}</font>"
            else:
                translated_label_html = escape(translated_label)
            bilingual_label = f"{escape(english_label)} / {translated_label_html}"
        header_row.append(Paragraph(f"<b>{bilingual_label}</b>", getSampleStyleSheet()["Normal"]))
    table_rows.append(header_row)

    # Data rows: each repeatable item becomes one row; non-repeatable is a single row.
    for row_data in section_rows:
        value_row: List[Paragraph] = []
        for field in usable_fields:
            field_name = str(field.get("field_name") or "").strip()
            english_value = row_data.get(field_name, "")
            if not english_value and row_data.get("_raw_content") and len(usable_fields) == 1:
                english_value = row_data.get("_raw_content")
            english_value_text = str(english_value or "").strip() or "-"

            if _field_uses_vernacular(field):
                translated_value = _translate_text(english_value_text, target_language_code, translation_cache)
                if target_language_code == "en" or _same_text(english_value_text, translated_value):
                    value_html = escape(english_value_text)
                else:
                    if multilingual_font_name and translated_value:
                        translated_value_html = (
                            f"<font name='{multilingual_font_name}' size='8' color='#475569'>{escape(translated_value)}</font>"
                        )
                    else:
                        translated_value_html = f"<font size='8' color='#475569'>{escape(translated_value)}</font>"
                    value_html = f"{escape(english_value_text)}<br/>{translated_value_html}"
            else:
                value_html = escape(english_value_text)

            value_row.append(Paragraph(value_html.replace("\n", "<br/>"), getSampleStyleSheet()["Normal"]))
        table_rows.append(value_row)

    return table_rows


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
    logo = _build_logo_flowable(hospital)
    if logo is not None:
        story.append(logo)
        story.append(Spacer(1, 0.08 * inch))

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
    multilingual_font_name = _register_multilingual_font(target_language_code) if target_language_code != "en" else ""
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
            field_rows = _build_field_table_rows(
                content,
                section_cfg,
                target_language_code,
                translation_cache,
                multilingual_font_name=multilingual_font_name,
            )
            if field_rows:
                column_count = max(len(field_rows[0]), 1)
                total_width = 6.3 * inch
                col_width = total_width / column_count
                table = Table(field_rows, colWidths=[col_width] * column_count)
                table.setStyle(
                    TableStyle(
                        [
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#127ae2")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
