import os
import re
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup

URLS = [
    "https://www.idm-energie.at/terra/",
    "https://www.idm-energie.at/produkte/"
]
HISTORY_FILE = "known_models.json"

SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT")

def get_current_models():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    found_models = set()

    for url in URLS:
        try:
            response = requests.get(url, headers=headers, timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for elem in soup.find_all(["h1", "h2", "h3", "h4", "p", "a", "li"]):
                text = elem.get_text(strip=True)
                if not text or len(text) > 120:
                    continue

                if any(k in text.upper() for k in ["TERRA", "SOLE", "ERDWÄRME", "SW TWIN", "SW MAX"]):
                    matches = re.findall(r'(\d+[\.,]?\d*)\s*kW', text, re.IGNORECASE)
                    is_large = False
                    for m in matches:
                        kw_val = float(m.replace(",", "."))
                        if kw_val >= 20:
                            is_large = True
                            found_models.add(f"{text} ({kw_val} kW)")

                    if not is_large and any(kw in text.upper() for kw in ["TWIN", "MAX", "GROSSWÄRME"]):
                        found_models.add(text)

        except Exception as e:
            print(f"Fehler beim Abruf von {url}: {e}")

    return sorted(list(found_models))

def send_email_alert(new_items):
    if not all([SMTP_SERVER, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        print("⚠️ E-Mail-Zugangsdaten unvollständig. Gefundene Neuerungen:\n", new_items)
        return

    subject = "🚨 Neue iDM Sole/Wasser-Wärmepumpe (>20 kW) entdeckt!"
    body = "Hallo,\n\ndas Monitoring hat folgende Modelle auf der iDM-Website gefunden:\n\n"
    for item in new_items:
        body += f"• {item}\n"
    body += "\nLinks:\n" + "\n".join(URLS) + "\n\nDein iDM Monitor Bot"

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECIPIENT
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("📧 E-Mail erfolgreich versendet!")
    except Exception as e:
        print(f"❌ Fehler beim E-Mail-Versand: {e}")

def main():
    known_models = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                known_models = json.load(f)
        except Exception:
            known_models = []

    current_models = get_current_models()
    print(f"Gefundene Modelle: {len(current_models)}")
    for model in current_models:
        print(f" - {model}")

    new_models = [m for m in current_models if m not in known_models]

    if new_models:
        print(f"\n✨ Neuerungen: {new_models}")
        send_email_alert(new_models)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(set(known_models + new_models))), f, ensure_ascii=False, indent=2)
    else:
        print("\nKeine neuen Modelle.")

if __name__ == "__main__":
    main()
