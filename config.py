import os

class Config:
    DATABASE_PATH = 'inventory.db'
    BACKUP_DIR = 'backups'
    MAX_BACKUPS = 30
    PDF_DIR = 'invoices'
    
    # Company details
    COMPANY_NAME = "Gananath Enterprises"
    COMPANY_ADDRESS = "New Colony, Rayagada,"
    COMPANY_CITY = "Odisha, 765001"
    COMPANY_GSTIN = "XXX1933884" 