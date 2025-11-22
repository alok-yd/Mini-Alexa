import os
import re
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# ------------------ ENV + GEMINI CLIENT ------------------ #
load_dotenv()  # loads .env if present

from google import genai  # new Google GenAI SDK

# Client auto-reads GEMINI_API_KEY from environment
# Docs: ai.google.dev/gemini-api/docs/quickstart
client = genai.Client()

app = Flask(__name__)


# ------------------ GEMINI: SHORT ANSWERS ------------------ #
def ask_gemini_short(user_text: str) -> str:
    """
    Ask Gemini for a SHORT answer in Hinglish
    (mix of simple Hindi + English).
    """
    try:
        prompt = (
            "You are a friendly virtual assistant inside a web app.\n"
            "User is an Indian student / normal user.\n\n"
            "LANGUAGE STYLE:\n"
            "- Reply in Hinglish (mix of Hindi + simple English).\n"
            "- Use Roman Hindi (no Devanagari script).\n"
            "- Keep it very clear, casual and motivating.\n"
            "- Avoid very heavy Hindi or Urdu words.\n"
            "- Sound like a helpful friend, not a professor.\n\n"
            "ANSWER RULES:\n"
            "- Maximum 2 sentences. Keep it short.\n"
            "- Give direct, practical answer.\n"
            "- If user asks for definition/explanation, still keep it short.\n"
            "- If user greets you, greet back in Hinglish.\n\n"
            f"User: {user_text}\n"
            "Assistant (Hinglish, max 2 sentences):"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print("Gemini error:", e)
        # Also Hinglish fallback
        return "Yaar abhi mera AI brain connect nahi ho paa raha, thodi der baad try karo."



# ------------------ COMMAND PARSER (TO-DO / OPEN APPS) ------------------ #
def parse_command(user_text: str):
    """
    Detects special commands like:
      - open youtube/google/chatgpt/whatsapp
      - play <song> on youtube
      - remind me in 10 minutes to study
    Returns:
      dict with action info OR None.
    """
    text = user_text.strip()
    low = text.lower()

    # --- Open websites --- #
    if "open youtube" in low:
        return {
            "type": "open_url",
            "url": "https://www.youtube.com/",
            "message": "Opening YouTube in a new tab.",
        }

    if "open google" in low:
        return {
            "type": "open_url",
            "url": "https://www.google.com/",
            "message": "Opening Google search.",
        }

    if "open chatgpt" in low:
        return {
            "type": "open_url",
            "url": "https://chatgpt.com/",
            "message": "Opening ChatGPT.",
        }

    if "open whatsapp" in low or "open whatsapp web" in low:
        return {
            "type": "open_url",
            "url": "https://web.whatsapp.com/",
            "message": "Opening WhatsApp Web.",
        }

    # "open chrome" – we can't open local apps from the browser,
    # but we can approximate by opening Google.
    if "open chrome" in low:
        return {
            "type": "open_url",
            "url": "https://www.google.com/",
            "message": "I can’t open desktop apps directly, but I’ve opened Google in your browser.",
        }

    # --- Play / search YouTube: "play despacito on youtube" --- #
    m_play = re.search(r"play\s+(.+?)\s+on\s+youtube", text, re.IGNORECASE)
    if m_play:
        query = m_play.group(1).strip()
        return {
            "type": "search_youtube",
            "query": query,
            "message": f"Searching YouTube for “{query}”.",
        }

    # Also: "play <something>" (fallback)
    if low.startswith("play "):
        query = text[5:].strip()
        if query:
            return {
                "type": "search_youtube",
                "query": query,
                "message": f"Playing “{query}” on YouTube (search tab opened).",
            }

    # --- Reminders: "remind me in 10 minutes to study" --- #
    # Simple pattern: in X minutes
    m_remind = re.search(
        r"remind me in (\d+)\s+minutes?\s+to\s+(.+)", text, re.IGNORECASE
    )
    if m_remind:
        minutes = int(m_remind.group(1))
        reminder_text = m_remind.group(2).strip()
        return {
            "type": "set_reminder",
            "delay_minutes": minutes,
            "text": reminder_text,
            "message": f"Okay, I’ll set a reminder in {minutes} minute(s) to {reminder_text}. "
                       "Keep this tab open so the alert can fire.",
        }

    # You can add more patterns like:
    # "remind me at 5 pm to study" using dateutil or custom parsing.

    return None  # no special action found


# ------------------ ROUTES ------------------ #


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "I didn’t catch that. Can you type or say it again?"})

    # 1) Check if it's a special command (open url, reminder, play, etc.)
    cmd = parse_command(user_message)
    if cmd:
        message = cmd.pop("message")  # remove text from action, keep rest as metadata
        return jsonify({"reply": message, "action": cmd})

    # 2) Otherwise: ask Gemini for a short answer
    answer = ask_gemini_short(user_message)

    # (Optional) Add small rule-based extras, e.g. time/date:
    lower = user_message.lower()
    if "time" in lower and "?" in lower:
        now = datetime.now().strftime("%I:%M %p")
        answer += f" (By the way, current local time is {now}.)"

    return jsonify({"reply": answer})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
