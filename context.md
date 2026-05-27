# Android App Context

## What This Product Is

This repo is a local-first inventory and billing system for a small business.

The product already revolves around three core business modules:

1. Inventory
2. Invoice generation
3. Seller management / khata

Analytics, reports, backup, and company settings already exist, but they sit on top of those three core flows.

## Core Goal For Android

The Android application should be a cleaner rebuild of the current business workflow, not a brand new product.

The app should preserve the existing operating model:

- maintain stock
- create invoices from stock
- track paid vs credit invoices
- maintain seller pending balance
- record payments and history

## Current Business Modules

### 1. Inventory

Inventory currently supports:

- add single item
- bulk upload from CSV / Excel
- OCR-style import from PDF/image
- quick multi-row item entry for same company/category
- edit product details
- delete products
- filter/search by company, category, item name

Each product currently has:

- company
- category
- item name
- item code
- buying price
- selling price
- quantity
- date purchased
- GST percentage

Current product rules:

- `item_code` is unique
- `(company, category, item_name)` is also unique
- quantity represents current stock on hand
- stock is reduced when an invoice is saved

Important business note:

- buying price is entered excluding GST in UI, but stored after GST is added in current code

### 2. Invoice Generation

Invoice flow currently works like this:

1. user selects an existing seller or creates a new seller
2. user selects items from current inventory
3. user chooses quantity, selling price, GST, and discount
4. app builds an invoice cart
5. app previews invoice as PDF
6. app saves invoice
7. app reduces product quantities
8. if payment mode is credit, app adds khata entry

Invoice supports:

- seller/customer link
- line-item quantity
- editable selling price
- GST per line
- discount per line
- paid or credit status
- PDF preview

Current invoice item data includes:

- item name
- item code
- quantity
- price
- discount percentage
- discount amount
- GST percentage
- GST amount
- total amount

### 3. Seller Management / Khata

Seller management is one of the strongest parts of the current app.

It currently supports:

- add seller
- edit seller
- view seller list
- search sellers
- view seller-level totals
- record payments
- view payment history
- view invoice history
- search invoice by invoice number
- inspect invoice items for a seller

Each seller currently has:

- name
- address
- phone
- GSTIN
- total credit

Khata behavior today:

- credit invoice increases seller pending amount
- payment entry reduces seller pending amount
- payment history is stored separately from invoices
- seller detail view combines profile, totals, invoices, and transactions

## Main Data Concepts

The current app is built around these entities:

- Product
- Seller
- Invoice
- SellerTransaction
- CompanyDetails

### Product

Represents inventory stock.

Key meaning:

- this is the source of truth for available quantity during invoicing

### Seller

Represents the buyer/customer.

Key meaning:

- one seller can have many invoices
- one seller can have many khata/payment transactions

### Invoice

Represents a sale.

Key meaning:

- invoice stores seller linkage
- invoice stores final total
- invoice stores payment status (`paid` or `credit`)
- invoice currently stores line items as JSON blob

### SellerTransaction

Represents khata ledger movement.

Two important transaction types:

- `credit`
- `payment`

Meaning:

- `credit` comes from a credit sale invoice
- `payment` comes from later money collection

### CompanyDetails

Represents the business identity used in invoices.

Includes:

- company name and address
- GST details
- bank details
- jurisdiction

## Existing User Workflows

### Workflow A: Add stock

Typical flow:

1. open inventory add screen
2. add single item, bulk upload, or quick multi-row entry
3. validate values
4. save into product table

### Workflow B: Sell items and generate invoice

Typical flow:

1. select or create seller
2. filter inventory
3. add items to invoice cart
4. adjust quantity/price/GST/discount
5. preview invoice
6. save invoice
7. inventory gets reduced
8. if credit sale, seller khata increases

### Workflow C: Collect payment from seller

Typical flow:

1. open seller management
2. choose seller
3. review pending amount
4. record payment amount and date
5. save payment entry
6. seller pending amount decreases

### Workflow D: Review seller history

Typical flow:

1. open seller detail / credit management
2. inspect payment history
3. inspect invoices
4. search a specific invoice number
5. see invoice line items and related payments

## Existing Supporting Modules

### Analytics

Current app already has:

- revenue summary
- order counts
- credit sales tracking
- outstanding credit view
- product performance
- low-stock alerts
- category stock value
- customer segmentation

This means analytics can be rebuilt later from the same core entities.

### Company Settings

Current app already lets the business edit:

- company identity
- GST details
- contact details
- bank details
- invoice footer/jurisdiction data

This should remain a settings module in Android because invoice generation depends on it.

### Backup

Current repo includes:

- local SQLite backups
- optional Google Drive backup logic

This indicates backup/export is important operationally, even if it is not part of Android v1.

## Business Rules That Matter For Android

These are the important rules to preserve when rebuilding:

### Inventory rules

- only products with stock should be sellable
- invoice creation must not allow quantity beyond available stock
- quantity should reduce only when invoice save succeeds
- company/category grouping is part of how inventory is organized

### Invoice rules

- invoice must be tied to a seller
- invoice is built from real inventory items
- price can be overridden at sale time
- discount and GST are line-item level concepts
- invoice can be paid immediately or marked as credit

### Khata rules

- seller pending amount matters operationally
- credit sales should appear in khata
- payments should be stored as separate ledger entries
- seller detail screen should show both invoices and transactions

### Settings rules

- invoice output depends on company profile and bank details

## Important Problems In The Current App

These are not reasons to discard the product; they are the cleanup list for Android.

### 1. Invoice numbering is weak

Current invoice number generation is based on total invoice count.

This should be replaced with a proper sequence strategy.

### 2. Invoice items are stored as JSON only

Current app stores all line items inside a single invoice JSON field.

Android should use a proper `invoice_items` table.

### 3. Credit balance logic is duplicated

Seller pending amount is updated in multiple places.

Android should use one clean source of truth for khata balance.

### 4. Tax and totals need normalization

Current code has inconsistencies around GST and totals.

Android should define one exact pricing model and use it everywhere.

### 5. Schema drift exists

The intended schema and the live SQLite DB do not fully match.

Android should start from a clean final schema, not copy the drift.

### 6. Product logic is tightly mixed with UI code

Current Streamlit pages contain both UI and business logic.

Android should separate:

- UI
- data layer
- domain/use-case layer

## What Should Be In Android V1

If the goal is to preserve business value quickly, Android v1 should include:

1. Inventory list + add/edit/delete
2. Quick product entry
3. Seller list + seller detail
4. Record seller payments
5. Create invoice from inventory
6. Paid vs credit invoice handling
7. Stock deduction on invoice save
8. Company settings
9. PDF invoice generation/sharing

Analytics can come after the operational workflows are stable.

## Recommended Clean Data Model For Android

Use these core entities:

- `Product`
- `Seller`
- `Invoice`
- `InvoiceItem`
- `SellerTransaction`
- `CompanyProfile`

Strong recommendation:

- keep `Invoice` and `InvoiceItem` separate
- keep khata ledger explicit
- optionally add `StockMovement` if you want better inventory history

## Suggested Android Screen Set

Practical screen set based on current business usage:

1. Dashboard / Home
2. Inventory List
3. Add/Edit Product
4. Quick Add / Bulk Add
5. Sellers List
6. Seller Detail / Khata
7. Record Payment
8. Create Invoice
9. Invoice Preview / Share PDF
10. Company Settings
11. Reports later

## Migration Priority

Build in this order:

1. Inventory
2. Sellers / khata
3. Invoice generation
4. Settings
5. PDF export/share
6. Analytics
7. Backup/sync improvements

## Bottom Line

The repo already proves the product shape.

The Android app should preserve this business loop:

1. add stock
2. sell from stock
3. create invoice
4. mark paid or credit
5. track seller pending balance
6. record payments
7. review history

That loop is the real product.
