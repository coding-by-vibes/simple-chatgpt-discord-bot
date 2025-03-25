import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional
import zipfile

class BackupManager:
    def __init__(self, settings_dir: str):
        self.settings_dir = settings_dir
        self.backup_dir = os.path.join(settings_dir, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

    async def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a backup of all bot data and settings.
        
        Args:
            backup_name: Optional name for the backup. If not provided, 
                        generates a timestamp-based name.
                        
        Returns:
            str: Path to the backup file
        """
        # Create timestamp for backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = backup_name or f"bot_backup_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        # Create temporary directory for backup
        temp_dir = os.path.join(self.backup_dir, "temp_backup")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Backup settings directory
            settings_backup = os.path.join(temp_dir, "settings")
            shutil.copytree(self.settings_dir, settings_backup, 
                          ignore=shutil.ignore_patterns('backups', 'temp_backup'))
            
            # Create backup manifest
            manifest = {
                "backup_name": backup_name,
                "timestamp": timestamp,
                "backup_version": "1.0",
                "contents": {
                    "settings": True,
                    "personas": True,
                    "user_data": True,
                    "conversations": True,
                    "error_logs": True,
                    "feedback": True
                }
            }
            
            # Save manifest
            with open(os.path.join(temp_dir, "manifest.json"), 'w') as f:
                json.dump(manifest, f, indent=4)
            
            # Create zip file
            zip_path = f"{backup_path}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            return zip_path
            
        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    async def restore_backup(self, backup_path: str) -> bool:
        """Restore bot state from a backup file.
        
        Args:
            backup_path: Path to the backup zip file
            
        Returns:
            bool: True if restore was successful, False otherwise
        """
        try:
            # Create temporary directory for restoration
            temp_dir = os.path.join(self.backup_dir, "temp_restore")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Extract backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Read manifest
            with open(os.path.join(temp_dir, "manifest.json"), 'r') as f:
                manifest = json.load(f)
            
            # Restore settings directory
            settings_backup = os.path.join(temp_dir, "settings")
            if os.path.exists(settings_backup):
                # Remove existing settings (except backups)
                for item in os.listdir(self.settings_dir):
                    if item not in ['backups', 'temp_backup']:
                        item_path = os.path.join(self.settings_dir, item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                
                # Copy backup settings
                for item in os.listdir(settings_backup):
                    s = os.path.join(settings_backup, item)
                    d = os.path.join(self.settings_dir, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d)
                    elif os.path.isdir(s):
                        shutil.copytree(s, d)
            
            return True
            
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False
            
        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    async def list_backups(self) -> List[Dict]:
        """List all available backups.
        
        Returns:
            List[Dict]: List of backup information
        """
        backups = []
        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.zip'):
                file_path = os.path.join(self.backup_dir, filename)
                file_stats = os.stat(file_path)
                backups.append({
                    "name": filename,
                    "path": file_path,
                    "size": file_stats.st_size,
                    "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                })
        return sorted(backups, key=lambda x: x["modified"], reverse=True)

    async def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup file.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting backup: {e}")
            return False 