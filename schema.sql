-- Enable foreign key support
PRAGMA foreign_keys = ON;

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT,
    category TEXT,
    item_name TEXT,
    item_code TEXT,
    buying_price REAL,
    selling_price REAL,
    quantity INTEGER,
    date_purchased TEXT,
    gst_percentage REAL,
    UNIQUE(company, category, item_name),
    UNIQUE(item_code)
);

-- Sellers table
CREATE TABLE IF NOT EXISTS sellers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT,
    phone TEXT,
    gstin TEXT,
    total_credit REAL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, phone)
);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_data TEXT,  -- JSON data containing invoice items
    total_amount REAL,
    date TEXT,
    seller_id INTEGER,
    payment_status TEXT DEFAULT 'paid',  -- 'paid' or 'credit'
    invoice_number TEXT,  -- Format: INV0001, INV0002, etc.
    FOREIGN KEY(seller_id) REFERENCES sellers(id)
);

-- Seller transactions table
CREATE TABLE IF NOT EXISTS seller_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER,
    invoice_id INTEGER,
    amount REAL,
    transaction_type TEXT,  -- 'payment' or 'credit'
    date TEXT,
    notes TEXT,
    FOREIGN KEY(seller_id) REFERENCES sellers(id),
    FOREIGN KEY(invoice_id) REFERENCES invoices(id)
);

-- Create company details table
CREATE TABLE IF NOT EXISTS company_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL,
    gstin TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    bank_name TEXT,
    bank_account TEXT,
    bank_ifsc TEXT,
    bank_branch TEXT,
    jurisdiction TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Insert default company details if not exists
INSERT OR IGNORE INTO company_details (
    name, address, city, state, state_code, gstin, 
    phone, email, bank_name, bank_account, bank_ifsc, 
    bank_branch, jurisdiction
) VALUES (
    'GANANATH ENTERPRISES',
    'New Colony',
    'Rayagada',
    'Odisha',
    '21',
    'XXX1933884',
    '',
    '',
    'HDFC BANK',
    '50200055243922',
    'HDFC0000640',
    'HDFC BANK NAYAPALLI BRANCH',
    'BHUBANESWAR'
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_products_item_code ON products(item_code);
CREATE INDEX IF NOT EXISTS idx_sellers_name ON sellers(name);
CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_seller ON invoices(seller_id);
CREATE INDEX IF NOT EXISTS idx_transactions_seller ON seller_transactions(seller_id);
CREATE INDEX IF NOT EXISTS idx_transactions_invoice ON seller_transactions(invoice_id);

-- Add trigger for credit updates
CREATE TRIGGER IF NOT EXISTS update_seller_credit
AFTER INSERT ON seller_transactions
BEGIN
    UPDATE sellers 
    SET total_credit = total_credit + 
        CASE WHEN NEW.transaction_type = 'credit' 
            THEN NEW.amount 
            ELSE -NEW.amount 
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.seller_id;
END; 