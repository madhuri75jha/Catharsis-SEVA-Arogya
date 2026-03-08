from __future__ import annotations

"""PDF Generator Service for creating prescription PDFs with dynamic section rendering"""
import logging
import json
import ast
import re
from io import BytesIO
from typing import Dict, Any, List, Optional
from datetime import datetime
import boto3
from botocore.config import Config

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning("ReportLab not installed. PDF generation will not be available.")

logger = logging.getLogger(__name__)


def _normalize_section_key(section_key: Any) -> str:
    raw = str(section_key or '').strip().lower()
    if not raw:
        return ''
    # Normalize only numeric suffixes for repeatable section instances.
    return re.sub(r'_\d+$', '', raw)


class PDFGenerator:
    """Service for generating prescription PDFs with dynamic section rendering"""
    
    def __init__(self, storage_manager):
        """
        Initialize PDFGenerator
        
        Args:
            storage_manager: StorageManager instance for S3 operations
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")
        
        self.storage = storage_manager
        self.styles = getSampleStyleSheet()
        self.page_width, self.page_height = A4
        
        # Create custom styles
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles for PDF"""
        # Section title style
        self.section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=self.styles['Heading2'],
            textColor=colors.HexColor('#127ae2'),
            fontSize=14,
            spaceAfter=6,
            spaceBefore=12
        )
        
        # Hospital header style
        self.hospital_header_style = ParagraphStyle(
            'HospitalHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            spaceAfter=12
        )

        self.hospital_name_style = ParagraphStyle(
            'HospitalName',
            parent=self.styles['Heading1'],
            alignment=TA_CENTER,
            textColor=colors.HexColor('#0f4c81'),
            fontSize=19,
            leading=22,
            spaceAfter=4
        )

        self.document_title_style = ParagraphStyle(
            'DocumentTitle',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            textColor=colors.HexColor('#127ae2'),
            fontSize=11,
            leading=13,
            spaceAfter=8
        )

        self.hospital_contact_style = ParagraphStyle(
            'HospitalContact',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            textColor=colors.HexColor('#475569'),
            fontSize=9,
            leading=11,
            spaceAfter=3
        )
        
        # Metadata style
        self.metadata_style = ParagraphStyle(
            'Metadata',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
    
    def generate_prescription_pdf(
        self,
        prescription: Dict[str, Any],
        hospital: Dict[str, Any],
        hospital_config: Optional[Dict[str, Any]] = None,
        translation: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Generate prescription PDF and upload to S3
        
        Args:
            prescription: Prescription dictionary
            hospital: Hospital dictionary
            
        Returns:
            S3 key if successful, None otherwise
        """
        try:
            # Generate PDF bytes
            pdf_bytes = self._generate_pdf_bytes(
                prescription,
                hospital,
                hospital_config=hospital_config or {},
                translation=translation or {},
            )
            
            # Upload to S3
            prescription_id = prescription['prescription_id']
            owner_id = prescription.get('user_id') or prescription.get('created_by_doctor_id') or 'system'

            uploaded_key = self.storage.upload_pdf(pdf_bytes, str(owner_id), str(prescription_id))
            if uploaded_key:
                logger.info(f"PDF generated and uploaded: {uploaded_key}")
                return uploaded_key
            else:
                logger.error(f"Failed to upload PDF to S3 for prescription {prescription_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate prescription PDF: {str(e)}")
            return None
    
    def _generate_pdf_bytes(
        self,
        prescription: Dict[str, Any],
        hospital: Dict[str, Any],
        hospital_config: Dict[str, Any] | None = None,
        translation: Dict[str, Any] | None = None,
    ) -> bytes:
        """
        Generate PDF document as bytes
        
        Args:
            prescription: Prescription dictionary
            hospital: Hospital dictionary
            
        Returns:
            PDF bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                               leftMargin=0.75*inch, rightMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []
        
        # Header with hospital branding
        story.extend(self._render_header(hospital))
        story.append(Spacer(1, 0.3*inch))
        
        # Prescription metadata
        story.extend(self._render_metadata(prescription))
        story.append(Spacer(1, 0.3*inch))
        
        hospital_config = hospital_config or {}
        translation = translation or {}
        target_language_code = str(translation.get('target_language_code') or 'en').strip().lower() or 'en'

        # Dynamic sections
        sections = self._normalize_sections(prescription.get('sections', []))
        section_cfg_map = self._section_config_map(hospital_config)
        sorted_sections = self._order_sections(sections, hospital_config)
        translation_cache: Dict[str, str] = {}
        
        for section in sorted_sections:
            # Only render sections with content
            if section.get('content'):
                section_key = str(section.get('key') or '').strip().lower()
                section_cfg = section_cfg_map.get(_normalize_section_key(section_key), {})
                story.extend(
                    self._render_section(
                        section,
                        section_cfg=section_cfg,
                        target_language_code=target_language_code,
                        translation_cache=translation_cache,
                    )
                )
                story.append(Spacer(1, 0.2*inch))
        
        # Footer with doctor signature
        story.extend(self._render_footer(prescription))
        
        # Build PDF
        doc.build(story)
        
        return buffer.getvalue()

    def _section_config_map(self, hospital_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        section_map: Dict[str, Dict[str, Any]] = {}
        for section in hospital_config.get('sections', []) or []:
            section_id = str(section.get('section_id') or '').strip()
            if not section_id:
                continue
            section_map[_normalize_section_key(section_id)] = section
        return section_map

    def _order_sections(self, sections: List[Dict[str, Any]], hospital_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not sections:
            return []

        config_sections = sorted(
            hospital_config.get('sections', []) or [],
            key=lambda s: int(s.get('display_order', 999) or 999),
        )
        config_order = [_normalize_section_key(s.get('section_id')) for s in config_sections if s.get('section_id')]
        section_by_key: Dict[str, Dict[str, Any]] = {}
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_key = _normalize_section_key(section.get('key'))
            if section_key and section_key not in section_by_key:
                section_by_key[section_key] = section

        ordered: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for section_key in config_order:
            if section_key and section_key in section_by_key:
                ordered.append(section_by_key[section_key])
                seen.add(section_key)

        remaining = sorted(
            [s for s in sections if isinstance(s, dict) and _normalize_section_key(s.get('key')) not in seen],
            key=lambda s: int(s.get('display_order', s.get('order', 999)) or 999),
        )
        ordered.extend(remaining)
        return ordered

    def _normalize_sections(self, raw_sections: Any) -> List[Dict[str, Any]]:
        """Normalize sections into a list of dictionaries."""
        sections = raw_sections

        if isinstance(sections, str):
            try:
                sections = json.loads(sections)
            except json.JSONDecodeError:
                sections = []

        # Some legacy payloads store sections as an object keyed by section name.
        if isinstance(sections, dict):
            if isinstance(sections.get('sections'), list):
                sections = sections['sections']
            else:
                normalized_from_map: List[Dict[str, Any]] = []
                for index, (key, content) in enumerate(sections.items()):
                    normalized_from_map.append({
                        'key': str(key),
                        'title': str(key).replace('_', ' ').title(),
                        'content': content if content is not None else '',
                        'order': index + 1
                    })
                sections = normalized_from_map

        if not isinstance(sections, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for index, section in enumerate(sections):
            if isinstance(section, dict):
                if 'order' not in section and 'display_order' in section:
                    section['order'] = section.get('display_order')
                if 'display_order' not in section and 'order' in section:
                    section['display_order'] = section.get('order')
                if section.get('key'):
                    section['key'] = _normalize_section_key(section.get('key'))
                normalized.append(section)
                continue

            if isinstance(section, str):
                # Try JSON object encoded as string first.
                try:
                    parsed = json.loads(section)
                    if isinstance(parsed, dict):
                        normalized.append(parsed)
                        continue
                except json.JSONDecodeError:
                    pass

                if section.strip():
                    normalized.append({
                        'key': f'section_{index + 1}',
                        'title': f'Section {index + 1}',
                        'content': section,
                        'order': index + 1
                    })

        return normalized
    
    def _render_header(self, hospital: Dict[str, Any]) -> List:
        """
        Render hospital header with logo and information
        
        Args:
            hospital: Hospital dictionary
            
        Returns:
            List of flowable elements
        """
        elements = []
        
        # Hospital logo (if available)
        logo_url = hospital.get('logo_url')
        if logo_url:
            try:
                # Note: In production, you'd download the logo from S3
                # For now, we'll skip the logo if it's not accessible
                # logo = Image(logo_url, width=1*inch, height=1*inch)
                # elements.append(logo)
                pass
            except Exception as e:
                logger.warning(f"Could not load hospital logo: {str(e)}")
        
        hospital_name = str(hospital.get('name') or 'Hospital')
        elements.append(Paragraph(hospital_name, self.hospital_name_style))
        elements.append(Paragraph("MEDICAL PRESCRIPTION", self.document_title_style))

        if hospital.get('address'):
            elements.append(Paragraph(str(hospital['address']), self.hospital_contact_style))

        contact_parts = []
        if hospital.get('phone'):
            contact_parts.append(f"Phone: {hospital['phone']}")
        if hospital.get('email'):
            contact_parts.append(f"Email: {hospital['email']}")
        if contact_parts:
            elements.append(Paragraph(" | ".join(contact_parts), self.hospital_contact_style))

        aux_parts = []
        if hospital.get('registration_number'):
            aux_parts.append(f"Reg. No: {hospital['registration_number']}")
        if hospital.get('website'):
            aux_parts.append(str(hospital['website']))
        if aux_parts:
            elements.append(Paragraph(" | ".join(aux_parts), self.hospital_contact_style))

        # Subtle divider beneath the letterhead.
        divider = Table([['']], colWidths=[6.4 * inch], rowHeights=[0.02 * inch])
        divider.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#dbe7f3')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(Spacer(1, 0.08 * inch))
        elements.append(divider)
        elements.append(Spacer(1, 0.12 * inch))
        
        return elements
    
    def _render_metadata(self, prescription: Dict[str, Any]) -> List:
        """
        Render prescription metadata
        
        Args:
            prescription: Prescription dictionary
            
        Returns:
            List of flowable elements
        """
        elements = []
        
        # Create metadata table
        doctor_name = str(prescription.get('doctor_name') or '').strip()
        if not doctor_name or '@' in doctor_name:
            doctor_name = 'Doctor'
        metadata_data = [
            ['Prescription ID:', str(prescription.get('prescription_id', 'N/A'))],
            ['Patient Name:', prescription.get('patient_name', 'N/A')],
            ['Doctor:', doctor_name],
            ['Date:', self._format_date(prescription.get('finalized_at') or prescription.get('created_at'))]
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        elements.append(metadata_table)
        
        return elements
    
    def _render_section(
        self,
        section: Dict[str, Any],
        section_cfg: Optional[Dict[str, Any]] = None,
        target_language_code: str = 'en',
        translation_cache: Optional[Dict[str, str]] = None,
    ) -> List:
        """
        Render a prescription section
        
        Args:
            section: Section dictionary
            
        Returns:
            List of flowable elements
        """
        elements = []
        
        # Section title
        title = section.get('title', section.get('key', 'Section'))
        elements.append(Paragraph(str(title), self.section_title_style))
        
        # Section content
        content = self._parse_structured_content(section.get('content', ''))
        section_key = str(section.get('key', '')).strip().lower()
        translation_cache = translation_cache or {}
        has_vernacular_fields = self._section_uses_vernacular(section_cfg or {})
        
        # Check if content is medications list (array)
        if section_key == 'medications' and isinstance(content, list):
            # Render as table
            table_element = self._format_medications_table(
                content,
                target_language_code=target_language_code if has_vernacular_fields else 'en',
                translation_cache=translation_cache,
            )
            if table_element:
                elements.append(table_element)
            elif content:
                elements.append(Paragraph(self._format_list_content(content), self.styles['Normal']))
        else:
            content_text = self._format_content_for_paragraph(content, section_key)
            if content_text:
                if has_vernacular_fields and target_language_code != 'en':
                    translated = self._translate_text(
                        re.sub(r'<br\s*/?>', '\n', content_text),
                        target_language_code,
                        translation_cache,
                    )
                    content_text = (
                        f"{content_text}<br/><font size='8' color='#475569'>{translated.replace('\n', '<br/>')}</font>"
                    )
                elements.append(Paragraph(content_text, self.styles['Normal']))
        
        return elements
    
    def _format_medications_table(
        self,
        medications: List[Dict[str, Any]],
        target_language_code: str = 'en',
        translation_cache: Optional[Dict[str, str]] = None,
    ) -> Optional[Table]:
        """
        Format medications as a table
        
        Args:
            medications: List of medication dictionaries
            
        Returns:
            Table element or None
        """
        if not medications:
            return None
        
        # Table header
        table_data = [['Medication', 'Dosage', 'Frequency', 'Duration']]
        
        # Add medication rows
        for med in medications:
            if isinstance(med, dict):
                name = (
                    med.get('name') or med.get('medication') or med.get('medication_name') or
                    med.get('medicine') or med.get('medicine_name') or med.get('drug') or
                    med.get('drug_name') or med.get('brand') or med.get('brand_name') or
                    med.get('generic') or med.get('generic_name') or med.get('tablet') or ''
                )
                dosage = med.get('dosage') or med.get('dose') or med.get('strength') or med.get('qty') or ''
                frequency = med.get('frequency') or med.get('schedule') or med.get('timing') or med.get('when') or ''
                duration = med.get('duration') or med.get('course') or med.get('days') or ''

                # Last-resort name inference: choose first non-empty field that is not dose/frequency/duration.
                if not name:
                    excluded = {
                        'dosage', 'dose', 'strength', 'qty',
                        'frequency', 'schedule', 'timing', 'when',
                        'duration', 'course', 'days', 'notes', 'instructions'
                    }
                    for key, value in med.items():
                        if str(key).lower() in excluded:
                            continue
                        if value not in [None, '']:
                            name = value
                            break

                name_text = str(name)
                dosage_text = str(dosage)
                frequency_text = str(frequency)
                duration_text = str(duration)

                if target_language_code != 'en':
                    cache = translation_cache or {}
                    name_text = f"{name_text}\n{self._translate_text(name_text, target_language_code, cache)}"
                    dosage_text = f"{dosage_text}\n{self._translate_text(dosage_text, target_language_code, cache)}"
                    frequency_text = f"{frequency_text}\n{self._translate_text(frequency_text, target_language_code, cache)}"
                    duration_text = f"{duration_text}\n{self._translate_text(duration_text, target_language_code, cache)}"

                table_data.append([name_text, dosage_text, frequency_text, duration_text])
            elif med:
                table_data.append([str(med), '', '', ''])

        # Do not render a table with only header row.
        if len(table_data) == 1:
            return None
        
        # Create table
        table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#127ae2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        return table

    def _section_uses_vernacular(self, section_cfg: Dict[str, Any]) -> bool:
        for field in section_cfg.get('fields', []) or []:
            if isinstance(field, dict) and (field.get('vernacular_language') or field.get('response_language')):
                return True
        return False

    def _get_translate_client(self):
        if not hasattr(self, '_translate_client'):
            self._translate_client = boto3.client(
                'translate',
                config=Config(connect_timeout=3, read_timeout=10, retries={'max_attempts': 2}),
            )
        return self._translate_client

    def _translate_text(self, text: str, target_language_code: str, translation_cache: Dict[str, str]) -> str:
        normalized = str(text or '').strip()
        if not normalized:
            return ''
        if target_language_code.lower() == 'en':
            return normalized

        cache_key = f"{target_language_code}:{normalized}"
        if cache_key in translation_cache:
            return translation_cache[cache_key]

        try:
            response = self._get_translate_client().translate_text(
                Text=normalized[:4500],
                SourceLanguageCode='en',
                TargetLanguageCode=target_language_code,
            )
            translated = str(response.get('TranslatedText') or '').strip() or normalized
            translation_cache[cache_key] = translated
            return translated
        except Exception as e:
            logger.warning("Translation failed for '%s': %s", normalized[:60], str(e))
            translation_cache[cache_key] = normalized
            return normalized
    
    def _render_footer(self, prescription: Dict[str, Any]) -> List:
        """
        Render footer with doctor signature
        
        Args:
            prescription: Prescription dictionary
            
        Returns:
            List of flowable elements
        """
        elements = []
        
        elements.append(Spacer(1, 0.5*inch))
        
        # Doctor signature (if available)
        signature_url = prescription.get('doctor_signature_url')
        if signature_url:
            try:
                # Note: In production, you'd download the signature from S3
                # signature = Image(signature_url, width=2*inch, height=0.5*inch)
                # elements.append(signature)
                pass
            except Exception as e:
                logger.warning(f"Could not load doctor signature: {str(e)}")
        
        # Doctor information
        doctor_info_parts = []
        
        doctor_name = str(prescription.get('doctor_name') or '').strip()
        if not doctor_name or '@' in doctor_name:
            doctor_name = 'Doctor'
        doctor_info_parts.append(f"<b>Dr. {doctor_name}</b>")
        
        if prescription.get('doctor_specialty'):
            doctor_info_parts.append(prescription['doctor_specialty'])
        
        finalized_at = prescription.get('finalized_at') or prescription.get('created_at')
        if finalized_at:
            doctor_info_parts.append(f"Date: {self._format_date(finalized_at)}")
        
        doctor_info = "<br/>".join(doctor_info_parts)
        elements.append(Paragraph(doctor_info, self.styles['Normal']))
        
        return elements

    def _parse_structured_content(self, content: Any) -> Any:
        """Best-effort parse for JSON/Python-literal strings."""
        if not isinstance(content, str):
            return content

        stripped = content.strip()
        if not stripped:
            return ''

        if stripped[0] in ['{', '['] and stripped[-1] in ['}', ']']:
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                try:
                    return ast.literal_eval(stripped)
                except Exception:
                    return content
        return content

    def _humanize_key(self, key: str) -> str:
        return str(key).replace('_', ' ').strip().title()

    def _format_dict_content(self, content: Dict[str, Any], section_key: str) -> str:
        if not content:
            return ''

        # Common case: {"diagnosis": "..."} inside Diagnosis section.
        if section_key and section_key in content and len(content) == 1:
            return self._format_content_for_paragraph(content[section_key], section_key)

        lines: List[str] = []
        for key, value in content.items():
            if value in [None, '', [], {}]:
                continue
            value_text = self._format_content_for_paragraph(value, str(key).lower())
            if value_text:
                lines.append(f"<b>{self._humanize_key(str(key))}:</b> {value_text}")
        return '<br/>'.join(lines)

    def _format_list_content(self, content: List[Any]) -> str:
        lines: List[str] = []
        for item in content:
            if isinstance(item, dict):
                formatted = self._format_dict_content(item, '')
                if formatted:
                    lines.append(f"- {formatted}")
            elif item not in [None, '']:
                lines.append(f"- {str(item)}")
        return '<br/>'.join(lines)

    def _format_content_for_paragraph(self, content: Any, section_key: str) -> str:
        if content in [None, '', [], {}]:
            return ''
        if isinstance(content, str):
            return content.replace('\n', '<br/>')
        if isinstance(content, dict):
            return self._format_dict_content(content, section_key)
        if isinstance(content, list):
            return self._format_list_content(content)
        return str(content)
    
    def _format_date(self, date_value: Any) -> str:
        """
        Format date for display
        
        Args:
            date_value: Date string or datetime object
            
        Returns:
            Formatted date string
        """
        if not date_value:
            return 'N/A'
        
        try:
            if isinstance(date_value, str):
                date_obj = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            else:
                date_obj = date_value
            
            return date_obj.strftime('%B %d, %Y')
        except Exception as e:
            logger.warning(f"Could not format date: {str(e)}")
            return str(date_value)
    
    def get_signed_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Get signed URL for PDF download
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration in seconds (default 1 hour)
            
        Returns:
            Signed URL or None
        """
        try:
            url = self.storage.generate_presigned_url(s3_key, expiration=expiration)
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {str(e)}")
            return None
