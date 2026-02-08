# SEVA Arogya - Requirements Document

## Overview

SEVA Arogya is a voice-enabled clinical note capture and prescription generation system designed for Indian healthcare settings. The system allows doctors to dictate clinical notes, automatically structures them into prescriptions, and generates professional, multi-language prescription documents.

## Feature Breakdown

### Core Features

- **Voice-to-text clinical note capture (High Priority):** Allow doctors to narrate clinical notes and findings via voice. The system transcribes speech to text in real-time, tuned for medical terminology and Indian accents.

- **Automatic note structuring (High Priority):** Convert transcribed free-text into structured prescription elements. The system identifies and categorizes inputs into sections like Symptoms/Complaints, Vitals, Diagnosis, Medications (with dosage & duration), and Instructions.

- **Smart suggestion engine (High Priority):** Provide context-aware suggestions for medications or care instructions. Suggestions are based on learned doctor preferences and standard treatment guidelines, aiding doctors with auto-complete options (e.g., common dosages, follow-up advice).

- **Multi-language output (Medium Priority):** Support generating the prescription in multiple languages (English and local vernacular, e.g., Hindi). Ensures prescriptions can be understood by patients in their preferred language while maintaining medical accuracy.

- **Secure doctor login & profile (High Priority):** Implement a secure authentication system for doctors. Each doctor has a profile (name, qualifications, clinic details) and preferences (preferred language, frequently used medications templates) that personalize the experience and appear on prescriptions.

- **Standardized digital prescription (High Priority):** Output a well-formatted, legible prescription document (PDF or print) with a standard layout. The prescription includes all necessary sections, is easily readable (no handwriting issues), and can be printed or shared electronically.

### Nice-to-have Features

- **Voice commands & macros (Low Priority):** Enable voice-based commands (e.g., "next line", "new prescription") and reusable macros/templates for common text (like a predefined set of instructions or follow-up plan) to speed up note-taking.

- **Patient record integration (Future Scope):** Ability to pull in or store basic patient data (name, age, past history) and retrieve past prescriptions for a patient. Useful for follow-up visits and continuity of care.

- **Ambient conversation capture (Future Scope):** An ambient mode that listens to the entire doctor-patient conversation (with consent) and auto-generates a summary or SOAP note. This is a more advanced, continuous transcription feature beyond short-burst dictation.

- **EHR/Clinic system integration (Future Scope):** APIs or data export to integrate with hospital EMR systems. For example, pushing the structured prescription or notes into the hospital's electronic health record or billing system.

- **Regulatory compliance features (Future Scope):** Alignment with health data regulations (e.g., DISHA in India, HIPAA in future). This could include patient consent management, advanced audit trails, and data anonymization features for research use of aggregated data.

## Functional Requirements

### Voice Capture & Transcription

- The system shall capture audio from the doctor via the device microphone and convert it to text in near real-time. It must handle medical vocabulary (drug names, symptoms, common medical abbreviations) and diverse Indian English accents (as well as Hindi or other language input if spoken).

- The transcription shall be streamed or returned quickly (within a couple of seconds for a sentence). If transcription confidence is low for certain words, the system should mark them (e.g., underline or color) for the doctor to review.

### Automated Note Structuring

- The system shall analyze transcribed text to identify and extract key elements:
  - Patient information (name, age, etc.) if provided verbally
  - Clinical complaints/symptoms and their duration
  - Vital signs or examination findings (e.g., "BP 120/80, heart rate 80 bpm")
  - Diagnoses or assessments stated by the doctor
  - Medications prescribed, including dosage, frequency, and duration
  - Additional instructions or advice (e.g., lifestyle advice, next visit schedule)

- The system shall populate a digital prescription template with these extracted elements into predefined fields. Unrecognized or miscellaneous information can be placed in a "Notes" section for manual review.

### Editing and Confirmation

- The doctor shall be able to edit any transcribed text or structured field manually in the user interface. (For example, if a dosage or diagnosis is misheard, they can correct it.)

- The system shall update suggestions and structuring in real-time as text is edited or new voice input is added, without losing prior inputs.

- Before finalizing, the doctor shall be presented with a complete, structured prescription view to review and confirm that all details are correct.

### Smart Suggestions

- Based on the context of what's been transcribed (e.g., a diagnosed condition or mentioned symptom), the system shall offer non-intrusive suggestions:
  - **Medications:** e.g., if "acid reflux" is diagnosed, suggest an antacid or proton-pump inhibitor commonly used by the doctor or generally recommended
  - **Dosages & Frequency:** e.g., if "Paracetamol" is prescribed, suggest "500 mg twice a day for 3 days" if that's a typical regimen
  - **Instructions:** e.g., for an antibiotic, suggest "Take after food and complete the full course"

- Suggestions shall be presented in the UI in a way that the doctor can easily accept (one click to add) or ignore them. The system should learn from what the doctor does (e.g., if suggestions are frequently adjusted, adapt next time).

- The system shall allow the doctor to override or manually input anything - suggestions are aids but not forced. There should be no automatic addition without user confirmation.

### Multi-Language Output

- The system shall support producing the final prescription in English and at least one regional language (initially Hindi). The doctor can choose the output language (per prescription or as a profile default).

- If a regional language is chosen, the system shall translate the structured content (like the symptom descriptions and instructions) into that language's script, while keeping medical terms (drug names, etc.) consistent (not erroneously translated).

- The interface for the doctor can remain in English (for now) even if output is translated, but future enhancement may allow the doctor to dictate or see the interface in vernacular language as well.

### User Authentication & Profile Management

- The system shall require doctors to create an account and log in securely before accessing patient prescription features. Account creation includes capturing essential details (name, email/phone, professional ID or registration number, clinic/hospital name).

- Passwords shall be stored securely (hashed); the system should enforce strong passwords or support OTP-based login if feasible. Multi-factor authentication is a nice-to-have for added security, but not required in MVP.

- Each doctor shall have a profile where they can:
  - Set their preferred prescription language
  - Configure header info that appears on prescriptions (like their qualifications, clinic address, signature)
  - View or edit lists of "favorite" or frequently used medications/instructions to further customize suggestions

- The system shall only allow authenticated users (doctors) to access their own data. There is no public or patient-facing login in this phase.

### Prescription Output & Sharing

- Upon confirmation, the system shall generate a final prescription document (PDF format) that the doctor can download or print. It should follow a standard layout:
  - Header with clinic and doctor info, date, patient name (if provided)
  - Clearly labeled sections for Findings/Complaints, Diagnosis, Medications (with dosage & duration), and Instructions/Advice
  - Footer with any disclaimers or follow-up info

- The PDF shall be properly formatted for A4 paper (common prescription print size in clinics). If content is too long, it should gracefully span multiple pages while repeating necessary headers.

- The system shall provide an option to directly print the prescription or save it. If internet connectivity allows, a share option (e.g., email to patient or WhatsApp link) is a nice-to-have, but not core in MVP.

- A copy of the prescription data shall be saved in the system (database) under the doctor's account for future reference or audit.

## Non-Functional Requirements

### Performance

- The system shall be optimized for low latency. Transcription of a typical sentence (5-10 seconds of speech) should be returned and displayed in under 2 seconds on average on a good connection. UI interactions (like clicking buttons, loading the app) should feel responsive (< 300ms for any local action).

- The end-to-end process from dictation to final PDF generation should be fast enough to fit within a standard short consultation (~2-3 minutes for note-taking). The system should not introduce significant delays in a fast-paced OPD workflow.

- The system shall scale to handle ~50 concurrent active users (doctors dictating) initially, with design considerations to easily scale to hundreds of concurrent users as adoption grows. Adding more users should linearly scale the backend and not degrade individual performance.

### Reliability & Availability

- The system shall be highly available during clinic hours. Target uptime is 99.5% or higher, especially during 9am-6pm typical OPD times. Maintenance or updates should be scheduled off-hours or with zero-downtime deployment strategies.

- In case of a failure (e.g., the transcription service is unreachable, or the backend crashes), the system should fail gracefully:
  - The UI should show an error message with guidance (e.g., "Unable to transcribe at the moment, please retry" or fallback to manual typing)
  - Partial data should not be lost if possible - e.g., keep already transcribed text visible if a later step fails

- The system shall ensure data durability for saved prescriptions (using reliable storage). Once a prescription is saved or printed, it should be retrievable later (no data loss).

### Security

- All communication shall be encrypted (HTTPS for all API calls). Users' credentials and tokens must never be sent or stored in plaintext.

- The system shall enforce access controls such that one doctor cannot access another doctor's prescriptions or data. Each API request will be authenticated and scoped to the requesting user's context.

- Sensitive personal health information (PHI) is minimal in this system (mainly what's on a prescription), but whatever is stored (patient name, diagnoses, medications) shall be encrypted at rest in the database and in backups.

- The system shall log access and key actions (audit log) for security monitoring. For example, log when a user logs in, when a prescription is created, or if any data export occurs.

- Initial compliance with Indian IT security best practices and anticipation of future healthcare regulations is expected. While not fully HIPAA/DISHA compliant in MVP, the architecture should allow retrofitting compliance (e.g., consent capture, detailed audit trails, data retention policies) with minimal redesign.

### Usability

- The application shall have an intuitive UI/UX tailored for doctors who may not be very tech-savvy:
  - Minimal clicks: e.g., one tap to start/stop recording voice
  - Clear visualization of structured fields (maybe form-like or sections) so doctors can quickly verify auto-filled content
  - Legible fonts and adequate text sizes on the prescription preview
  - Support for quick corrections: editing text should be as simple as typing, with no complex steps

- The interface shall be responsive to different device types (desktop in clinics, tablets, possibly mobile phones in future). However, primary target is a desktop or laptop with Chrome/Firefox browsers.

- The system shall provide feedback to the user during processing (like a spinner or progress bar during transcription) so the doctor knows the system is working and not stuck.

### Maintainability & Extensibility

- The codebase shall be organized into clearly separated modules (front-end, back-end API, voice processing, suggestion engine, etc.). This modularity makes it easier to update one component (like swap out the STT engine or update the suggestion algorithm) without affecting others.

- The system should allow updating the medical vocabulary or adding new templates without a full redeploy (for example, via configuration files or database entries). For instance, adding a new common medication name should be possible via updating a list rather than changing code.

- Documentation shall be maintained for the system's API and data models, enabling new developers to understand and contribute with minimal onboarding time.

- The system should have automated tests for critical components (transcription parsing, suggestion logic, etc.) to facilitate safe refactoring and updates. This ensures maintainers catch regressions early.

- Extensibility: Adding new languages or integrating new services (like a different speech recognition API or EHR integration) should be feasible by adding new modules or adapters rather than rewriting core logic.

### Scalability

- The design shall be cloud-native to allow horizontal scaling. For example, multiple instances of the transcription-processing service can run in parallel to serve more users. There should be no single bottleneck that limits throughput (stateful components are minimized).

- The architecture should use managed services (where possible) that automatically scale (e.g., AWS's auto-scaling for containers, fully managed databases that handle load). This reduces the need for manual intervention when usage spikes.

- For future scale, the system should support multi-clinic or multi-institution deployments. Initially one environment will serve all users, but design decisions (like unique identifiers, tenancy isolation) should allow partitioning data by clinic or region if needed.

### Cost Constraints

- The solution shall be cost-effective to operate for a small clinic setting. Using pay-per-use services (like paying per transcription minute) is acceptable in trade for zero upfront infrastructure, but costs need monitoring. There should be options to configure limits (e.g., maximum transcription time per user per month) to control expenses in early deployments.

- Development effort should focus on core differentiators (the voice and AI features) while relying on existing platforms for commodity features (auth, DB). This ensures we deliver value quickly without reinventing the wheel.

- As usage grows, the team should regularly review the AWS resource usage and see if any optimizations or reserved instances make sense to reduce ongoing costs. The architecture should allow substituting expensive components if needed (for instance, switch to an open-source speech model on our servers if that becomes cheaper at scale).

- There is an implicit cost in data usage as well (bandwidth for audio upload/download). The system should be mindful of that by sending only necessary data (e.g., compress audio, avoid sending audio at an extremely high bitrate).

## User Stories

### Primary User - Doctor

1. **As a busy doctor in an OPD, I want to quickly record patient findings and prescriptions by speaking, so that I spend less time writing and maintain eye contact with my patient.**
   - Acceptance Criteria: After speaking a sentence, the text appears on my screen correctly. I can do this in front of the patient naturally, and it doesn't slow me down compared to writing.

2. **As a doctor, I want the system to automatically organize my spoken notes into a neat prescription format, so that I don't have to manually structure or rewrite anything before handing it to the patient.**
   - Acceptance Criteria: When I finish dictating, the prescription fields (like diagnosis, medications) are automatically filled in appropriately. The final document looks professional without my manual formatting.

3. **As a doctor, I want the assistant to suggest common medications or doses based on what I've said, so that I save time and don't forget standard care practices.**
   - Acceptance Criteria: If I diagnose a common condition (e.g., hypertension), the system shows me a couple of medication options or guidelines (like typical drugs/dosages) which I can accept with one click. The suggestions are relevant and help me complete the prescription faster.

4. **As a doctor concerned about errors, I want to review and edit the output easily, so that I remain in control of the final prescription content and ensure 100% accuracy.**
   - Acceptance Criteria: I can click on any part of the generated text to correct it (for example, fix a misspelled drug name or adjust a dose). The system updates the final prescription immediately with my changes and doesn't revert them.

5. **As a multilingual doctor, I want to give some patients a prescription in their local language (e.g., Hindi), so that they can read and understand it better.**
   - Acceptance Criteria: I can select "Hindi" as output language, and the prescription (except drug names) appears in Hindi script accurately. If I switch back to English, it toggles back. The patient section (like instructions) is clearly understandable in the chosen language.

6. **As a doctor, I want my prescription outputs to look uniform and clear, with my letterhead and date, so that they have a professional appearance and can be easily referenced later.**
   - Acceptance Criteria: The PDF output includes my pre-set letterhead information (name, clinic, etc.) at the top, the date of visit, and is formatted cleanly (easy to read font, proper alignment). When I print it, it fits on one page and looks like a standard prescription format.

### Secondary/Future Stories

7. **As a patient receiving the prescription, I want it to be typed and clearly printed, possibly in my language, so that I can follow the instructions correctly and not worry about misreading the doctor's handwriting.**
   - Acceptance Criteria: (From the patient perspective) The prescription I get is easy to read. If it's in English and I'm not comfortable, the doctor can give it in my language. Key details like medicine names and timing are unambiguous.

8. **As a clinic admin or IT support, I want to ensure the doctors' data and patient info are secure and backed up, so that we comply with guidelines and can recover information if needed.**
   - Acceptance Criteria: There is a secure login for each doctor; if a doctor leaves, their account can be deactivated. All prescription records are stored securely. In case of any audit or medicolegal need, an authorized person can retrieve a log of what was prescribed, when, and by whom (with proper permission).

9. **As a future product owner, I want to easily update the system's drug database or add new features, so that the product stays up-to-date with medical advancements and user needs.**
   - Acceptance Criteria: (From development perspective) The system's architecture and documentation make it straightforward to expand (e.g., adding a new language pack or integrating a new AI model). Changes in features are reflected in the requirements and design docs, and there's an automated process or clear guidelines to do so.

## Acceptance Criteria

### Voice Transcription

- **Accuracy:** For a given test set of medical phrases and prescriptions dictated by a doctor, the transcription service should correctly transcribe at least 90% of the words overall. Critical medical terms (drug names, symptom names) should be nearly perfect (e.g., >98% for a known list of common terms). Any uncertain words should be flagged to draw the doctor's attention.

- **Speed:** In usability tests, doctors should observe the transcribed text appear within ~2 seconds after finishing a sentence. (We measure from end of speech audio to text displayed.) The system should handle at least 20 short dictations per minute for a single user without queue delays (since a doctor might dictate multiple short sentences quickly).

- **Robustness:** If background noise or accent causes a transcription error, the system should still capture some output rather than failing silently. It might mis-recognize a word, but it should never drop the entire sentence. In cases of low confidence, it could display a "?" or highlight to indicate the need for verification.

- **Medical terminology:** When tested with a list of 100 common medications and medical terms (especially India-specific ones), the system should transcribe at least 95 of them correctly in context. (e.g., "Paracetamol", "Metformin", "Blood pressure", common units like "mg/ml", etc., are handled correctly by the voice engine.)

### Structured Data Extraction

- **Field Population:** Given a complex sentence or sequence (e.g., "Patient has fever for 3 days and cough. On exam, temp 101F. Impression: viral fever. Plan: Tab Paracetamol 500 mg twice daily for 3 days."), the system should fill:
  - Symptoms: "fever (3 days)", "cough"
  - Vitals: "Temperature 101°F"
  - Diagnosis: "Viral fever"
  - Medications: "Paracetamol 500 mg - 1 tablet twice daily - 3 days"
  - Instructions: (none explicitly in example, but if absent, section can be blank or omitted)
  - Patient Name: (left blank if not provided; not inferable from this input)

- **Accuracy of Extraction:** In a controlled test of 10 sample prescriptions dictated, at least 9 should have all key fields correctly identified and placed. Minor mistakes (like categorizing something as instruction vs medication note) are acceptable if easily fixable by the doctor, but critical info (medication name, dose) must consistently land in the right field.

- **Handling Unknowns:** If the system cannot confidently categorize a piece of info, it should place it in a general note section or prompt the user. Acceptance if, in edge cases, no information is lost - everything the doctor said is somewhere on the draft prescription (even if not perfectly classified, the doctor can see it and adjust).

- **Manual Override:** Verify that if a doctor edits the structured fields manually, the system does not re-overwrite those with its own suggestions. For example, if the doctor changes the dosage from what was auto-filled, the change persists. The acceptance test: doctor edits a field and continues dictation; the previously edited field remains as edited unless the doctor explicitly changes it again.

### Suggestion Engine

- **Relevance:** In at least 8 out of 10 test scenarios, the suggestions offered must be contextually relevant. (Test scenarios example: for "Type 2 Diabetes" diagnosis, suggestions include common diabetes meds like Metformin or dietary advice; for "fever", suggestion might be Paracetamol if not already given, etc.) If a suggestion appears that is clearly unrelated to the case, that's a fail.

- **Non-intrusive UI:** During a user test, doctors report that the suggestions are helpful and not annoying. Acceptance if the suggestion interface (maybe a dropdown or small list) does not obstruct the doctor's view and can be ignored without additional clicks. For instance, if the doctor chooses to ignore them, they can just continue without dismissing popups.

- **Adapting to Doctor:** If a doctor repeatedly prefers a certain medication for a condition (e.g., always prescribes Drug A for hypertension instead of the suggested Drug B), the system should learn this. After, say, 5 such occurrences, acceptance criteria is that Drug A becomes the first suggestion next time that condition is encountered. We can simulate this by feeding multiple similar inputs and checking the suggestion order.

- **Opt-out:** Ensure that turning off suggestions (if a feature toggle exists) indeed stops showing suggestions. Acceptance: when a "Suggestions" setting is off, the same dictation input yields no suggestions in the UI, only the raw transcription and structuring.

### Prescription Document Output

- **Completeness:** Every structured field that has data should appear in the PDF. For example, if "Follow-up after 7 days" was an instruction, it should be present in the printed instructions section. Acceptance: Cross-verify with test data that nothing captured is missing on the PDF.

- **Format Consistency:** The PDF layout should match a predefined template. Acceptance: a review of the PDF output shows consistent fonts, spacing, and section headers. If two different doctors use it, their outputs differ only in content and header (each doctor's name/clinic), but the style remains uniform (unless customized).

- **Legibility:** The printed prescription must be easily readable:
  - Font size >= 11pt for body text
  - Important fields labeled (e.g., "Diagnosis:" in bold followed by the text)
  - Medication entries formatted clearly (one per line or in a table with columns for dosage and duration)
  - In user feedback, at least 90% of doctors and test patients should agree the printout is clear and professional

- **Language Accuracy:** If a prescription is output in Hindi (or another language), have a bilingual expert confirm that the translation of instructions and common terms is correct and patient-friendly. Acceptance: In a sample of 5 prescriptions translated to Hindi, the medical content remains correct (no mistranslation of critical terms) and the grammar/spelling in Hindi is correct in at least 4 out of 5. Any errors identified are added to a glossary to prevent future mistakes (continuous improvement).

- **File Delivery:** Generating the PDF should not take more than a couple of seconds. When tested on a sample prescription, the system produces the PDF and initiates download < 3 seconds after clicking "Finalize". The PDF file size should be reasonable (e.g., <200KB for a one-page prescription without images). Printing the PDF on a standard printer yields the expected result (sections not cut off, margins correct).

### Authentication & Security

- **Account Creation:** New user registration with valid details results in an account and immediate ability to use the system (if email verification is required, we'll simulate a verified state for testing). Attempting to register with an already used email or weak password is gracefully handled (error message given). Acceptance if validation messages appear for invalid inputs and a new user can successfully sign up and log in.

- **Login:** Using the correct credentials lets the user in (token issued, interface accessible). Using wrong credentials (wrong password) shows an appropriate error and does not log them in. After 5 failed attempts, if we have a lockout policy, it triggers (nice-to-have). Acceptance: test login with correct and incorrect credentials, behavior is as expected; ensure no information leakage in error (e.g., don't say "user not found vs wrong password" differently).

- **Auth Token Usage:** After login, the user's session token (JWT) must be required for accessing APIs. Test by calling an API endpoint (like transcription) without a token or with an invalid token - the result should be a 401 Unauthorized error. Acceptance if the system rejects unauthorized calls and allows authorized ones. Also, ensure that a valid token from one user cannot access another user's data (simulate by substituting an ID in an endpoint if any are exposed in URLs, or by using another user's token).

- **Data Isolation:** Create two test doctor accounts. Doctor A creates a prescription. Doctor B (with their credentials/token) tries to fetch or view anything of Doctor A (if such API exists, or by ID guessing). Acceptance: Doctor B is denied access or gets no data of A. Essentially, verify that each doctor's records are scoped to their identity.

- **Encryption & Privacy:** Verify that the database entries for sensitive fields (like patient name, prescription details) are stored encrypted (this might be a configuration - for example, RDS encryption at rest is on, which we assume in design). Also verify that any cached files (if any) are cleared or stored securely. This might be more of a design check than runtime test; acceptance is a checklist verification that all storage is configured to be encrypted and no sensitive data is written to logs in plaintext.

- **Logout:** Logging out in the UI should remove the session. After logout, using the same token should fail. Acceptance: After a logout action, attempt an API call with the old token results in a 401 (if token was revoked or just expired). If using short-lived tokens without explicit revocation, ensure that after, say, 1 hour, the token naturally expires and can't be used (and the front-end requires a fresh login).

### Performance & Load Testing

- **Concurrent Usage:** Simulate 20 doctors using the system simultaneously (20 audio transcriptions nearly at the same time). All should receive responses within acceptable latency (maybe it goes from 2s to 3s under load, which might be okay). Acceptance if the system remains responsive and no requests time out or fail under this load. Further test at 50 concurrent to evaluate headroom (this might be for future scaling criteria).

- **Throughput:** Over an hour of heavy usage (e.g., 100 prescriptions created in an hour by various test scripts), the system should not crash or leak resources (memory/CPU within container limits). Acceptance via monitoring: no memory leaks observed, CPU stays within reasonable % (e.g., < 70% on average under peak), and the auto-scaling (if enabled) kicks in appropriately to handle load.

- **Recovery:** Manually simulate a failure scenario, such as the connection to the speech service failing mid-request or the database going down briefly. The system should handle gracefully (return error to user, not crash) and recover when the service comes back (next request succeeds). Acceptance if after a transient failure, the system continues to work normally without requiring restart.
