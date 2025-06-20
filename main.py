import telebot
import requests
import os
import config
from keep_alive import keep_alive

bot = telebot.TeleBot(config.TOKEN)

def fix_youtube_shorts(url):
    # Convert shorts URL to normal YouTube watch URL
    if "youtube.com/shorts/" in url:
        try:
            video_id = url.split("/shorts/")[1].split("?")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        except IndexError:
            return url
    return url

def get_platform(url):
    url = url.lower()
    if "youtu" in url:
        return "youtube"
    elif "instagram" in url or "insta" in url:
        return "instagram"
    elif "facebook" in url or "fb" in url:
        return "facebook"
    elif "reddit" in url:
        return "reddit"
    else:
        return None

def get_api_url(platform, url):
    if platform == "youtube":
        return f"https://yt.bdbots.xyz/dl?url={url}"
    elif platform == "instagram":
        return f"https://insta.bdbots.xyz/dl?url={url}"
    elif platform == "facebook":
        return f"https://fb.bdbots.xyz/dl?url={url}"
    elif platform == "reddit":
        return f"https://reddit.bdbots.xyz/dl?url={url}"
    return None

@bot.message_handler(commands=['start'])
def start_message(msg):
    bot.send_message(msg.chat.id, "👋 Send me a link from YouTube, Instagram, Facebook, or Reddit and I'll download it for you!")

@bot.message_handler(func=lambda msg: True)
def handle_message(msg):
    raw_url = msg.text.strip()
    # Fix shorts URLs for YouTube
    url = fix_youtube_shorts(raw_url)

    platform = get_platform(url)

    if not platform:
        bot.send_message(msg.chat.id, "❌ Unsupported link. Please send a YouTube, Instagram, Facebook, or Reddit URL.")
        return

    try:
        bot.delete_message(msg.chat.id, msg.message_id)
    except:
        pass

    sent = bot.send_message(msg.chat.id, f"⏳ Downloading from {platform.title()}...")

    try:
        api_url = get_api_url(platform, url)
        res = requests.get(api_url).json()

        # Debug log - uncomment if needed
        # print("API response:", res)

        if "url" not in res:
            bot.edit_message_text("❌ Failed to fetch download link. Try another URL.", sent.chat.id, sent.message_id)
            return

        file_url = res['url']
        title = res.get('title', 'No Title')
        uploader = res.get('uploader', 'Unknown')
        caption_text = res.get('caption', '')

        file_data = requests.get(file_url, stream=True)
        file_size = int(file_data.headers.get('content-length', 0))

        if file_size > config.MAX_FILESIZE:
            bot.edit_message_text("❌ File too large to download.", sent.chat.id, sent.message_id)
            return

        # Guess file extension from url or default to mp4
        ext = file_url.split('.')[-1].split('?')[0]
        if ext.lower() not in ['mp4', 'jpg', 'jpeg', 'png', 'gif', 'mp3', 'mkv']:
            ext = 'mp4'

        filename = f"downloaded_file.{ext}"

        with open(filename, 'wb') as f:
            f.write(file_data.content)

        with open(filename, 'rb') as f:
            caption = f"🎬 *Video by* _{uploader}_\n\n🔗 `{url}`\n```{caption_text}```\n\n@YourBotUsername"
            # Send as video or photo based on extension
            if ext in ['jpg', 'jpeg', 'png', 'gif']:
                bot.send_photo(msg.chat.id, f, caption=caption, parse_mode="Markdown")
            else:
                bot.send_video(msg.chat.id, f, caption=caption, parse_mode="Markdown")

        os.remove(filename)

        try:
            bot.delete_message(sent.chat.id, sent.message_id)
        except:
            pass

        if config.LOG_CHANNEL:
            bot.send_message(
                config.LOG_CHANNEL,
                f"📥 New download from [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})\nPlatform: {platform}\nURL: {url}",
                parse_mode="Markdown"
            )

    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", sent.chat.id, sent.message_id)

# Start keep-alive and bot
keep_alive()
bot.infinity_polling()
