# Inventory App Repo Context For Android Rebuild

## Purpose

This document captures what the current Streamlit application already does, how the data is stored, what business rules exist in code, and what should be carried forward into the Android application.

The repo is a local-first small-business inventory and billing system built around three core areas:

1. Inventory management
2. Invoice generation
3. Seller management / khata (credit, payments, history)

Analytics and reporting already exist, but they look like a later-phase feature compared to the three core workflows.

## High-Level Repo Summary

Tech stack in current app:

- UI: Streamlit
- Database: SQLite (`inventory.db`)
- Data processing: pandas
- PDF/invoice rendering: reportlab
- Charts/analytics: plotly
- OCR / import helpers: `pytesseract`, `pdfplumber`, `openpyxl`
- Backup: local copy + optional Google Drive upload

Main entrypoint:

- `main.py`

Primary screens/pages:

- `pages/add_items.py`
- `pages/manage_items.py`
- `pages/invoice_generation.py`
- `pages/manage_sellers.py`
- `pages/reports.py`
- `pages/company_settings.py`

Shared utilities:

- `utils/db_manager.py`
- `utils/backup_manager.py`
- `utils/logger.py`
- `utils/validators.py`
- `schema.sql`

Other notable files:

- `backup.py`
- `requirements.txt`
- `invoices/` contains previously generated PDF invoices from older flows
- `logs/` contains application logs

## Current Navigation / Product Shape

The app sidebar exposes these sections:

1. Create Invoice
2. Add New Items
3. Inventory Management
4. Customer Database
5. Business Analytics
6. Business Settings

Internal mapping:

- `Create Invoice` -> invoice generation
- `Add New Items` -> add items
- `Inventory Management` -> manage items
- `Customer Database` -> seller/khata management
- `Business Analytics` -> reports
- `Business Settings` -> company profile + invoice header settings

There is a login screen, but it is not real authentication. It is only a Streamlit session flag toggled by a button.

## Current Database Model

Live database tables found in `inventory.db`:

- `products`
- `sellers`
- `invoices`
- `seller_transactions`
- `company_details`

Current row counts in the local DB snapshot:

- `products`: 4
- `sellers`: 2
- `invoices`: 5
- `seller_transactions`: 13
- `company_details`: 1

### 1. Products

Current live schema:

- `id`
- `company`
- `category`
- `item_name`
- `item_code`
- `buying_price`
- `selling_price`
- `quantity`
- `date_purchased`
- `gst_percentage`

Constraints:

- unique `(company, category, item_name)`
- unique `item_code`

Business meaning:

- `buying_price` is stored **including GST** in the add-item flows, even though the form asks for buying price excluding GST.
- `selling_price` is the default selling price used during invoice creation.
- `quantity` is current stock on hand.

### 2. Sellers

Current live schema:

- `id`
- `name`
- `address`
- `phone`
- `gstin`
- `total_credit`

Constraint:

- unique `(name, phone)`

Business meaning:

- one seller/customer record per buyer
- `total_credit` is intended to hold current pending khata balance

### 3. Invoices

Current live schema:

- `id`
- `invoice_number`
- `invoice_data`
- `total_amount`
- `date`
- `seller_id`
- `payment_status`
- `pdf_path`

Business meaning:

- `invoice_data` stores the line items JSON for the invoice
- `payment_status` is `paid` or `credit`
- `seller_id` links invoice to seller/customer
- `pdf_path` exists in schema but is not actively written by the current invoice creation flow

Typical `invoice_data` item shape:

- `item_name`
- `item_code`
- `quantity`
- `price`
- `discount_percentage`
- `discount_amount`
- `gst_percentage`
- `gst_amount`
- `total_amount`

### 4. Seller Transactions

Current live schema:

- `id`
- `seller_id`
- `invoice_id`
- `amount`
- `transaction_type`
- `date`
- `notes`

Business meaning:

- ledger entries for khata
- `transaction_type = credit` when an invoice is sold on credit
- `transaction_type = payment` when seller pays some amount later

### 5. Company Details

Current live schema:

- `id`
- `name`
- `address`
- `city`
- `state`
- `state_code`
- `gstin`
- `phone`
- `email`
- `bank_name`
- `bank_account`
- `bank_ifsc`
- `bank_branch`
- `jurisdiction`
- `created_at`
- `updated_at`

Business meaning:

- invoice header / footer settings
- business identity and bank account details used in generated tax invoices

## Core Feature 1: Inventory

Inventory work is split across `pages/add_items.py` and `pages/manage_items.py`.

### What Already Exists

#### A. Add single item

Users can add a single product with:

- company
- category
- item name
- item code
- buying price excluding GST
- GST percentage
- selling price
- quantity
- purchase date

Behavior:

- buying price is converted to buying price including GST before saving
- duplicate check is done against `(company, category, item_name)`
- validation requires all important fields and quantity > 0

#### B. Bulk upload items

Bulk import supports:

- CSV
- XLSX / XLS
- PDF
- PNG / JPG / JPEG

Behavior:

- spreadsheets are read directly into a DataFrame
- PDFs/images are processed with a simple text extraction / OCR approach
- user maps uploaded columns to required product fields
- user can preview and edit mapped rows before upload
- uploaded rows are inserted product-by-product

Important note:

- OCR/PDF parsing is basic and not domain-specific. It is more of a convenience import than a robust purchase-bill parser.

#### C. Combined item entry

There is a bulk-manual entry mode where the user can create many rows at once with a shared:

- company
- category
- or both

This is useful for adding multiple SKUs quickly for the same supplier/category.

#### D. Inventory management / CRUD

Manage Items screen supports:

- load all products
- filter by company
- filter by category
- filter by item name
- edit rows directly in a grid
- save updates back to database
- delete selected products

Editable fields:

- company
- category
- item_name
- item_code
- buying_price
- selling_price
- quantity
- date_purchased
- gst_percentage

Delete behavior:

- products are selected by display label `item_name (Code: item_code)`
- deletion runs by `item_name + item_code`

### Inventory Rules To Preserve In Android

- product identity currently depends on both item metadata and unique `item_code`
- inventory is quantity-based, not batch/lot based
- stock is reduced only when invoice is saved
- zero/negative stock is blocked in invoice flow
- bulk add and quick multi-row add are important productivity features
- company/category based grouping matters in current usage

### Inventory Gaps / Issues To Fix In Android

- no separate stock movement table exists; only the current quantity is stored
- no purchase history table exists beyond `date_purchased`
- item search is filter-text based, no barcode scanner or smart search
- `INSERT OR REPLACE` is used in add flows, which can be dangerous around unique conflicts
- buying price semantics should be normalized clearly: store base price and tax separately, or explicitly store tax-inclusive purchase price

## Core Feature 2: Invoice Generation

Invoice flow lives mainly in `pages/invoice_generation.py`.

### What Already Exists

#### A. Seller selection / seller creation during invoice

User can:

- select an existing seller from history
- or create a new seller inline

The selection UI also shows seller context such as:

- last order date
- total orders
- current credit

#### B. Product selection for invoice

User can:

- browse available products where `quantity > 0`
- filter by company/category/item name
- select one item at a time
- choose quantity
- override selling price
- set GST percentage
- set discount percentage

The invoice cart is stored in Streamlit session state.

#### C. Invoice item calculations

For each line item the system calculates:

- subtotal = quantity x price
- discount amount
- GST amount
- final amount for that line

The user can edit the invoice cart in a grid before saving.

#### D. Stock protection

Before adding an item to the invoice, the app checks:

- current DB stock for that item
- total quantity already present for same item in current invoice cart

This prevents overselling inside the same invoice draft.

#### E. Invoice preview

The app renders a PDF preview inside Streamlit using a generated base64 iframe.

The PDF layout includes:

- company details
- seller details
- invoice number
- invoice date
- item table
- bank details
- declaration and jurisdiction footer

#### F. Save invoice transaction

On save, the current flow:

1. resolves or creates the seller
2. inserts invoice row into `invoices`
3. if payment status is `credit`, inserts a `seller_transactions` credit row
4. reduces inventory quantities for all invoice items
5. commits transaction
6. clears current invoice cart

### Invoice Rules To Preserve In Android

- invoice is created from product stock, not free-text invoice items
- selling price is editable at invoice time
- discount is per line item
- GST is stored per line item
- invoice may be `paid` or `credit`
- invoice links to seller/customer
- invoice save updates inventory and khata together

### Invoice Gaps / Issues To Fix In Android

#### 1. Invoice numbering is weak

`get_next_invoice_number()` uses `COUNT(*) + 1`.

That means:

- invoice numbers depend on row count, not a real sequence
- if deletion ever happens, numbers could be reused
- Android version should use a stable incrementing sequence or UUID-backed display number

#### 2. PDF persistence is incomplete

- `pdf_path` exists in the invoice table
- historical PDFs exist in `invoices/`
- current save flow previews the PDF but does not clearly save the PDF file and persist its path

Android version should define a real document strategy:

- generate PDF on demand
- save/share PDF file
- optionally cache file path

#### 3. Tax / amount logic needs normalization

There is a logic inconsistency in the current code:

- line-item `total_amount` already includes GST
- later invoice totals compute GST again from those totals
- `generate_pdf()` receives a value named `gst_rate`, but the caller passes total GST amount, not a percentage

This likely causes wrong GST display and potential double-counting in parts of the invoice summary.

Android rebuild should define one clean calculation model:

- unit price before tax
- discount
- taxable amount
- tax amount
- line total after tax
- invoice subtotal / tax total / grand total

#### 4. No invoice edit/cancel flow

Current app creates invoices, but there is no strong post-save invoice lifecycle such as:

- edit invoice
- cancel invoice
- return items to stock
- partial payment applied to a specific credit invoice from invoice screen

## Core Feature 3: Seller Management / Khata

Seller management lives in `pages/manage_sellers.py`.

### What Already Exists

The screen has three tabs:

1. Add/Edit Sellers
2. View Sellers
3. Manage Credits

### A. Add/Edit seller master data

Fields:

- name
- address
- phone
- GSTIN

Behavior:

- create new seller
- toggle edit mode for existing seller
- uniqueness is based on `(name, phone)`

### B. View seller list

The seller list shows:

- total invoices
- total sales
- total payments
- remaining credit
- last invoice date

There is search by:

- name
- phone
- GSTIN

Summary cards show:

- total sellers
- total sales
- total payments
- total outstanding

### C. Khata / credit management

For a selected seller, the app shows:

- total sales
- total credit sales
- total paid sales
- total payments
- pending amount
- total invoices

User can record a payment with:

- amount
- payment date
- notes

User can also view:

- payment history / transaction history
- all invoices for that seller
- invoice balances
- invoice search by invoice number
- line-item details for a searched invoice
- related transactions for an invoice

### Khata Rules To Preserve In Android

- seller has a running pending amount
- payment entries are separate ledger rows
- credit sale originates from invoice creation
- seller detail page should combine:
  - profile
  - outstanding amount
  - payment history
  - invoice list
  - invoice detail drill-down

This is one of the strongest features in the current app and should remain a first-class Android flow.

### Seller / Khata Gaps And Risks To Fix In Android

#### 1. Credit update logic is duplicated

Current code updates seller credit in multiple places:

- `manage_sellers.add_transaction()` inserts into `seller_transactions` and also updates `sellers.total_credit`
- invoice save for credit sales inserts into `seller_transactions` and also updates `sellers.total_credit`
- `schema.sql` also defines a trigger `update_seller_credit` that updates `sellers.total_credit` on insert into `seller_transactions`

This means the credit balance logic is duplicated and risky.

Android version should choose exactly one source of truth:

- either compute balance from ledger entries
- or maintain a materialized balance in one controlled place

Recommended: keep `seller_transactions` as the source of truth and derive pending balance from ledger/invoices.

#### 2. Schema drift exists

`schema.sql` expects `sellers.created_at` and `sellers.updated_at`, and the trigger updates `updated_at`.

But the live SQLite table currently does **not** have those columns.

This means the repo has drift between intended schema and actual database state.

Android migration should define a clean, final schema instead of copying the current drift.

#### 3. Bad data already exists

The current local database has at least one suspicious transaction row:

- `seller_transactions.seller_id = '^A'`

That indicates data integrity issues exist in the live DB snapshot and migration scripts should validate imported records.

## Analytics / Reporting

Analytics are implemented in `pages/reports.py`.

### What Already Exists

#### Executive summary

- total revenue
- total orders
- credit sales
- outstanding credit
- growth vs previous period

#### Sales analysis

- daily sales trends
- moving averages
- top products by revenue
- top products by quantity

#### Customer analysis

- RFM-style segmentation
- champions / loyal / regular / inactive buckets

#### Credit analysis

- daily credit sales trend
- top customers by outstanding credit

#### Inventory insights

- stock value by category
- low-stock item alerts

### Notes For Android

- analytics are useful, but not required for v1 if the goal is to get the operational app working first
- most analytics can be recreated from invoices, sellers, and products once the core data model is solid
- low-stock alerts should probably move into core inventory rather than wait for analytics phase

## Company Settings / Invoice Branding

`pages/company_settings.py` manages business metadata used in invoices.

### What Already Exists

Editable business details:

- company name
- address
- city
- state
- state code
- GSTIN
- phone
- email
- jurisdiction

Editable bank details:

- bank name
- account number
- IFSC
- branch

There is also a visual preview of how the company block will look on the invoice.

### Android Relevance

This should become a Settings section in Android because invoices depend on it.

## Backup / Logging / Operational Behavior

### Backup

There are two backup paths in the repo:

#### 1. `backup.py`

- creates local backup copies of `inventory.db`
- keeps only a limited number of files
- backup is triggered on login/logout through `after_login_logout()`

#### 2. `utils/backup_manager.py`

- creates local backup copies
- uploads backups to Google Drive using `credentials.json` and `token.pickle`
- `main.py` calls `init_backup()` at startup

Operational meaning:

- backups are considered important in the current product
- Android version should also have a clear backup/export story

Potential Android options later:

- local database export
- Google Drive backup
- manual JSON/CSV export

### Logging

`utils/logger.py` writes logs to:

- console
- `logs/app_YYYYMMDD.log`

Important note:

- `setup_logger()` adds handlers each time it is called, so repeated imports may lead to duplicate log lines

## Live Data Snapshot From Current DB

This is useful only as context for migration, not as final product logic.

Current sample state in local DB:

- 4 products across categories like `pen`, `egr`, `eee`
- 2 sellers
- 5 invoices
- invoice statuses include both `paid` and `credit`
- 13 seller transaction rows

Aggregate invoice totals in current DB:

- credit invoices: 2 invoices, total about `2333.18`
- paid invoices: 3 invoices, total about `903.17`

This confirms the app is already being used for real workflows, not just demo data.

## Important Code / Architecture Observations

### 1. Business logic is tightly mixed into UI pages

Most logic lives directly inside Streamlit page files.

Examples:

- DB writes in page handlers
- invoice math in page code
- PDF generation in page code
- seller/credit logic in page code

For Android, this should be separated into:

- data layer
- domain/use-case layer
- UI layer

### 2. `schema.sql` and `main.py` both define schema behavior

Database setup logic is split between:

- direct `CREATE TABLE` in `main.py`
- `schema.sql` executed through `utils/db_manager.init_db()`

This increases drift risk and should not be copied into Android.

### 3. `utils/pdf_generator.py` is not really used

There is a placeholder class, but the real invoice PDF generation is inside `pages/invoice_generation.py`.

### 4. No tests were found

There is no visible test suite in the repo.

### 5. No API/backend separation exists

This is a monolithic local app. Android migration can either:

- stay local-first with on-device database
- or move to a backend later

Given current repo behavior, a local-first Android app is the closest migration path.

## What The Android App Should Preserve First

Recommended v1 parity based on what is already valuable in this repo:

### 1. Inventory

- product master list
- add/edit/delete item
- search/filter by company/category/name
- quick multi-row item add
- bulk import later if needed
- low-stock warning

### 2. Invoice

- seller selection or creation
- item selection from inventory
- editable selling price
- discount and GST handling
- invoice preview
- save invoice
- paid vs credit mode
- reduce stock when invoice is saved
- generate/share PDF

### 3. Seller / khata

- seller list
- seller detail screen
- outstanding amount
- payment recording
- payment history
- invoice history
- invoice-level balance view

### 4. Settings

- company details
- GST details
- bank details
- invoice branding config

## Suggested Android Screen Map

If the Android app is meant to mirror the current product, these screens map well:

1. Home
2. Inventory List
3. Add/Edit Product
4. Bulk Add / Quick Add
5. Create Invoice
6. Invoice Preview / Share
7. Sellers List
8. Seller Detail / Khata
9. Record Payment
10. Company Settings
11. Reports / Analytics later

## Suggested Clean Android Data Model

The current repo suggests these core entities for Android:

- `Product`
- `Seller`
- `Invoice`
- `InvoiceItem`
- `SellerTransaction`
- `CompanyProfile`

Recommended improvement over current schema:

- split invoice header and invoice items cleanly instead of storing all items only as JSON
- keep invoice items in a dedicated table
- keep stock movements in a dedicated table
- compute seller balances from ledger/invoices or maintain one carefully controlled aggregate
- use proper migrations instead of manual schema drift

## Suggested Build Order For Android

This order fits both the current repo and your stated priority:

1. Inventory module
2. Seller module
3. Invoice module with stock updates + credit handling
4. Settings / company profile
5. PDF generation + share/export
6. Analytics and dashboards
7. Backup/sync/export improvements

## Recommended Migration Decisions

These are the most important decisions before building:

### Decision 1: local-only or backend-backed

Closest to current repo:

- local Android DB first

Possible later:

- cloud sync/backend

### Decision 2: invoice item storage

Current app:

- invoice items stored as JSON in one column

Recommended Android approach:

- dedicated `invoice_items` table

### Decision 3: khata balance source of truth

Recommended:

- ledger-driven balance, not multiple manual updates

### Decision 4: tax model

Recommended:

- normalize before implementation and keep one consistent pricing formula across UI, DB, and PDF

## Risks To Keep In Mind During Migration

1. Current schema and live DB do not fully match.
2. Credit balance logic is duplicated and risky.
3. Invoice total/tax logic is inconsistent.
4. PDF persistence is incomplete.
5. Current data may include integrity issues.
6. Business rules are spread across UI code and need extraction.

## Bottom Line

The repo already contains a real, working foundation for the Android app.

The strongest existing product value is:

1. inventory CRUD with multi-item entry
2. invoice generation directly from stock
3. seller khata with payment history and outstanding tracking

The Android app should not be treated as a totally new product. It should be treated as a cleaner rebuild of the same local business operating system, with these improvements:

- cleaner schema
- proper invoice math
- more reliable khata accounting
- better document export
- better UI for mobile usage

## File Reference Index

- `main.py`: app entrypoint, page routing, backup startup call, manual schema setup
- `schema.sql`: intended schema and trigger definitions
- `utils/db_manager.py`: DB connection + schema initialization + company defaults
- `pages/add_items.py`: single add, bulk upload, OCR import, combined item entry
- `pages/manage_items.py`: inventory edit/delete/filter screen
- `pages/invoice_generation.py`: seller select/create, invoice cart, stock checks, PDF preview, invoice save
- `pages/manage_sellers.py`: seller CRUD, khata, payments, invoice history, invoice search
- `pages/reports.py`: analytics/reporting dashboard
- `pages/company_settings.py`: business profile and bank details
- `utils/backup_manager.py`: local + Google Drive backup flow
- `backup.py`: simple local backup on login/logout
- `utils/logger.py`: logging setup
- `utils/validators.py`: minimal validation helpers
