def upload_to_instagram(video_path, caption, is_story=False):
    media_type = 'STORIES' if is_story else 'REELS'
    BASE_URL = "https://graph.facebook.com/v21.0"

    print("\n" + "="*60)
    print(f"INSTAGRAM {media_type} UPLOAD STARTING")
    print("="*60)

    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN') or os.getenv('FACEBOOK_ACCESS_TOKEN')
    user_id = os.getenv('INSTAGRAM_ACCOUNT_ID') or os.getenv('IG_USER_ID')

    if not access_token:
        raise Exception("Missing access token")

    if not user_id:
        raise Exception("Missing Instagram account ID")

    compressed = compress_for_instagram(video_path)
    upload_path = compressed

    try:
        # ---------------------------------------
        # STEP 1: Upload to temp host
        # ---------------------------------------

        print("[instagram] Uploading to temporary host...")
        video_url = upload_to_temporary_host(upload_path)

        print(f"[instagram] Video URL:")
        print(video_url)

        # ---------------------------------------
        # STEP 2: Create container
        # ---------------------------------------

        container_url = f"{BASE_URL}/{user_id}/media"

        params = {
            "media_type": media_type,
            "video_url": video_url,
            "access_token": access_token
        }

        if not is_story:
            params["caption"] = caption[:2200]
            params["share_to_feed"] = "false"
            params["thumb_offset"] = "5000"

        response = requests.post(
            container_url,
            params=params,
            timeout=120
        )

        print("\nCREATE RESPONSE:")
        print(response.text)

        if response.status_code != 200:
            raise Exception(response.text)

        container_id = response.json()["id"]

        print(f"""
Container created:
{container_id}
        """)

        # ---------------------------------------
        # STEP 3: Poll status
        # ---------------------------------------

        max_wait = 900
        poll_interval = 60
        waited = 0

        processing_done = False

        while waited < max_wait:

            status_url = f"{BASE_URL}/{container_id}"

            status = requests.get(
                status_url,
                params={
                    "fields":
                    "status_code,status",
                    "access_token":
                    access_token
                },
                timeout=60
            )

            raw = status.json()

            print("\n====================")
            print("RAW STATUS:")
            print(raw)
            print("====================")

            status_code = (
                raw.get("status_code")
                or raw.get("status")
                or "UNKNOWN"
            )

            print(
                f"[instagram] "
                f"Status={status_code} "
                f"waited={waited}s"
            )

            if status_code == "FINISHED":

                print(
                    "[instagram] "
                    "Processing complete"
                )

                processing_done = True
                break


            elif status_code == "ERROR":

                raise Exception(
                    f"Processing failed:\n{raw}"
                )


            elif waited >= 300 and status_code == "UNKNOWN":

                print(
                    "[instagram] "
                    "UNKNOWN >5min "
                    "Proceeding anyway..."
                )

                break


            time.sleep(
                poll_interval
            )

            waited += poll_interval


        # ---------------------------------------
        # STEP 4: Publish
        # ---------------------------------------

        print(
            "\nPublishing..."
        )

        time.sleep(5)

        publish_url = (
            f"{BASE_URL}/"
            f"{user_id}/media_publish"
        )

        publish = requests.post(
            publish_url,
            params={
                "creation_id":
                container_id,

                "access_token":
                access_token
            },
            timeout=120
        )

        print(
            "\nPUBLISH RESPONSE:"
        )

        print(
            publish.text
        )

        if publish.status_code != 200:

            raise Exception(
                publish.text
            )


        media_id = publish.json()["id"]

        print(
            "\nSUCCESS"
        )

        print(
            f"Media ID:"
            f"{media_id}"
        )

        return {

            "status":
            "success",

            "platform":
            "instagram",

            "id":
            media_id,

            "processing_done":
            processing_done
        }


    except Exception as e:

        print(
            "\nERROR:"
        )

        print(
            str(e)
        )

        raise


    finally:

        cleanup_compressed(
            upload_path
        )
