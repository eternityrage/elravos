import os
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)


def upload_to_instagram(video_path, caption, is_story=False):

    media_type = "STORIES" if is_story else "REELS"

    print("\n" + "="*60)
    print(f"INSTAGRAM {media_type} UPLOAD")
    print("="*60)

    access_token = (
        os.getenv("INSTAGRAM_ACCESS_TOKEN")
        or
        os.getenv("FACEBOOK_ACCESS_TOKEN")
    )

    user_id = (
        os.getenv("INSTAGRAM_ACCOUNT_ID")
        or
        os.getenv("IG_USER_ID")
    )


    if not access_token:
        raise Exception(
            "Missing access token"
        )

    if not user_id:
        raise Exception(
            "Missing user id"
        )


    video = Path(video_path)

    if not video.exists():
        raise Exception(
            f"Missing file {video_path}"
        )


    print(
        f"Video size:"
        f"{video.stat().st_size/1024/1024:.1f}MB"
    )


    caption = caption[:2200]


    # -------------------------
    # upload tmpfiles
    # -------------------------

    print(
        "[instagram] "
        "Uploading temp..."
    )

    with open(
        video,
        "rb"
    ) as f:

        tmp = requests.post(

            "https://tmpfiles.org/api/v1/upload",

            files={
                "file":
                (
                    "video.mp4",
                    f,
                    "video/mp4"
                )
            },

            timeout=180
        )


    print(
        "TMP RESPONSE:"
    )

    print(
        tmp.text
    )


    if tmp.status_code != 200:

        raise Exception(
            tmp.text
        )


    temp_url = (
        tmp.json()
        ["data"]
        ["url"]
    )


    video_url = temp_url.replace(

        "tmpfiles.org/",

        "tmpfiles.org/dl/"
    )


    print(
        video_url
    )


    # -------------------------
    # create container
    # -------------------------

    container = requests.post(

        f"https://graph.facebook.com/v21.0/{user_id}/media",

        params={

            "media_type":
            media_type,

            "video_url":
            video_url,

            "caption":
            caption,

            "access_token":
            access_token,

            "share_to_feed":
            "false"

        },

        timeout=120
    )


    print(
        "CREATE:"
    )

    print(
        container.text
    )


    if container.status_code != 200:

        raise Exception(
            container.text
        )


    container_id = (

        container.json()

        ["id"]

    )


    print(

        f"Container:"
        f"{container_id}"

    )


    # -------------------------
    # wait
    # -------------------------

    waited = 0

    max_wait = 900

    poll = 60


    while waited < max_wait:


        status = requests.get(

            f"https://graph.facebook.com/v21.0/{container_id}",

            params={

                "fields":

                "status_code,status",

                "access_token":

                access_token

            },

            timeout=60
        )


        raw = status.json()


        print(
            "\nRAW:"
        )

        print(
            raw
        )


        code = (

            raw.get(
                "status_code"
            )

            or

            raw.get(
                "status"
            )

            or

            "UNKNOWN"

        )


        print(

            f"STATUS="
            f"{code}"

            f" waited="
            f"{waited}"

        )


        if code == "FINISHED":

            print(
                "DONE"
            )

            break


        if code == "ERROR":

            raise Exception(
                raw
            )


        # important fix

        if (
            code=="UNKNOWN"

            and

            waited>=300
        ):

            print(

                "UNKNOWN>5min"

                " publish anyway"

            )

            break


        time.sleep(
            poll
        )

        waited += poll



    # -------------------------
    # publish
    # -------------------------

    print(
        "Publishing..."
    )


    publish = requests.post(

        f"https://graph.facebook.com/v21.0/{user_id}/media_publish",

        params={

            "creation_id":

            container_id,

            "access_token":

            access_token

        },

        timeout=120
    )


    print(
        publish.text
    )


    if publish.status_code != 200:

        raise Exception(
            publish.text
        )


    media = (

        publish.json()

        ["id"]

    )


    print(

        "SUCCESS"

    )

    print(

        media

    )


    return {

        "status":

        "success",

        "id":

        media

    }



if __name__ == "__main__":

    video = Path(

        "ielts_short.mp4"

    )


    result = upload_to_instagram(

        str(video),

        "test"

    )


    print(
        result
    )
