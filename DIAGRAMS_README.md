# SEVA Arogya - Visual Documentation Guide

This document provides an overview of all the diagrams created for the SEVA Arogya system design.

## Available Diagrams

All diagrams are available in the [diagrams.md](diagrams.md) file. Below is a quick reference:

### 1. System Architecture Diagram
Shows the complete system architecture including:
- React Frontend (Doctor's Browser)
- Application Load Balancer
- AWS ECS Fargate (Flask Backend)
- AWS RDS (PostgreSQL Database)
- AWS AI Services (Transcribe, Comprehend, Translate, Cognito)
- AWS S3 Storage

### 2. Data Flow Diagram (DFD)
- **Level 0**: High-level view showing Doctor → System → Patient flow
- **Level 1**: Detailed process breakdown showing:
  - Voice Capture & Transcription
  - Structure & Extract Entities
  - Generate Suggestions
  - Review & Finalize
  - Generate PDF & Store

### 3. Sequence Diagram
Complete prescription flow showing interactions between:
- Doctor
- React App
- Application Load Balancer
- Flask API
- AWS Cognito
- AWS Transcribe
- AWS Comprehend Medical
- RDS Database
- S3 Storage

### 4. Database Schema Diagram
Entity-Relationship diagram showing:
- Doctors table
- Prescriptions table
- Prescription_Medications table
- Medications_Master table
- Audit_Logs table

### 5. AWS Infrastructure Diagram
Detailed AWS resource layout including:
- VPC with Public and Private Subnets
- Multi-AZ deployment
- Security Groups
- NAT Gateway
- All AWS managed services
- CI/CD Pipeline

### 6. Authentication Flow Diagram
Step-by-step authentication process:
- Login flow
- JWT token generation
- Token validation
- Token refresh mechanism
- API authorization

### 7. Voice Processing Flowchart
Complete voice-to-text processing flow:
- Audio capture
- Transcription via AWS Transcribe Medical
- Entity extraction via AWS Comprehend Medical
- Suggestion generation
- UI update

### 8. Prescription Generation Flowchart
End-to-end prescription creation:
- Data validation
- Language selection
- Translation (if needed)
- Database storage
- PDF generation
- S3 upload
- Download/Print options

### 9. Component Interaction Diagram
Detailed component-level architecture:
- Frontend components
- State management
- API service layer
- Backend middleware
- Service layer
- External services integration

### 10. Network Security Architecture
Security-focused view showing:
- VPC structure
- Security Groups configuration
- Inbound/Outbound rules
- NAT Gateway placement
- Private subnet isolation

### 11. Suggestion Engine Logic Flow
Algorithm flow for smart suggestions:
- Context analysis
- Historical data query
- Pattern matching
- Confidence scoring
- Filtering and ranking

## How to Use These Diagrams

1. **For Developers**: Use the Component Interaction and Sequence diagrams to understand code flow
2. **For DevOps**: Reference the AWS Infrastructure and Network Security diagrams for deployment
3. **For Database Admins**: Use the Database Schema diagram for data modeling
4. **For Product Managers**: Review the DFD and flowcharts to understand user journeys
5. **For Security Audits**: Examine the Authentication Flow and Network Security diagrams

## Integration with Design Document

The main design document has been updated to reference these diagrams. See:
- [design_with_diagrams.md](design_with_diagrams.md) - Complete design document with diagram references
- [diagrams.md](diagrams.md) - All visual diagrams
- [design.md](design.md) - Original design document

## Diagram Format

All diagrams are created using ASCII art for:
- Easy version control
- No external tool dependencies
- Clear text-based representation
- Universal accessibility

## Future Enhancements

Consider creating interactive versions using:
- Mermaid.js for web rendering
- PlantUML for more complex diagrams
- Draw.io for collaborative editing
- Lucidchart for presentation-ready versions
