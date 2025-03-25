import os
import shutil
import json
from datetime import datetime
import zipfile
import argparse
from typing import List, Dict, Optional

class BotBackup:
    def __init__(self, bot_dir: str):
        self.bot_dir = bot_dir
        self.backup_dir = os.path.join(bot_dir, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Define directories and files to exclude
        self.exclude_patterns = [
            "venv",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".git",
            ".env",
            "backups",
            "temp_backup",
            "temp_restore"
        ]

    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a backup of the bot directory.
        
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
            # Copy bot directory to temp directory
            for item in os.listdir(self.bot_dir):
                # Skip excluded patterns
                if any(pattern in item for pattern in self.exclude_patterns):
                    continue
                    
                s = os.path.join(self.bot_dir, item)
                d = os.path.join(temp_dir, item)
                
                if os.path.isfile(s):
                    shutil.copy2(s, d)
                elif os.path.isdir(s):
                    shutil.copytree(s, d)
            
            # Create backup manifest
            manifest = {
                "backup_name": backup_name,
                "timestamp": timestamp,
                "backup_version": "1.0",
                "bot_directory": self.bot_dir,
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
            
            print(f"✅ Backup created successfully: {zip_path}")
            return zip_path
            
        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def restore_backup(self, backup_path: str) -> bool:
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
            
            # Remove existing files (except backups and venv)
            for item in os.listdir(self.bot_dir):
                if item not in ['backups', 'venv']:
                    item_path = os.path.join(self.bot_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
            
            # Copy backup files
            for item in os.listdir(temp_dir):
                if item != "manifest.json":  # Skip manifest
                    s = os.path.join(temp_dir, item)
                    d = os.path.join(self.bot_dir, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d)
                    elif os.path.isdir(s):
                        shutil.copytree(s, d)
            
            print("✅ Backup restored successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error restoring backup: {e}")
            return False
            
        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def list_backups(self) -> List[Dict]:
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

    def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup file.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                print(f"✅ Backup deleted successfully: {backup_path}")
                return True
            print(f"❌ Backup not found: {backup_path}")
            return False
        except Exception as e:
            print(f"❌ Error deleting backup: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Bot Backup Utility")
    parser.add_argument("--dir", default=".", help="Bot directory path")
    parser.add_argument("--action", choices=["create", "restore", "list", "delete"], required=True,
                      help="Action to perform")
    parser.add_argument("--name", help="Backup name (for create) or backup path (for restore/delete)")
    
    args = parser.parse_args()
    
    backup = BotBackup(args.dir)
    
    if args.action == "create":
        backup.create_backup(args.name)
    elif args.action == "restore":
        if not args.name:
            print("❌ Please provide a backup path to restore from")
            return
        backup.restore_backup(args.name)
    elif args.action == "list":
        backups = backup.list_backups()
        if not backups:
            print("No backups found.")
            return
            
        print("\nAvailable Backups:")
        print("-" * 50)
        for backup_info in backups:
            print(f"Name: {backup_info['name']}")
            print(f"Size: {backup_info['size'] / 1024 / 1024:.2f} MB")
            print(f"Created: {backup_info['created']}")
            print(f"Modified: {backup_info['modified']}")
            print("-" * 50)
    elif args.action == "delete":
        if not args.name:
            print("❌ Please provide a backup path to delete")
            return
        backup.delete_backup(args.name)

if __name__ == "__main__":
    main() 