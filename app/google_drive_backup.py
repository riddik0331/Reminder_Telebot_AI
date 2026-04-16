"""
Google Drive Backup Module for Telegram Reminder Bot.

This module handles automatic backup of the SQLite database to Google Drive.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Path to credentials file
CREDENTIALS_PATH = Path(__file__).parent.parent / "credentials.json"
TOKEN_PATH = Path(__file__).parent.parent / "token.json"


def get_drive_service():
    """
    Get Google Drive API service.

    Requires:
    - credentials.json from Google Cloud Console
    - First run: browser will open for authorization

    Returns:
        Google Drive service object or None if not configured
    """
    if not CREDENTIALS_PATH.exists():
        logger.warning(
            "Google Drive credentials not found. Create credentials.json from Google Cloud Console."
        )
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        SCOPES = ["https://www.googleapis.com/auth/drive.file"]

        creds = None

        # Load existing token
        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(google.auth.transport.requests.Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_PATH), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next time
            with open(TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())

        service = build("drive", "v3", credentials=creds)
        return service

    except Exception as e:
        logger.error(f"Failed to initialize Google Drive: {e}")
        return None


def is_drive_configured() -> bool:
    """Check if Google Drive is configured."""
    return CREDENTIALS_PATH.exists()


async def backup_database_to_drive() -> dict:
    """
    Backup database to Google Drive.

    Returns:
        Dict with status and message
    """
    from app.database import DATABASE_PATH

    try:
        service = get_drive_service()
        if not service:
            return {
                "success": False,
                "message": "❌ Google Drive не настроен.\n\nДля настройки:\n1. Создай проект в Google Cloud Console\n2. Включи Google Drive API\n3. Скачай credentials.json\n4. Помести его в папку с ботом",
            }

        # Check if database exists
        if not DATABASE_PATH.exists():
            return {"success": False, "message": "❌ База данных не найдена"}

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"reminder_bot_backup_{timestamp}.db"

        # Get folder ID or create one
        folder_id = await get_or_create_backup_folder(service)
        if not folder_id:
            return {
                "success": False,
                "message": "❌ Не удалось создать папку для бекапов",
            }

        # Upload file
        from googleapiclient.http import MediaFileUpload

        file_metadata = {"name": backup_filename, "parents": [folder_id]}

        media = MediaFileUpload(str(DATABASE_PATH), mimetype="application/x-sqlite3")

        file = (
            service.files()
            .create(
                body=file_metadata, media_body=media, fields="id, name, createdTime"
            )
            .execute()
        )

        # Format creation time
        created_time = datetime.fromisoformat(
            file.get("createdTime", "").replace("Z", "+00:00")
        )
        created_str = created_time.strftime("%d.%m.%Y %H:%M:%S")

        logger.info(f"Backup created: {file.get('name')} (ID: {file.get('id')})")

        return {
            "success": True,
            "message": f"✅ *Бекап создан!*\n\n📁 Файл: `{file.get('name')}`\n🕐 Время: {created_str}\n🆔 ID: `{file.get('id')}`",
            "file_id": file.get("id"),
            "filename": file.get("name"),
        }

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return {"success": False, "message": f"❌ Ошибка при бекапе: {str(e)}"}


async def get_or_create_backup_folder(service) -> Optional[str]:
    """Get or create folder for backups."""
    try:
        # Search for existing folder
        results = (
            service.files()
            .list(
                q="name='ReminderBot Backups' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces="drive",
                fields="files(id, name)",
            )
            .execute()
        )

        folders = results.get("files", [])

        if folders:
            return folders[0]["id"]

        # Create new folder
        file_metadata = {
            "name": "ReminderBot Backups",
            "mimeType": "application/vnd.google-apps.folder",
        }

        folder = service.files().create(body=file_metadata, fields="id").execute()

        return folder.get("id")

    except Exception as e:
        logger.error(f"Failed to get/create backup folder: {e}")
        return None


async def list_backups() -> dict:
    """
    List all backups on Google Drive.

    Returns:
        Dict with list of backups
    """
    try:
        service = get_drive_service()
        if not service:
            return {"success": False, "message": "❌ Google Drive не настроен"}

        # Find backup folder
        results = (
            service.files()
            .list(
                q="name='ReminderBot Backups' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces="drive",
                fields="files(id)",
            )
            .execute()
        )

        folders = results.get("files", [])
        if not folders:
            return {"success": False, "message": "❌ Папка бекапов не найдена"}

        folder_id = folders[0]["id"]

        # List files in folder
        results = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces="drive",
                fields="files(id, name, createdTime, size)",
            )
            .execute()
        )

        files = results.get("files", [])

        if not files:
            return {"success": True, "message": "📁 Бекапов пока нет", "backups": []}

        # Format response
        file_list = []
        for f in files:
            created = datetime.fromisoformat(
                f.get("createdTime", "").replace("Z", "+00:00")
            )
            size_kb = int(f.get("size", 0)) / 1024
            file_list.append(
                {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "created": created.strftime("%d.%m.%Y %H:%M"),
                    "size_kb": round(size_kb, 1),
                }
            )

        # Sort by date (newest first)
        file_list.sort(key=lambda x: x["created"], reverse=True)

        message = "📁 *Бекапы на Google Drive:*\n\n"
        for i, f in enumerate(file_list[:10], 1):  # Show last 10
            message += f"{i}. {f['name']}\n"
            message += f"   🕐 {f['created']} | 📦 {f['size_kb']} KB\n\n"

        if len(file_list) > 10:
            message += f"\n... и ещё {len(file_list) - 10} бекапов"

        return {"success": True, "message": message, "backups": file_list}

    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        return {"success": False, "message": f"❌ Ошибка: {str(e)}"}
