# NEXORA — Proposed Documentation Corrections (M03 Customer Management)

- **Audit Reference:** `documentation_audit/DOCUMENTATION_AUDIT_REPORT.md`
- **Audit Date:** 2026-11-27
- **Notice:** This document contains **proposed replacement text only**. In accordance with audit restrictions, **no changes have been applied to original project documents**.

---

## 1. Summary of Proposed Corrections

| Finding ID | Target Document | Target Section / Heading | Severity | Approval Required |
| :---: | :--- | :--- | :---: | :---: |
| **F-01** | `docs/NEXORA — Technical Blueprint v1.0.md` | Section 3.2 (Module 3: Customer Management), Subsection E | Medium | Yes |
| **F-02** | `docs/NEXORA — Technical Blueprint v1.0.md` | Section 3.2 (Module 3: Customer Management), Subsection E | Medium | No |
| **F-03** | `docs/API_DOCUMENTATION.md` | Section 7 (Planned Operational REST API Specifications) | High | Yes |
| **F-04** | `docs/DATABASE_DESIGN.md` | Top of file / Notice block | Low | No |
| **F-05** | `docs/NEXORA — Technical Blueprint v1.0.md` | Section 3.2 (Module 3: Customer Management), Subsection E | Medium | Yes |
| **F-06** | `docs/API_DOCUMENTATION.md` | Section 6.1 (Group 1 — Retail Foundation Summary Table) | Low | No |

---

## 2. Side-by-Side Proposed Text Replacements

### Correction C-01 & C-02 & C-05: Technical Blueprint v1.0.md — Module 3 Database Requirements

- **File Path:** `docs/NEXORA — Technical Blueprint v1.0.md`
- **Section:** `Module 3: Customer Management` $\rightarrow$ `E. Database Requirements` (Lines 345–349)
- **Rationale:**
  - Harmonizes default country to `'India'` matching `DATABASE_SCHEMA.md` v2.8 (`F-01`).
  - Replaces ambiguous `customer_code / optional uci_customer_ref` with exact schema column `uci_customer_ref` (`F-02`).
  - Clarifies that walk-in sales use a standard seeded customer row (`customer_id = 1`) rather than introducing an unapproved `customer_type` column (`F-05`).

#### Original Text (Lines 345–349):
```markdown
#### E. Database Requirements
- **Entities:** `customers`.
- **Important Fields:** `id` (PK), `customer_code` / optional `uci_customer_ref` (VARCHAR, nullable, indexed), `customer_name` (VARCHAR, NOT NULL), `phone`, `email`, `billing_address` (TEXT), `shipping_address` (TEXT, nullable — defaults to billing if omitted), `city`, `state`, `postal_code`, `country` (NOT NULL DEFAULT `'United Kingdom'`), `is_active` (BOOLEAN DEFAULT TRUE), `created_at`, `updated_at`.
- **Guest / Historical Handling:** Operational retail orders/invoices must link to a valid `customers.id` (including an explicit seeded `Walk-In / Guest Customer` or created customer record); historical imported UCI `transactions` retain optional string `uci_customer_ref` (allowing `NULL` matching raw UCI missing rates) without polluting newly entered customer address books.
```

#### Proposed Replacement Text:
```markdown
#### E. Database Requirements
- **Entities:** `customers`.
- **Important Fields:** `id` (BIGINT UNSIGNED AUTO_INCREMENT PK), `uci_customer_ref` (VARCHAR(64), nullable, indexed for historical UCI trace), `customer_name` (VARCHAR(150), NOT NULL), `phone` (VARCHAR(50), nullable), `email` (VARCHAR(255), nullable), `billing_address` (TEXT, NOT NULL), `shipping_address` (TEXT, nullable — defaults to billing if omitted), `city` (VARCHAR(100), NOT NULL), `state` (VARCHAR(100), nullable), `postal_code` (VARCHAR(20), NOT NULL), `country` (VARCHAR(100), NOT NULL DEFAULT `'India'`), `is_active` (BOOLEAN NOT NULL DEFAULT TRUE), `selected_workspace`, `action_source`, `operator_ref`, `created_at`, `updated_at`.
- **Guest / Historical Handling:** Operational retail orders/invoices must link to a valid `customers.id` (counter sales link to a designated seeded customer record such as `id=1, customer_name='Walk-In Customer'`); historical imported UCI `transactions` retain optional string `uci_customer_ref` (allowing `NULL` matching raw UCI missing rates) without polluting newly entered customer address books.
```

---

### Correction C-03: API_DOCUMENTATION.md — Add Section 7.6 Customer Management API Specification

- **File Path:** `docs/API_DOCUMENTATION.md`
- **Section:** Insert as `Section 7.6 Customer Management API Specification` immediately following `Section 7.5 UoM API Planning`
- **Rationale:** Resolves `F-03` by providing explicit Pydantic request/response schemas, validation rules, query parameters, and error status codes for `/api/v1/customers`.

#### Original Text:
*(None — detailed customer API contract was missing from Section 7)*

#### Proposed Replacement Text:
```markdown
### 7.6 Customer Management API Specification (`M03`)

Designed around **`EXCL-08`** (manual intake only; zero UCI address scraping) and standard provenance tracking (`customers` table):

#### 1. Customer Endpoints
1. `GET /api/v1/customers`
   - **Query Parameters:**
     - `search`: `Optional[str]` (filters case-insensitively across `customer_name`, `email`, `phone`, and `uci_customer_ref`)
     - `country`: `Optional[str]` (filters exact country match)
     - `is_active`: `Optional[bool]` (filters active/inactive status)
     - `limit`: `int = 50` (`1 <= limit <= 200`)
     - `offset`: `int = 0` (`offset >= 0`)
   - **Response (`200 OK`):**
     ```json
     {
       "items": [
         {
           "id": 1,
           "uci_customer_ref": null,
           "customer_name": "Acme Retail Ltd",
           "phone": "+91 9876543210",
           "email": "contact@acmeretail.in",
           "billing_address": "123 MG Road, Suite 400",
           "shipping_address": "123 MG Road, Suite 400",
           "city": "Bengaluru",
           "state": "Karnataka",
           "postal_code": "560001",
           "country": "India",
           "is_active": true,
           "created_at": "2026-11-27T10:00:00Z",
           "updated_at": "2026-11-27T10:00:00Z"
         }
       ],
       "total": 1,
       "limit": 50,
       "offset": 0
     }
     ```

2. `GET /api/v1/customers/{customer_id}`
   - **Response (`200 OK`):** Single `CustomerResponse` object.
   - **Errors:** `404 Not Found` if customer does not exist.

3. `POST /api/v1/customers`
   - **Headers:** Optional `X-NEXORA-Workspace`, `X-Correlation-ID`.
   - **Request Payload (`CustomerCreate`):**
     - Mandatory: `customer_name` (str, 1..150), `billing_address` (str), `city` (str, 1..100), `postal_code` (str, 1..20).
     - Optional: `shipping_address` (str, defaults to `billing_address` if omitted or null), `phone` (str, 1..50), `email` (EmailStr), `state` (str, 1..100), `country` (str, default `'India'`), `uci_customer_ref` (str), `operator_ref` (str).
   - **Validation Rules:** Incomplete mandatory billing fields return **`422 Unprocessable Content`**.
   - **Response (`201 Created`):** `CustomerResponse` object. Emits `CUSTOMER_CREATED` audit log.

4. `PUT /api/v1/customers/{customer_id}`
   - **Request Payload (`CustomerUpdate`):** Partial or full updates to address and contact details.
   - **Business Rules:** Updating customer profile updates future orders/shipments but **never modifies** frozen `billing_snapshot` records on past invoices (`DDR-04`).
   - **Response (`200 OK`):** Updated `CustomerResponse`. Emits `CUSTOMER_UPDATED` audit log.
   - **Errors:** `404 Not Found`, `422 Unprocessable Content`.

5. `PATCH /api/v1/customers/{customer_id}/status`
   - **Request Payload:** `{"is_active": false}`
   - **Business Rules:** Soft-deactivates customer. Deactivated customers cannot be selected on newly created orders or invoices. Historical records and foreign keys remain preserved.
   - **Response (`200 OK`):** Updated `CustomerResponse` with `is_active` reflected. Emits `CUSTOMER_DEACTIVATED` audit log.
   - **Errors:** `404 Not Found`.
```

---

### Correction C-04: DATABASE_DESIGN.md — Add Prominent Deprecation Banner

- **File Path:** `docs/DATABASE_DESIGN.md`
- **Section:** Top of document (Lines 1–5)
- **Rationale:** Resolves `F-04` by clarifying that `DATABASE_DESIGN.md` is an unmaintained legacy draft from Milestone 1 and must not be used for implementation.

#### Original Text (Lines 1–4):
```markdown
# NEXORA – Database Design Specification (MySQL)

> **Notice:** This document defines the planned relational schema for future milestones. Database integration is not yet active in Milestone 1.
```

#### Proposed Replacement Text:
```markdown
# NEXORA – Database Design Specification (MySQL) [HISTORICAL DRAFT — DEPRECATED]

> [!WARNING]
> **HISTORICAL SPECIFICATION ONLY:** This document is an archived early design draft and is **non-authoritative**.
> All live relational design, schemas, and invariants are governed strictly by [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) *(Version 2.8, 41 InnoDB tables)*.
> Capabilities shown here such as `users` table and password authentication are **completely retired** under Technical Blueprint v2.2 and `AGENTS.md`.
```

---

### Correction C-06: API_DOCUMENTATION.md — Clarify Deactivation in Group 1 Summary Table

- **File Path:** `docs/API_DOCUMENTATION.md`
- **Section:** Section 6.1 (Group 1 — Retail Foundation Table, Line 690)
- **Rationale:** Resolves `F-06` by removing misleading "Deactivate-only if referenced" text to make clear that hard deletion is never supported for customer master records.

#### Original Text (Line 690):
```markdown
| **M03 Customer Management** | `/api/v1/customers` | `GET /api/v1/customers` *(search/filter/paginate)*<br>`GET /api/v1/customers/{customer_id}`<br>`POST /api/v1/customers`<br>`PUT /api/v1/customers/{customer_id}`<br>`PATCH /api/v1/customers/{customer_id}/status` | `customers` | Deactivate-only if referenced by orders, transactions, or invoices |
```

#### Proposed Replacement Text:
```markdown
| **M03 Customer Management** | `/api/v1/customers` | `GET /api/v1/customers` *(search/filter/paginate)*<br>`GET /api/v1/customers/{customer_id}`<br>`POST /api/v1/customers`<br>`PUT /api/v1/customers/{customer_id}`<br>`PATCH /api/v1/customers/{customer_id}/status` | `customers` | Soft-deactivation only (`is_active = FALSE`); hard delete is prohibited |
```
