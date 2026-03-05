## SEVA Arogya — Concrete Requirements for Implementation (Existing App Enhancement)

### 0) Key rules / decisions (confirmed)

* **Prescription states:** `Draft → InProgress → Finalized → Deleted`
* **Reject/Flag behavior:** If doctor rejects/flags a section, **allow immediate inline editing** in the same UI (this editing feature already exists—**reuse the existing section-edit UX**).
* **After Finalized:** prescription becomes **strict read-only** (no edits allowed).
* **CloudWatch logs:** build an **in-app log viewer UI** that fetches CloudWatch logs using config from `.env` (machine/instance/service ARN is available).
* **Soft delete restore:** **Doctor who created** the prescription can restore within 30 days.
* **PDF generation:** **on-demand** (generate when user clicks download/view). If performance becomes an issue later, we’ll switch to pre-generation.

---

## 1) Final Prescription UX (Bedrock output + section approvals)

### 1.1 Data source

* Final prescription content should be populated from **Bedrock output** (whatever existing bedrock payload structure is).
* Load Bedrock-generated content into the prescription’s sections when entering `InProgress` (or when doctor opens the finalization view).

### 1.2 UI modes

* **InProgress mode**

  * Sections are visible and have a per-section status:

    * `Pending` (default)
    * `Approved`
    * `Rejected/Flagged`
  * Doctor can:

    * Approve a section (locks it unless later rejected)
    * Reject/Flag a section → instantly enables edit mode for that section (reuse existing edit UI)
    * Edit section content and save → section returns to `Pending` (or `ReadyForApproval`) and must be approved again
* **Finalized mode**

  * Entire prescription becomes **read-only**.
  * Section approve/reject/edit controls are hidden/disabled.
  * PDF button remains available.

### 1.3 Approval gating

* Doctor can finalize only when:

  * All required sections are in `Approved`
  * Prescription is currently `InProgress`
* Finalize action sets:

  * `prescription.state = Finalized`
  * `finalized_at = now`
  * `finalized_by = doctor_user_id`

### 1.4 Thank you page after finalization

* After successful finalization:

  * Redirect to `/thank-you` (or equivalent)
  * Show **random message** from a predefined list (local constant or config)
  * Show CTA: “Back to Prescriptions”

---

## 2) Prescriptions List Page (table + filters + status visibility)

### 2.1 Route integration

* Home page actions:

  * “View all” → redirect to `/prescriptions`
  * “Search” → redirect to `/prescriptions` with query param prefilled (e.g. `?q=...`)

### 2.2 Table requirements

Create `/prescriptions` page with:

* Search box (debounced)
* Filters:

  * Doctor (dropdown; scope based on role)
  * Date range (created_at)
* Columns:

  * Prescription ID
  * Patient name / identifier (whatever exists)
  * Doctor
  * Created date/time
  * Overall prescription state (Draft/InProgress/Finalized/Deleted)
  * **Section/page statuses** (compact: icons or small pills per section)

### 2.3 Scoping rules

* **Doctor**: see own prescriptions by default (unless Hospital Admin wants broader view—see roles below).
* **Hospital Admin**: see all prescriptions within hospital.
* **Developer Admin**: see all prescriptions across hospitals.

---

## 3) Single Prescription View (audio, transcription, read-only render, delete/restore, PDF)

### 3.1 Must show

* Audio list:

  * Play controls
  * Each audio linked to a transcription block
* Transcription:

  * show stored transcript text
* Read-only “visual prescription view”:

  * Use same section renderer as edit mode but in read-only
* PDF:

  * Button: “Download PDF”
  * On click: call PDF generate endpoint (on-demand) → returns a file link or streams download

### 3.2 Delete / restore logic

* Delete button:

  * Confirmation modal required
  * Sets state to `Deleted` + `deleted_at = now` + `deleted_by`
  * Does NOT permanently remove DB row immediately
* Restore button:

  * Visible only if:

    * `state = Deleted`
    * `deleted_at <= 30 days ago`
    * current user is the **creator doctor** OR is Developer Admin (optional but recommended)
  * Restore sets state back to previous (`Draft` or `InProgress`—store `pre_deleted_state`), clears deleted fields

### 3.3 Permanent deletion after 30 days

* Implement a scheduled cleanup (cron/Lambda/worker depending on current infra):

  * Finds prescriptions with `state=Deleted` and `deleted_at < now - 30d`
  * Permanently deletes DB record (or archives to separate table)
  * Also delete associated audio/transcription/PDF objects from S3 if needed

---

## 4) Roles + Sidebar + Permissions

### 4.1 Roles

1. **DeveloperAdmin**
2. **HospitalAdmin** (may also be Doctor)
3. **Doctor**

### 4.2 Sidebar menu (mobile friendly)

* Implement responsive sidebar drawer for phone
* Menu items shown based on role:

  * Doctor:

    * Home
    * Create Prescription
    * Prescriptions
    * Profile (signature, name, specialty, availability display-only)
    * Dashboard (basic stats)
  * Hospital Admin:

    * All Doctor items
    * Hospital Settings (edit hospital + manage doctors)
  * Developer Admin:

    * Prescriptions (all)
    * Hospitals CRUD
    * CloudWatch Logs
    * (Optional) Users/role admin if already present

### 4.3 Permissions summary

* Doctor:

  * CRUD (create/update) prescriptions only if not Finalized and not Deleted
  * Can finalize only their own prescriptions
  * Can soft delete own prescriptions
  * Can restore own deleted prescriptions within 30 days
* Hospital Admin:

  * Same as Doctor + hospital-wide visibility and doctor management
* Developer Admin:

  * Full cross-hospital access + hospitals CRUD + logs viewer

---

## 5) Transition Overlay (branding)

* Add global route/page transition overlay:

  * Displays “SEVA Arogya” text in same font as login
  * Animates login icon + text (simple fade/slide/type effect acceptable)
  * Overlay shows on route change and fades when page is ready
* Keep it lightweight and consistent with existing theme.

---

## 6) CloudWatch Logs Viewer (in-app UI)

### 6.1 Data source

* Use ARN/service identifier from `.env` (already available).
* Implement backend endpoint that:

  * Calls CloudWatch Logs APIs (filter events)
  * Returns logs to frontend (paginated)
* Do NOT expose AWS credentials to browser.

### 6.2 UI requirements

* Page: `/logs`
* Show:

  * Date range selector (default last 24h or last 3 days)
  * Search filter (text contains)
  * List view with timestamp + message
  * Pagination / “Load more”
* Access: **DeveloperAdmin only**

---

## 7) PDF Generation (on-demand) — Lambda + S3

### 7.1 On-demand flow

* Button click → backend endpoint `/prescriptions/{id}/pdf`
* Endpoint triggers Lambda (or directly generates if that’s current architecture):

  * Fetch prescription data + hospital data
  * Render PDF using section-based renderer (dynamic)
  * Save to S3
  * Return signed URL (or stream response)

### 7.2 Hospital fields (minimum)

* `logo_url`
* `name`
* `address`
  Recommended additions:
* `phone`, `email`
* `registration_number` (if applicable)
* `website` (optional)

### 7.3 Dynamic section renderer requirement

* PDF layout must be section-driven:

  * Iterate through prescription sections in defined order
  * Render only existing sections
  * Each section has a title + content block
* Must support future new sections without rewriting the PDF engine.

---

## 8) Implementation guidance for the AI dev agent

* **Do not rewrite the whole app.** Extend existing patterns:

  * reuse existing API style, auth middleware, state management, components
  * reuse the existing “section edit” UI/logic for rejected/flagged sections
* Add new routes/pages minimally:

  * `/prescriptions`
  * `/prescriptions/:id`
  * `/thank-you`
  * `/logs` (DeveloperAdmin)
* Keep code consistent with existing folder structure and naming.

---

## 9) Data model expectations (add fields if missing)

Prescription:

* `state: Draft|InProgress|Finalized|Deleted`
* `created_by_doctor_id`
* `finalized_at`, `finalized_by`
* `deleted_at`, `deleted_by`, `pre_deleted_state`
* `sections: [{ key, title, content, status: Pending|Approved|Rejected }]`
* `bedrock_payload` (optional: raw response for audit)
* `hospital_id`

Audio/Transcription:

* store per prescription, listable and viewable

