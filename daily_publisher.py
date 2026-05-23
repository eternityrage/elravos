import os
import json
import glob
import random
import requests
import shutil
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
from pathlib import Path
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Import upload functions
try:
    from upload.upload_instagram import upload_to_instagram
    from upload.upload_threads import upload_to_threads
    from upload.upload_facebook import upload_to_facebook, upload_to_facebook_story
    from upload.upload_to_youtube import upload_to_youtube
except ImportError as e:
    print(f"Error importing upload modules: {e}")
    # Still want to proceed or stop?
    pass

PROCESSED_DIR = "Processed_Videos"
PUBLISHED_LOG = "published_videos.json"

def get_already_published():
    if os.path.exists(PUBLISHED_LOG):
        with open(PUBLISHED_LOG, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def get_repost_counts():
    """Count how many times each video has been posted."""
    published = get_already_published()
    counts = {}
    for entry in published:
        vname = entry.get("video_name", "")
        counts[vname] = counts.get(vname, 0) + 1
    return counts

def mark_as_published(video_name, metadata):
    published = get_already_published()
    published.append({
        "video_name": video_name,
        "metadata": metadata
    })
    with open(PUBLISHED_LOG, 'w', encoding='utf-8') as f:
        json.dump(published, f, indent=4)

def select_video(specific_video=None):
    published = [item["video_name"] for item in get_already_published()]
    all_videos = sorted(glob.glob(os.path.join(PROCESSED_DIR, "*.mp4")))

    if specific_video:
        # specific_video might be a full path or just a filename
        if os.path.exists(specific_video):
            # It's a full path
            vid_path = specific_video
            name = os.path.basename(specific_video)
        else:
            # It's just a filename, join with PROCESSED_DIR
            vid_path = os.path.join(PROCESSED_DIR, specific_video)
            name = specific_video

        if os.path.exists(vid_path):
            if name in published:
                post_count = sum(1 for p in published if p == name)
                print(f"🔄 Video {name} was already published ({post_count}x) - Re-publishing (recycling)")
            return vid_path, name
        else:
            print(f"❌ Error: Specific video {name} not found")
            return None, None

    # Find unpublished videos first
    unpublished = [(vid, os.path.basename(vid)) for vid in all_videos if os.path.basename(vid) not in published]

    if unpublished:
        vid, name = unpublished[0]
        return vid, name

    # All videos published - use weighted random selection (less posted = more likely)
    if all_videos:
        repost_counts = get_repost_counts()
        weights = []
        for vid in all_videos:
            name = os.path.basename(vid)
            count = repost_counts.get(name, 0)
            weight = max(1, 1000 // (3 ** min(count, 6)))
            weights.append(weight)

        selected_vid = random.choices(all_videos, weights=weights, k=1)[0]
        name = os.path.basename(selected_vid)
        post_count = repost_counts.get(name, 0)
        print(f"🎲 All videos published. Weighted random reuse (posted {post_count}x): {name}")
        return selected_vid, name

    return None, None

def generate_caption():
    import random
    import time

    api_key = os.getenv("POLLINATIONS_API_KEY")
    model = os.getenv("AI_MODEL", "openai")

    fallback_titles = [
        "He Left Me — Here's How I Survived the Pain",
        "The Hardest Truth About Love Nobody Tells You",
        "Why You Keep Falling for the Wrong Person",
        "How to Heal a Broken Heart — Step by Step",
        "Signs You're Settling for Less Than You Deserve",
        "The Moment I Realized My Worth After Heartbreak",
        "Why Men Pull Away — What's Really Going On",
        "How to Stop Overthinking in a Relationship",
        "The 5 Stages of a Breakup You Need to Know",
        "Trust Your Gut — The Red Flags I Ignored",
        "How to Love Yourself First (Before Someone Else)",
        "Why Silence Speaks Louder Than Words in Love",
        "The Pain of Loving Someone Who Couldn't Love You Back",
        "How to Move On When You Still Love Them",
        "You Are Not Too Much — You Were Just With the Wrong Person",
    ]

    fallback_descriptions = [
        "He left and I thought my world was over. But here's what nobody tells you about heartbreak — it's also where you find yourself again. I cried, I spiraled, I questioned everything. And then slowly, I started to rebuild. The pain doesn't disappear overnight, but every day you choose yourself, you get a little stronger. If you're going through a breakup right now, I see you. And I promise you will get through this. Drop a 💔 if you've been here too. #elaravoss #heartbreak #breakup #healing #love #relationshipadvice #movingon #selflove #emotionalhealing #pain #growth #mentalhealth #womenempowerment #toxicrelationships #lettinggo",
        "The hardest truth about love is that loving someone doesn't mean they're good for you. You can pour your whole heart into someone and still end up empty. I learned this the hard way — giving everything to a person who couldn't meet me halfway. But that experience taught me something valuable: your love is precious, and not everyone deserves it. Save your energy for someone who shows up the same way you do. Like if this hit home 💔 #elaravoss #lovelessons #relationshiptruth #heartbreak #selfworth #toxiclove #emotionalhealth #datingadvice #healingjourney #boundaries #selfrespect #love #growth #wisdom",
        "Why do we keep falling for the same type of person over and over? It's not bad luck — it's a pattern rooted in what we think we deserve. I used to chase emotionally unavailable men because deep down I didn't believe I was worthy of consistent love. Breaking the cycle starts with looking inward. Ask yourself: what am I accepting that I don't really want? Comment 'same' if you've been guilty of this too 💫 #elaravoss #relationships #datingpatterns #selfawareness #emotionalhealth #toxicpatterns #love #healing #psychologyofattraction #selfgrowth",
        "Healing a broken heart isn't linear. Some days you feel like you're finally okay, and the next day you're crying in the shower. I've been there more times than I'd like to admit. But here's what actually helped me: letting myself feel every emotion without judgment, cutting off contact, surrounding myself with people who reminded me of my worth, and giving it time — real time. There's no shortcut through pain, but there is a way through. Save this for when you need the reminder. 💪 #elaravoss #heartbreak #healing #selflove #breakupadvice #emotionalhealth #movingon #mentalhealth #women #love #grief #healingjourney",
        "You deserve someone who chooses you every single day — not just when it's convenient. I used to accept breadcrumbs and call it love. I made excuses for behavior that deep down I knew was wrong. If you're constantly questioning where you stand with someone, that's your answer. Real love doesn't leave you confused. It feels safe, consistent, and peaceful. Not perfect — but peaceful. Like if you're done settling for less 💯 #elaravoss #selfworth #relationshipadvice #love #boundaries #toxicrelationships #dating #emotionalhealth #knowyourworth #selflove #respect #healing",
        "Why do men pull away when things get good? I've experienced this more than once and here's what I've learned: it's usually about them, not you. Some people get scared when emotions get real. They sabotage good things because intimacy terrifies them. Does it hurt? Absolutely. But understanding that their pulling away is about their own fears helps you stop making it mean something's wrong with you. Have you dealt with this? Comment below 👇 #elaravoss #relationships #datingadvice #men #emotionalintimacy #love #heartbreak #attachmentstyles #psychology #healing",
        "Overthinking will kill your peace faster than any external situation ever could. I used to replay conversations in my head, wondering what I should have said differently. analyzing every text, every tone shift, every pause. It was exhausting. The truth is, if someone wants to be with you, they will make it clear. You don't need to decode mixed signals. If it's confusing, it's a no. Save this for when your mind starts spiraling. 🧠 #elaravoss #overthinking #anxiety #relationships #mentalhealth #peaceofmind #lettinggo #selflove #dating #emotionalhealth",
        "There are 5 stages of a breakup and nobody tells you about the ones in between. Denial, anger, bargaining, depression, acceptance — but what about the stage where you text them at 2 AM? Or the stage where you convince yourself you're fine when you're not? I've been through every single one. The most important thing is to be gentle with yourself. You're not broken. You're just healing. Which stage are you in right now? 💌 #elaravoss #breakup #heartbreak #healing #grief #emotionalhealth #mentalhealth #selflove #stagesofgrief #movingon #love",
        "I ignored so many red flags because I was wearing rose-colored glasses. 'He's just busy.' 'He's not good with words.' 'He'll change.' Sound familiar? Looking back, I realize my gut was trying to protect me, but I didn't want to listen. Trust your intuition — it knows when something is off even when your heart doesn't want to admit it. If you've ever ignored red flags too, drop an 🚩 below. #elaravoss #redflags #relationshipadvice #trustyourgut #toxicrelationships #love #dating #selfawareness #emotionalhealth #healing #boundaries",
        "Learning to love yourself first sounds like a cliché until you actually do it. I used to think love meant finding someone to complete me. But the truth is, no one can fill a void you haven't learned to sit with yourself. So I started taking myself on dates, journaling, setting boundaries, and saying no to things that drained me. It was uncomfortable at first. But now? I'd rather be alone than with someone who makes me feel lonely. Share this with someone who needs to hear it 💖 #elaravoss #selflove #healing #loveyourself #boundaries #emotionalhealth #growth #personalgrowth #mentalhealth #relationships",
        "Silence says what words cannot. When someone suddenly stops texting, when the energy shifts, when you feel the distance growing — believe it. I used to chase explanations, demand closure. But I learned that silence is an answer too. Not every situation deserves your words. Sometimes the most powerful thing you can do is walk away without a scene. Let your absence speak for itself. Have you ever had to walk away in silence? 🤐 #elaravoss #silence #relationships #datingadvice #emotionalhealth #selfrespect #lettinggo #boundaries #love #heartbreak",
        "Loving someone who couldn't love me back the way I needed was the most painful lesson of my life. I gave and gave until I had nothing left. And the hardest part was realizing that my love alone wasn't enough to fix things. You cannot love someone into loving you the way you deserve. Some people just aren't capable of giving what you need, and that's not your fault. It took me a long time to understand that. If you've been here, you're not alone. 💔 #elaravoss #unrequitedlove #heartbreak #emotionalhealth #healing #selflove #love #relationships #movingon #toxiclove",
        "How do you move on when you still love them? This is the question that kept me up at night. The answer isn't to stop loving them — it's to start loving yourself more. You don't move on by forgetting. You move on by choosing your peace over the chaos. By accepting that loving someone doesn't mean you should be with them. By realizing your future happiness is worth more than a past that already ended. Save this for when you need strength. 💪 #elaravoss #movingon #heartbreak #healing #selflove #breakup #lettinggo #growth #emotionalhealth #peace #love",
        "You are not too much. You are not too emotional. You are not too sensitive. You were just with someone who couldn't handle the depth of your heart. I spent years trying to shrink myself so I wouldn't scare people away. Making myself smaller, quieter, easier to handle. But the right person won't ask you to dim your light. They'll hold space for all of you — the tears, the passion, the questions, the love. Never apologize for feeling deeply. Like if you needed to hear this today 🌹 #elaravoss #toomuch #emotional #highlysensitive #selflove #relationships #love #healing #mentalhealth #empathy #worth",
    ]

    if not api_key:
        chosen_title = random.choice(fallback_titles)
        chosen_desc = random.choice(fallback_descriptions)
        print("Warning: POLLINATIONS_API_KEY not found. Using fallback captions.")
        return chosen_title, chosen_desc

    vibes = [
        "raw and honest — speak from the heart like you're confiding in a close friend",
        "relatable and real — describe feelings every woman has experienced in love",
        "emotional and vulnerable — share the pain and the growth that came from heartbreak",
        "empowering and uplifting — remind her that she is strong and worthy of real love",
        "soothing and comforting — be the voice that tells her everything will be okay",
        "sassy and confident — speak with the energy of someone who learned her worth",
        "reflective and wise — share hard-won lessons about love, loss, and self-discovery",
    ]
    chosen_vibe = random.choice(vibes)

    prompt = (
        f"Write a completely unique, long, and captivating title and description for a short video "
        f"for the page 'Elara Voss'. "
        f"Elara Voss is a woman who speaks openly about love, relationships, breakups, heartbreak, and emotional healing. "
        f"She shares her personal experiences, the hard lessons she learned, and the wisdom she gained from going through pain. "
        f"She is authentic, vulnerable, and deeply relatable — a voice for every woman who has loved, lost, and found herself again. "
        f"Speak as Elara Voss — first person, intimate, and emotionally honest. "
        f"Make the vibe {chosen_vibe}. "
        f"The description should be LONG (4-6 sentences minimum), deeply emotional, and relatable. "
        f"Include engagement calls-to-action such as: "
        f"- Like if this spoke to your soul! "
        f"- Comment your story below, I want to hear it! "
        f"- Share this with a friend who needs to hear this! "
        f"- Follow Elara Voss for more real talk on love and healing! "
        f"Include relevant hashtags in ALL LOWERCASE such as #elaravoss #love #relationships #heartbreak #healing #selflove #breakup #emotionalhealth #datingadvice #movingon #toxicrelationships #growth #women #mentalhealth #real. "
        f"Return ONLY a valid JSON object in this format: {{\"title\": \"<title>\", \"description\": \"<description>\"}} "
        f"Do not include any other text or markdown block backticks."
    )

    url = "https://gen.pollinations.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "seed": random.randint(1, 999999)
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)

        chosen_title = random.choice(fallback_titles)
        chosen_desc = random.choice(fallback_descriptions)
        return result.get("title", chosen_title), result.get("description", chosen_desc)
    except Exception as e:
        print(f"Error generating caption: {e}")
        return random.choice(fallback_titles), random.choice(fallback_descriptions)

def main():
    print("=" * 60)
    print("🚀 DAILY AUTOMATION STARTING")
    print("=" * 60)
    
    specific_video = sys.argv[1] if len(sys.argv) > 1 else None
    video_path, video_name = select_video(specific_video)
    if not video_path:
        print("✅ No new videos found to publish. Exiting.")
        return
        
    print(f"👉 Selected Video: {video_name}")
    print("🧠 Generating caption via Pollination AI...")
    title, description = generate_caption()
    
    print(f"📝 Title: {title}")
    print(f"📝 Description:\n{description}")
    
    # Combined caption for platforms that use a single text field
    combined_caption = f"{title}\n\n{description}"
    
    success_flags = {
        "instagram_reel": False,
        "instagram_story": False,
        "facebook_reel": False,
        "facebook_story": False,
        "threads": False,
        "youtube": False
    }
    
    # Instagram Reels
    try:
        result = upload_to_instagram(video_path, combined_caption, is_story=False)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Instagram Reel: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["instagram_reel"] = True
    except Exception as e:
        print(f"❌ Instagram Reel upload failed: {e}")
        
    # Instagram Stories
    try:
        result = upload_to_instagram(video_path, combined_caption, is_story=True)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Instagram Story: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["instagram_story"] = True
    except Exception as e:
        print(f"❌ Instagram Story upload failed: {e}")
        
    # Facebook Reels
    try:
        result = upload_to_facebook(video_path, description, title=title)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Facebook Reel: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["facebook_reel"] = True
    except Exception as e:
        print(f"❌ Facebook Reel upload failed: {e}")
        
    # Facebook Stories
    try:
        result = upload_to_facebook_story(video_path)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Facebook Story: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["facebook_story"] = True
    except Exception as e:
        print(f"❌ Facebook Story upload failed: {e}")
        
    # Threads
    try:
        result = upload_to_threads(video_path, combined_caption)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Threads: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["threads"] = True
    except Exception as e:
        print(f"❌ Threads upload failed: {e}")
        
    # YouTube Shorts
    try:
        upload_to_youtube(video_path, title, description, tags=["elara voss", "love", "relationships", "heartbreak", "healing", "breakup", "self love", "dating advice", "emotional health", "moving on", "toxic relationships", "women", "mental health", "real talk", "personal growth"])
        success_flags["youtube"] = True
    except Exception as e:
        print(f"❌ YouTube upload failed: {e}")
        
    # Record as published regardless of partial success,
    # to avoid repeating the same video. Alternatively, only record if fully successful.
    print("\n✅ Marking video as published.")
    
    # Check if this is a recycled video (already in published_videos.json)
    published_list = get_already_published()
    is_recycled = any(item["video_name"] == video_name for item in published_list)
    
    if is_recycled:
        print(f"   🔄 This is a recycled video (re-publishing)")
    
    mark_as_published(video_name, {
        "title": title,
        "description": description,
        "success_flags": success_flags,
        "recycled": is_recycled
    })
    
    # Move the published video to Published_Videos folder
    published_dir = "Published_Videos"
    if not os.path.exists(published_dir):
        os.makedirs(published_dir)
        
    try:
        dest_path = os.path.join(published_dir, video_name)
        shutil.move(video_path, dest_path)
        print(f"📦 Moved published video to {dest_path}")
    except Exception as e:
        print(f"❌ Failed to move published video: {e}")
    
    print("🎉 DAILY AUTOMATION COMPLETE")

if __name__ == "__main__":
    main()
