"""
Instagram Reels Upload - Using Google Drive for Public URL
Uploads video to Google Drive, makes it public, then uses URL for Instagram API
"""

import os
import requests
import time
import tempfile
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)


def get_drive_service():
    """Initialize and return Google Drive API client with write access."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    GOOGLE_SERVICE_ACCOUNT_KEY = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")

    if not GOOGLE_SERVICE_ACCOUNT_KEY:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY not set")

    if os.path.exists(GOOGLE_SERVICE_ACCOUNT_KEY):
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_KEY, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    elif GOOGLE_SERVICE_ACCOUNT_KEY.strip().startswith('{'):
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.write(GOOGLE_SERVICE_ACCOUNT_KEY)
        temp_file.close()
        creds = service_account.Credentials.from_service_account_file(
            temp_file.name, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        os.unlink(temp_file.name)
        return service
    else:
        raise ValueError("Google Service Account key is invalid")


def upload_video_to_drive(service, file_path, folder_id):
    """Upload video to Google Drive and return public direct download URL."""
    from googleapiclient.http import MediaFileUpload

    file_name = f"temp_ig_upload_{int(time.time())}.mp4"
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)

    file = service.files().create(
        body=file_metadata, media_body=media, fields='id'
    ).execute()
    file_id = file.get('id')
    print(f"[instagram] Uploaded to Google Drive (file_id: {file_id})")

    permission = {'type': 'anyone', 'role': 'reader'}
    service.permissions().create(fileId=file_id, body=permission).execute()
    print(f"[instagram] Made file publicly accessible")

    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    return file_id, direct_url


def delete_drive_file(service, file_id):
    """Clean up temporary file from Google Drive."""
    try:
        service.files().delete(fileId=file_id).execute()
        print(f"[instagram] Cleaned up temporary file {file_id} from Google Drive")
    except Exception as e:
        print(f"[instagram] Could not delete temporary file: {e}")


def cleanup_stale_temp_files(service, folder_id):
    """Remove any leftover temp files from previous aborted runs."""
    try:
        query = f"'{folder_id}' in parents and name contains 'temp_ig_upload_' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        stale = results.get('files', [])
        for f in stale:
            try:
                service.files().delete(fileId=f['id']).execute()
                print(f"[instagram] Cleaned stale temp file: {f['name']} ({f['id']})")
            except Exception:
                pass
        if stale:
            print(f"[instagram] Cleaned {len(stale)} stale temp file(s) from previous runs")
    except Exception as e:
        print(f"[instagram] Could not scan for stale temp files: {e}")


def upload_to_instagram(video_path, caption, is_story=False):
    media_type = 'STORIES' if is_story else 'REELS'

    print("\n" + "=" * 60)
    print(f"INSTAGRAM {media_type} UPLOAD STARTING")
    print("=" * 60)

    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN') or os.getenv('FACEBOOK_ACCESS_TOKEN')
    user_id = os.getenv('INSTAGRAM_ACCOUNT_ID') or os.getenv('IG_USER_ID')
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

    def mask(s):
        return f"{s[:10]}...{s[-4:]}" if s and len(s) > 10 else ("PLACEHOLDER" if s == "***" else "MISSING")

    print(f"[instagram] User ID Provided: {user_id}")
    print(f"[instagram] Access Token: {mask(access_token)}")

    if not access_token:
        print("[instagram] Skipping Instagram upload - INSTAGRAM_ACCESS_TOKEN not set")
        return {'status': 'skipped', 'reason': 'Missing credentials', 'platform': 'instagram'}

    if access_token.startswith('IGAA'):
        print("[instagram] Detected 'IGAA' token (Instagram Basic/Standard API)")
        print("[instagram] Fetching correct ID for this token...")
        try:
            me_resp = requests.get(
                f"https://graph.facebook.com/me?fields=id,username&access_token={access_token}",
                timeout=10
            )
            if me_resp.status_code == 200:
                me_data = me_resp.json()
                detected_id = me_data.get('id')
                if detected_id and detected_id != user_id:
                    print(f"[instagram] ID Mismatch! Provided: {user_id}, Detected: {detected_id}")
                    print(f"[instagram] Using detected ID: {detected_id}")
                    user_id = detected_id
            else:
                print(f"[instagram] Could not verify token: {me_resp.text}")
        except Exception as e:
            print(f"[instagram] Error during ID verification: {e}")

    if not user_id:
        print("[instagram] Skipping Instagram upload - INSTAGRAM_ACCOUNT_ID not set")
        return {'status': 'skipped', 'reason': 'Missing credentials', 'platform': 'instagram'}

    print("[instagram] Credentials loaded")

    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        error_msg = f"Video file not found: {video_path}"
        print(f"[instagram] {error_msg}")
        raise FileNotFoundError(error_msg)

    file_size_mb = video_path_obj.stat().st_size / (1024 * 1024)
    print(f"[instagram] Video file found: {video_path}")
    print(f"[instagram] Video size: {file_size_mb:.2f} MB")

    caption_limited = caption[:2200] if len(caption) > 2200 else caption
    print(f"[instagram] Caption length: {len(caption_limited)} characters")

    drive_service = None
    drive_file_id = None

    try:
        print(f"[instagram] Step 1: Uploading to Google Drive for temporary hosting...")

        if not folder_id:
            raise ValueError("GOOGLE_DRIVE_FOLDER_ID not set in .env")

        drive_service = get_drive_service()
        cleanup_stale_temp_files(drive_service, folder_id)
        drive_file_id, video_url = upload_video_to_drive(drive_service, video_path, folder_id)

        print(f"[instagram] Public URL created: {video_url}")

        print(f"[instagram] Step 2: Creating Instagram {media_type} container...")

        container_url = f"https://graph.facebook.com/v21.0/{user_id}/media"
        container_params = {
            'media_type': media_type,
            'video_url': video_url,
            'access_token': access_token
        }

        if not is_story:
            container_params['caption'] = caption_limited
            container_params['share_to_feed'] = 'false'
            container_params['thumb_offset'] = '5000'

        container_response = requests.post(container_url, params=container_params, timeout=60)

        if container_response.status_code != 200:
            error_data = container_response.json() if container_response.text else {}
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            print(f"[instagram] Container creation failed: {error_msg}")
            print(f"[instagram] Full response: {container_response.text[:500]}")

            print("[instagram] Retrying with Instagram Graph API endpoint...")
            container_url = f"https://graph.instagram.com/v21.0/{user_id}/media"
            container_response = requests.post(container_url, params=container_params, timeout=60)

            if container_response.status_code != 200:
                error_data = container_response.json() if container_response.text else {}
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                raise Exception(f"Instagram Container Error: {error_msg}")

        container_id = container_response.json().get('id')
        print(f"[instagram] Container created: {container_id}")

        print("[instagram] Step 3: Waiting for video processing...")
        max_wait = 300
        waited = 0

        while waited < max_wait:
            status_url = f"https://graph.facebook.com/v21.0/{container_id}"
            status_params = {
                'fields': 'status_code',
                'access_token': access_token
            }

            status_response = requests.get(status_url, params=status_params, timeout=30)

            if status_response.status_code != 200:
                status_url = f"https://graph.instagram.com/v21.0/{container_id}"
                status_response = requests.get(status_url, params=status_params, timeout=30)

            status_data = status_response.json()
            status_code = status_data.get('status_code', 'UNKNOWN')

            print(f"[instagram] Status: {status_code} (waited {waited}s)")

            if status_code == 'FINISHED':
                print("[instagram] Video processing complete!")
                break
            elif status_code == 'ERROR':
                error_msg = status_data.get('error_message', 'Video processing failed')
                print(f"[instagram] {error_msg}")
                raise Exception(error_msg)

            time.sleep(10)
            waited += 10

        if waited >= max_wait:
            error_msg = "Video processing timed out"
            print(f"[instagram] {error_msg}")
            raise Exception(error_msg)

        print("[instagram] Step 4: Publishing to Instagram... (Adding 5s buffer)")
        time.sleep(5)

        publish_url = f"https://graph.facebook.com/v21.0/{user_id}/media_publish"
        publish_params = {
            'creation_id': container_id,
            'access_token': access_token
        }

        max_publish_retries = 3
        publish_response = None

        for attempt in range(max_publish_retries):
            publish_response = requests.post(publish_url, params=publish_params, timeout=60)

            if publish_response.status_code == 200:
                break
            else:
                print(f"[instagram] Publish attempt {attempt+1} failed. Retrying...")
                time.sleep(10)

            if attempt == max_publish_retries - 1:
                publish_url = f"https://graph.instagram.com/v21.0/{user_id}/media_publish"
                publish_response = requests.post(publish_url, params=publish_params, timeout=60)

        if not publish_response or publish_response.status_code != 200:
            error_data = publish_response.json() if publish_response and publish_response.text else {}
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            print(f"[instagram] Publish failed after retries: {error_msg}")
            raise Exception(f"Instagram Publish Error: {error_msg}")

        media_id = publish_response.json().get('id')

        print("[instagram] SUCCESS! Video published to Instagram!")
        print(f"[instagram] Media ID: {media_id}")
        print("[instagram] Check your Instagram profile to see the post!")
        print("=" * 60)

        return {
            'id': media_id,
            'platform': 'instagram',
            'status': 'success'
        }

    except Exception as e:
        print("[instagram] ERROR!")
        print(f"[instagram] {str(e)}")
        print("=" * 60)
        raise

    finally:
        if drive_service is not None and drive_file_id is not None:
            delete_drive_file(drive_service, drive_file_id)


if __name__ == '__main__':
    video_file = Path('ielts_short.mp4')
    if video_file.exists():
        try:
            result = upload_to_instagram(str(video_file), "Real Talk with Elara Voss #elaravoss #love")
            print(f"\nSuccess! Result: {result}")
        except Exception as e:
            print(f"\nFailed: {e}")
    else:
        print(f"Video not found: {video_file}")
