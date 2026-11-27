# NEXORA — Documentation Audit Report (M03 Customer Management & Dependencies)

- **Audit Subject:** Module M03 Customer Management & Cross-Module Dependencies
- **Audit Date:** 2026-11-27
- **Target Repository:** `Lalith-Manohar/LLM-Project1`
- **Active Branch:** `saisuhas`
- **HEAD Commit:** `1e2b986cee9888e1850fb86ab322afdfbe8a1434`
- **Audit Mode:** Read-Only Audit (Zero modifications to original project files)

---

## 1. Executive Summary

This documentation consistency audit evaluates the specification, architecture, relational schema, API contracts, feature registry, and cross-module governance of **Module M03: Customer Management** and its immediate operational dependents (`M04 Sales Management`, `M05 Order Management`, `M17 Billing & Finance`, `M18 Shipping & Delivery`, and supporting capabilities `SYS-01 Workspace Selection`, `SYS-02 Centralized History & Audit`).

The inspection covered the current active documents in the repository:
1. `AGENTS.md` (v2.2 Architecture & Governance Handbook)
2. `docs/DATABASE_SCHEMA.md` (v2.8 Relational Schema Specification, 41 Tables)
3. `docs/API_DOCUMENTATION.md` (v2.0 Verified & Planned REST API Specification)
4. `docs/FEATURES_STATUS.md` (v2.3 277-Feature Registry)
5. `docs/NEXORA — Technical Blueprint v1.0.md` (System Architecture & Module Reference v2.2)
6. `docs/NEXORA — Application Functionality & System Workflow Guide.md` (v1.0 Workflow Guide)
7. `docs/DEVELOPMENT_ROADMAP.md` (v2.0 Six-Phase Roadmap)
8. `docs/PROJECT_OVERVIEW.md` (v2.0 High-Level Implementation Snapshot)
9. Historical draft specifications: `docs/DATABASE_DESIGN.md`, `docs/PROJECT_SPEC.md`

All findings are classified strictly under the project audit categories.

---

## 2. Audit Findings by Category

### Finding F-01: Contradiction in Country Default Value (`'United Kingdom'` vs `'India'`)
- **Finding ID:** `F-01`
- **Category:** `2. Documentation contradiction`
- **Severity:** `Medium`
- **Affected Files & Sections:**
  1. `docs/NEXORA — Technical Blueprint v1.0.md` — Section 3.2 (Module 3: Customer Management), Subsection E (Database Requirements), Line 347.
  2. `docs/DATABASE_SCHEMA.md` — Section 3.2 (Group 2 — Catalog, UoM & Partners), `customers` DDL table definition, Line 470.
- **Existing Documented Statements:**
  - *Technical Blueprint v1.0.md (Line 347):*
    ```text
    country (NOT NULL DEFAULT 'United Kingdom')
    ```
  - *DATABASE_SCHEMA.md (Line 470):*
    ```sql
    country VARCHAR(100) NOT NULL DEFAULT 'India'
    ```
- **Why it is Incorrect / Inconsistent:**
  The Technical Blueprint states that `customers.country` defaults to `'United Kingdom'` (reflecting the historical UCI Online Retail II dataset's predominant location). However, `DATABASE_SCHEMA.md` (v2.8, line 470) specifies `DEFAULT 'India'`, aligning with the system-wide operational currency change to `INR` under `DDR-04` and `operational_settings.operational_currency = 'INR'`. These two authoritative documents directly contradict each other regarding the column default.
- **Supporting References:**
  - `docs/DATABASE_SCHEMA.md` v2.8 (line 470)
  - `docs/NEXORA — Technical Blueprint v1.0.md` (line 347)
  - `AGENTS.md` Section 7.4 (INR currency invariant)
- **Proposed Correction:**
  Harmonize `docs/NEXORA — Technical Blueprint v1.0.md` line 347 to specify `NOT NULL DEFAULT 'India'`, noting that historical UCI imports preserve `'United Kingdom'` in `uci_customer_ref` or order metadata.
- **Team Lead Approval Required:** Yes.

---

### Finding F-02: Column Name Discrepancy (`customer_code` vs `uci_customer_ref`)
- **Finding ID:** `F-02`
- **Category:** `2. Documentation contradiction`
- **Severity:** `Medium`
- **Affected Files & Sections:**
  1. `docs/NEXORA — Technical Blueprint v1.0.md` — Section 3.2 (Module 3: Customer Management), Subsection E, Line 347.
  2. `docs/DATABASE_SCHEMA.md` — Section 3.2, `customers` DDL table definition, Lines 459–480.
- **Existing Documented Statements:**
  - *Technical Blueprint v1.0.md (Line 347):*
    ```text
    Important Fields: id (PK), customer_code / optional uci_customer_ref (VARCHAR, nullable, indexed)...
    ```
  - *DATABASE_SCHEMA.md (Line 461):*
    ```sql
    uci_customer_ref VARCHAR(64) NULL,
    ```
- **Why it is Incorrect / Inconsistent:**
  The Blueprint mentions `customer_code / optional uci_customer_ref`, implying an operational business customer code could be distinct from `uci_customer_ref`. However, the approved 41-table DDL in `DATABASE_SCHEMA.md` contains only `uci_customer_ref VARCHAR(64) NULL` and no `customer_code` column exists. Developers implementing M03 could mistakenly add a redundant or required `customer_code` column, breaking compatibility with `DATABASE_SCHEMA.md`.
- **Supporting References:**
  - `docs/DATABASE_SCHEMA.md` v2.8 (Section 3.2, lines 460–480).
- **Proposed Correction:**
  Clarify in `docs/NEXORA — Technical Blueprint v1.0.md` that operational customers are keyed by auto-increment `id` (with optional `uci_customer_ref` for historical records), and remove the ambiguous `customer_code /` mention.
- **Team Lead Approval Required:** No (Clarification aligning with approved DDL).

---

### Finding F-03: Missing Customer API Schema Specifications in API_DOCUMENTATION.md
- **Finding ID:** `F-03`
- **Category:** `4. Missing documentation requirement`
- **Severity:** `High`
- **Affected Files & Sections:**
  - `docs/API_DOCUMENTATION.md` — Section 6.1 (Group 1 — Retail Foundation) and Section 7.
- **Existing Documented Statements:**
  - `docs/API_DOCUMENTATION.md` line 690 lists customer endpoints in the summary table:
    ```markdown
    | **M03 Customer Management** | `/api/v1/customers` | `GET /api/v1/customers` *(search/filter/paginate)*<br>`GET /api/v1/customers/{customer_id}`<br>`POST /api/v1/customers`<br>`PUT /api/v1/customers/{customer_id}`<br>`PATCH /api/v1/customers/{customer_id}/status` | `customers` | Deactivate-only if referenced by orders, transactions, or invoices |
    ```
  - However, unlike Procurement (`Section 7.1`), Fulfilment (`Section 7.2`), Finance (`Section 7.3`), and Audit (`Section 7.4`), there is no dedicated detailed section specifying the JSON request and response payloads, query parameters, or validation schemas for `/api/v1/customers`.
- **Why it is Incorrect / Inconsistent:**
  The summary table lists 5 endpoints for M03, but the exact Pydantic schema contracts (`CustomerCreateRequest`, `CustomerUpdateRequest`, `CustomerResponse`, `CustomerListResponse`) and filter parameters (`country`, `is_active`, `search`, `limit`, `offset`) are not defined in Section 7 of `API_DOCUMENTATION.md`. This leaves developers without explicit JSON schema guidance.
- **Supporting References:**
  - `docs/API_DOCUMENTATION.md` v2.0 (lines 690, 738–820)
  - `docs/FEATURES_STATUS.md` v2.3 (`FEAT-V2-M03-01` to `FEAT-V2-M03-08`)
- **Proposed Correction:**
  Add a dedicated Subsection `7.6 Customer Management API Specification` in `API_DOCUMENTATION.md` providing standard Pydantic schemas, validation rules (`422` on missing billing fields), and HTTP status responses.
- **Team Lead Approval Required:** Yes.

---

### Finding F-04: Outdated Historical Draft Reference to Authentication & `users` Table
- **Finding ID:** `F-04`
- **Category:** `3. Outdated reference`
- **Severity:** `Low`
- **Affected Files & Sections:**
  - `docs/DATABASE_DESIGN.md` — Section 1 and Section 2, Lines 10–34.
  - `docs/PROJECT_SPEC.md` — Section 4 (Authentication & RBAC).
- **Existing Documented Statements:**
  - *DATABASE_DESIGN.md (Lines 11, 26–33):*
    ```markdown
    USERS ||--o{ ORDERS : processes
    ### `users` (Authentication & RBAC)
    - `id` (BIGINT PK AUTO_INCREMENT)
    - `email` (VARCHAR 255 UNIQUE NOT NULL)
    - `hashed_password` (VARCHAR 255 NOT NULL)
    ...
    ```
- **Why it is Incorrect / Inconsistent:**
  `AGENTS.md` (Section 1, 2, and 4.2), `DATABASE_SCHEMA.md` (v2.8), and `Technical Blueprint v2.2` explicitly eliminated `users`, passwords, JWTs, and server-side RBAC in favor of non-authenticated UI workspace context (`SYS-01`, `DDR-10`). `DATABASE_DESIGN.md` is an unarchived legacy draft that directly contradicts the active architecture.
- **Supporting References:**
  - `AGENTS.md` Section 1, Section 2 ("Historical Drafts: non-authoritative wherever they conflict")
  - `docs/DATABASE_SCHEMA.md` v2.8 Section 1.1
- **Proposed Correction:**
  Prepend a prominent deprecation notice at the top of `docs/DATABASE_DESIGN.md` stating that it is superseded by `docs/DATABASE_SCHEMA.md` v2.8, and that `users` and RBAC are completely retired.
- **Team Lead Approval Required:** No.

---

### Finding F-05: Customer Walk-in / Guest Account Handling Specification Ambiguity
- **Finding ID:** `F-05`
- **Category:** `5. Potential issue requiring clarification`
- **Severity:** `Medium`
- **Affected Files & Sections:**
  1. `docs/NEXORA — Technical Blueprint v1.0.md` — Lines 334, 342, 348.
  2. `docs/DATABASE_SCHEMA.md` — Section 3.2 (`customers`) and Section 3.3 (`orders`).
  3. `docs/FEATURES_STATUS.md` — `FEAT-V2-M03-11`.
- **Existing Documented Statements:**
  - *Technical Blueprint (Line 342, 348):*
    `optional customer_type (registered / walk_in)` ... `Operational retail orders/invoices must link to a valid customers.id (including an explicit seeded Walk-In / Guest Customer or created customer record)`
  - *DATABASE_SCHEMA.md (Line 459–480):*
    The `customers` DDL table does not include a `customer_type` column.
- **Why it is Incorrect / Inconsistent:**
  The Blueprint mentions `optional customer_type ('registered' / 'walk_in')`, but `DATABASE_SCHEMA.md` does not have a `customer_type` column. Instead, `DATABASE_SCHEMA.md` specifies that `orders.customer_id` is `NOT NULL` with foreign key referencing `customers(id)`. This leaves ambiguity on how "Walk-in" counter customers are designated: whether by a designated seeded customer row (`customer_name='Walk-in Customer'`) or if a discriminator column was intended.
- **Supporting References:**
  - `docs/DATABASE_SCHEMA.md` v2.8 (Line 459–480, 515)
  - `docs/FEATURES_STATUS.md` (`FEAT-V2-M03-11`)
- **Proposed Correction:**
  Document explicitly in `docs/DATABASE_SCHEMA.md` (or module guidance) that walk-in sales use a standard seeded customer row (e.g., `id=1`, `customer_name='Walk-In Customer'`, `billing_address='Counter Sale'`, `city='Store Location'`, `postal_code='000000'`) rather than adding an unapproved `customer_type` column to the DDL.
- **Team Lead Approval Required:** Yes.

---

### Finding F-06: Customer Deactivation vs. Soft Delete Terminology Clarification
- **Finding ID:** `F-06`
- **Category:** `5. Potential issue requiring clarification`
- **Severity:** `Low`
- **Affected Files & Sections:**
  - `docs/API_DOCUMENTATION.md` — Line 690 ("Deactivate-only if referenced by orders, transactions, or invoices").
  - `docs/DATABASE_SCHEMA.md` — Line 1975 ("All referenced master entities... use soft-deactivation (is_active = FALSE)").
  - `docs/FEATURES_STATUS.md` — `FEAT-V2-M03-04`.
- **Existing Documented Statements:**
  - *API_DOCUMENTATION.md (Line 690):*
    "Deactivate-only if referenced by orders, transactions, or invoices"
- **Why it is Incorrect / Inconsistent:**
  The phrase "Deactivate-only if referenced by orders..." might imply that customers *not* referenced by orders can be hard-deleted via `DELETE /api/v1/customers/{id}`. However, `DELETE /api/v1/customers/{id}` is omitted from the API specification, and `DATABASE_SCHEMA.md` mandates soft-status toggles (`PATCH /api/v1/customers/{id}/status`, `is_active = FALSE`) across all master tables.
- **Supporting References:**
  - `docs/DATABASE_SCHEMA.md` Section 9.1 (Line 1975)
  - `docs/NEXORA — Technical Blueprint v1.0.md` (Line 358: "Create, Read, Update, Soft-Deactivate")
- **Proposed Correction:**
  Clarify in `docs/API_DOCUMENTATION.md` that hard `DELETE` is not supported on the customer resource; deactivation is always performed via `PATCH /api/v1/customers/{id}/status`.
- **Team Lead Approval Required:** No.

---

## 3. Review of All 12 M03 Feature IDs (`FEATURES_STATUS.md`)

| Feature ID | Feature Name | Documented Status | Consistency Review Result |
| :--- | :--- | :---: | :--- |
| `FEAT-V2-M03-01` | Create Customer | `PLANNED` | **Consistent.** Confirms strictly manual intake and prohibits automated scraping (`EXCL-08`). |
| `FEAT-V2-M03-02` | View Customer Directory | `PLANNED` | **Consistent.** Supports paginated search and detail retrieval. |
| `FEAT-V2-M03-03` | Edit Customer Details | `PLANNED` | **Consistent.** Strictly enforces snapshot immutability on child `invoices.billing_snapshot`. |
| `FEAT-V2-M03-04` | Deactivate / Reactivate Customer | `PLANNED` | **Consistent.** Toggles `is_active` to block new orders while preserving historical FKs. |
| `FEAT-V2-M03-05` | Contact Information Management | `PLANNED` | **Consistent.** Enforces clean phone and optional email validation. |
| `FEAT-V2-M03-06` | Billing Address Management | `PLANNED` | **Consistent.** Enforces mandatory street address, city, postal code, and country (`422` on omission). |
| `FEAT-V2-M03-07` | Shipping Address Management | `PLANNED` | **Consistent.** Enforces fallback to `billing_address` when `shipping_address` is null or empty. |
| `FEAT-V2-M03-08` | Customer Search and Filtering | `PLANNED` | **Consistent.** Parameterized query by name, phone, email, UCI ref, country, and active status. |
| `FEAT-V2-M03-09` | Customer Order History | `PLANNED` | **Consistent.** Read-only cross-reference to `orders.customer_id`. |
| `FEAT-V2-M03-10` | Customer Sales History | `PLANNED` | **Consistent.** Read-only cross-reference to `transactions.customer_id` and total invoiced spend. |
| `FEAT-V2-M03-11` | Guest & Historical Unidentified Customer Handling | `PLANNED` | **Potential Clarification (See F-05).** Supports nullable `uci_customer_ref` for ~25% UCI missing customer IDs. |
| `FEAT-V2-M03-12` | Contextual Inline Customer Lookup & Creation | `PLANNED` | **Consistent.** Used in Order/Invoice creation modals without losing line items. |

---

## 4. Cross-Module Consistency & Boundary Audit

1. **M04 Sales Management (`transactions`)**:
   - `transactions.customer_id` is nullable (`BIGINT UNSIGNED NULL`) to accommodate historical UCI imports where `Customer ID` is absent.
   - For operational sales linked to orders, constraint `chk_trans_order_requires_cust` mandates that `order_id IS NULL OR customer_id IS NOT NULL`. Composite FK `fk_trans_order_cust (order_id, customer_id)` guarantees consistency with `orders(id, customer_id)`.
   - **Result:** Fully consistent.
2. **M05 Order Management (`orders`)**:
   - `orders.customer_id` is strictly `NOT NULL` with `fk_orders_customer` referencing `customers(id)` with `ON DELETE RESTRICT`.
   - Inactive customers (`is_active = FALSE`) must be rejected at order draft/confirmation (`422` / `409`).
   - **Result:** Fully consistent.
3. **M17 Billing & Finance (`invoices`)**:
   - `invoices.customer_id` is `NOT NULL` referencing `customers(id)` with `ON DELETE RESTRICT`.
   - `invoices.billing_snapshot` stores a frozen JSON representation of customer billing details at invoice creation time.
   - Any subsequent edit to `customers` table does not rewrite `billing_snapshot` (`DDR-04`).
   - **Result:** Fully consistent.
4. **M18 Shipping & Delivery (`shipments`)**:
   - `shipments.shipping_address` is `TEXT NOT NULL`.
   - When drafting a shipment from an order, destination address is pulled from `customers.shipping_address` (falling back to `customers.billing_address`) and frozen onto `shipments.shipping_address`.
   - **Result:** Fully consistent.

---

## 5. Architecture & Governance Verification

- **Workspace Provenance (`DDR-10`, `SYS-01`)**:
  - `customers` table includes the standardized provenance triad: `selected_workspace`, `action_source`, and `operator_ref`.
  - No user authentication or server-enforced RBAC exists; workspace is passed via `X-NEXORA-Workspace`.
- **Audit Logging (`SYS-02`)**:
  - Customer profile mutations emit audit events: `CUSTOMER_CREATED`, `CUSTOMER_UPDATED`, `CUSTOMER_DEACTIVATED`.
- **Dataset Restriction (`EXCL-08`)**:
  - Customer directory records are created exclusively through manual operational entry or API endpoints. No scraping from UCI files.

---

## 6. Audit Conclusion

The database architecture, foreign-key invariants, and cross-module boundaries for M03 are sound and robust. The primary discrepancies found are documentation inconsistencies:
1. Contradictory `country` default (`'United Kingdom'` in Blueprint vs `'India'` in `DATABASE_SCHEMA.md`).
2. Ambiguous `customer_code` mention in Blueprint vs `uci_customer_ref` in DDL.
3. Absence of full JSON schema definitions for `/api/v1/customers` in `API_DOCUMENTATION.md`.
4. Walk-in guest account handling mechanism requiring team-lead signoff.
