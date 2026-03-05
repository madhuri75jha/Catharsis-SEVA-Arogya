"""PDF Generator Service for creating prescription PDFs with dynamic section rendering"""
import logging
import json
from io import BytesIO
from typing import Dict, Any, List, Optional
from datetime import datetime

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
        
        # Metadata style
        self.metadata_style = ParagraphStyle(
            'Metadata',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
    
    def generate_prescription_pdf(self, prescription: Dict[str, Any], 
                                 hospital: Dict[str, Any]) -> Optional[str]:
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
            pdf_bytes = self._generate_pdf_bytes(prescription, hospital)
            
            # Upload to S3
            prescription_id = prescription['prescription_id']
            s3_key = f"prescriptions/{prescription_id}/prescription_{prescription_id}.pdf"
            
            success = self.storage.upload_pdf(pdf_bytes, s3_key)
            if success:
                logger.info(f"PDF generated and uploaded: {s3_key}")
                return s3_key
            else:
                logger.error(f"Failed to upload PDF to S3: {s3_key}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate prescription PDF: {str(e)}")
            return None
    
    def _generate_pdf_bytes(self, prescription: Dict[str, Any], 
                           hospital: Dict[str, Any]) -> bytes:
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
        
        # Dynamic sections
        sections = prescription.get('sections', [])
        if isinstance(sections, str):
            sections = json.loads(sections)
        
        # Sort sections by order
        sorted_sections = sorted(sections, key=lambda s: s.get('order', 999))
        
        for section in sorted_sections:
            # Only render sections with content
            if section.get('content'):
                story.extend(self._render_section(section))
                story.append(Spacer(1, 0.2*inch))
        
        # Footer with doctor signature
        story.extend(self._render_footer(prescription))
        
        # Build PDF
        doc.build(story)
        
        return buffer.getvalue()
    
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
        
        # Hospital information
        hospital_info_parts = [f"<b>{hospital.get('name', 'Hospital')}</b>"]
        
        if hospital.get('address'):
            hospital_info_parts.append(hospital['address'])
        
        contact_parts = []
        if hospital.get('phone'):
            contact_parts.append(f"Phone: {hospital['phone']}")
        if hospital.get('email'):
            contact_parts.append(f"Email: {hospital['email']}")
        
        if contact_parts:
            hospital_info_parts.append(" | ".join(contact_parts))
        
        if hospital.get('registration_number'):
            hospital_info_parts.append(f"Reg. No: {hospital['registration_number']}")
        
        if hospital.get('website'):
            hospital_info_parts.append(hospital['website'])
        
        hospital_info = "<br/>".join(hospital_info_parts)
        elements.append(Paragraph(hospital_info, self.hospital_header_style))
        
        # Horizontal line
        elements.append(Spacer(1, 0.1*inch))
        
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
        metadata_data = [
            ['Prescription ID:', str(prescription.get('prescription_id', 'N/A'))],
            ['Patient Name:', prescription.get('patient_name', 'N/A')],
            ['Doctor:', prescription.get('doctor_name', 'N/A')],
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
    
    def _render_section(self, section: Dict[str, Any]) -> List:
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
        elements.append(Paragraph(title, self.section_title_style))
        
        # Section content
        content = section.get('content', '')
        
        # Check if content is medications list (array)
        if section.get('key') == 'medications' and isinstance(content, list):
            # Render as table
            table_element = self._format_medications_table(content)
            if table_element:
                elements.append(table_element)
        else:
            # Render as paragraph
            if isinstance(content, str):
                # Replace newlines with <br/> for proper rendering
                content = content.replace('\n', '<br/>')
                elements.append(Paragraph(content, self.styles['Normal']))
        
        return elements
    
    def _format_medications_table(self, medications: List[Dict[str, Any]]) -> Optional[Table]:
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
                table_data.append([
                    med.get('name', ''),
                    med.get('dosage', ''),
                    med.get('frequency', ''),
                    med.get('duration', '')
                ])
        
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
        
        doctor_name = prescription.get('doctor_name', 'Doctor')
        doctor_info_parts.append(f"<b>Dr. {doctor_name}</b>")
        
        if prescription.get('doctor_specialty'):
            doctor_info_parts.append(prescription['doctor_specialty'])
        
        finalized_at = prescription.get('finalized_at') or prescription.get('created_at')
        if finalized_at:
            doctor_info_parts.append(f"Date: {self._format_date(finalized_at)}")
        
        doctor_info = "<br/>".join(doctor_info_parts)
        elements.append(Paragraph(doctor_info, self.styles['Normal']))
        
        return elements
    
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
            url = self.storage.generate_presigned_url(s3_key, expiration)
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {str(e)}")
            return None
