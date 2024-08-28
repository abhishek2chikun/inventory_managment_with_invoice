CREATE DATABASE IF NOT EXISTS gananath;

USE gananath;

CREATE TABLE items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    billing_from_name VARCHAR(255) NOT NULL,
    category_name VARCHAR(255) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    item_buying_price DECIMAL(10, 2) NOT NULL,
    item_selling_price DECIMAL(10, 2) NOT NULL,
    sgst DECIMAL(5, 2) NOT NULL,
    cgst DECIMAL(5, 2) NOT NULL,
    box INT NOT NULL,
    quantity INT NOT NULL,
    buying_price_after_tax_per_quantity DECIMAL(10, 2) NOT NULL,
    total_buying_price_after_tax DECIMAL(10, 2) NOT NULL,
    date_purchased DATE NOT NULL
);