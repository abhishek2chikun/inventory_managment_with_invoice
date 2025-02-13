import os
import shutil
from datetime import datetime
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle
import json

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.file']
BACKUP_DIR = 'backups'
MAX_LOCAL_BACKUPS = 5
MAX_DRIVE_BACKUPS = 10

class BackupManager:
    def __init__(self):
        self.backup_dir = BACKUP_DIR
        self.ensure_backup_dir()
        self.creds = None
        
    def ensure_backup_dir(self):
        """Ensure backup directory exists"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            
    def get_google_creds(self):
        """Get or refresh Google Drive credentials"""
        creds = None
        token_path = 'token.pickle'
        creds_path = 'credentials.json'
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    logger.error("credentials.json not found")
                    return None
                    
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
                
        return creds
        
    def create_local_backup(self):
        """Create a local backup of the database"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(self.backup_dir, f'inventory_{timestamp}.db')
            
            # Copy the current database
            shutil.copy2('inventory.db', backup_path)
            
            # Remove old backups if exceeding MAX_LOCAL_BACKUPS
            backups = sorted([f for f in os.listdir(self.backup_dir) if f.endswith('.db')])
            while len(backups) > MAX_LOCAL_BACKUPS:
                os.remove(os.path.join(self.backup_dir, backups.pop(0)))
                
            logger.info(f"Local backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating local backup: {e}")
            return None
            
    def upload_to_drive(self, file_path):
        """Upload backup to Google Drive"""
        try:
            creds = self.get_google_creds()
            if not creds:
                logger.error("Failed to get Google credentials")
                return False
                
            service = build('drive', 'v3', credentials=creds)
            
            # Check for backup folder in Drive
            folder_name = 'InventoryBackups'
            folder_id = None
            
            # Search for existing backup folder
            results = service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                spaces='drive'
            ).execute()
            
            if not results['files']:
                # Create backup folder
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                folder_id = folder.get('id')
            else:
                folder_id = results['files'][0]['id']
            
            # Upload file
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [folder_id]
            }
            
            media = MediaFileUpload(
                file_path,
                mimetype='application/x-sqlite3',
                resumable=True
            )
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            # Clean up old backups in Drive
            results = service.files().list(
                q=f"'{folder_id}' in parents",
                orderBy='createdTime'
            ).execute()
            
            files = results.get('files', [])
            while len(files) > MAX_DRIVE_BACKUPS:
                service.files().delete(fileId=files[0]['id']).execute()
                files.pop(0)
                
            logger.info(f"Backup uploaded to Drive: {file.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading to Google Drive: {e}")
            return False
            
    def perform_backup(self):
        """Perform complete backup (local and Drive)"""
        backup_path = self.create_local_backup()
        if backup_path:
            if self.upload_to_drive(backup_path):
                logger.info("Backup completed successfully")
                return True
            else:
                logger.warning("Local backup created but Drive upload failed")
                return False
        return False

def init_backup():
    """Initialize backup system and perform backup"""
    backup_manager = BackupManager()
    return backup_manager.perform_backup() 