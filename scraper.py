import os
import re
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup

# Aktuelle iDM-URLs für Erdwärme/Sole-Wasser und Produkte
URLS = [
    "https://www.idm-energie.at/terra/",
    "https://www.idm-energie.at/produkte/"
]
HISTORY_FILE = "known_models.json"

# Zugangsdaten aus den GitHub Secrets
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT")

def get_current_models():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    found_models = set()

    for url in URLS:
        try:
            response = requests.get(url, headers=headers, timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Suche in Überschriften, Textabschnitten und Links
            for elem in soup.find_all(["h1", "h2", "h3", "h4", "p", "a", "li"]):
                text = elem.get_text(strip=True)
                if not text or len(text) > 120:
                    continue

                # Filter auf TERRA, Sole, Erdwärme oder SW
                if any(k in text.upper() for k in ["TERRA", "SOLE", "ERDWÄRME", "SW TWIN", "SW MAX"]):
                    # Prüfe auf Leistungsangaben in kW (z. B. "22 kW", "42kW", "50 kW")
                    matches = re.findall(r'(\d+[\.,]?\d*)\s*kW', text, re.IGNORECASE)
                    is_large = False
                    for m in matches:
                        kw_val = float(m.replace(",", "."))
                        if kw_val >= 20:
                            is_large = True
                            found_models.add(f"{text} ({kw_val} kW)")

                    # Auch Modellreihen erfassen, die typischerweise >20kW sind
                    if not is_large and any(kw in text.upper() for kw in ["TWIN", "MAX", "GROSSWÄRME"]):
                        found_models.add(text)

        except Exception as e:
            print(f"Warnung: Fehler beim Abruf von {url}: {e}")

    return sorted(list(found_models))

def send_email_alert(new_items):
    if not all([SMTP_SERVER, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        print("⚠️ E-Mail-Zugangsdaten unvollständig oder nicht gesetzt. Gefundene Neuerungen:\n", new_items)
        return

    subject = "🚨 Neue iDM Sole/Wasser-Wärmepumpe (>20 kW) entdeckt!"
    
    body = (
        "Hallo,\n\n"
        "das automatische Monitoring hat neue Modelle oder Leistungsgrößen auf der iDM-Website gefunden:\n\n"
    )
    for item in new_items:
        body += f"• {item}\n"
    
    body += "\nDirekte Links:\n" + "\n".join(URLS) + "\n\nViele Grüße\nDein iDM Monitor Bot"

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
        print("📧 Benachrichtigungs-E-Mail erfolgreich versendet!")
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
    print(f"Gefundene Modelle aktuell: {len(current_models)}")
    for model in current_models:
        print(f" - {model}")

    new_models = [m for m in current_models if m not in known_models]

    if new_models:
        print(f"\n✨ {len(new_models)} Neuerung(en) gefunden:")
        for nm in new_models:
            print(f" + {nm}")
        send_email_alert(new_models)
        
        # Stand aktualisieren
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(set(known_models + new_models))), f, ensure_ascii=False, indent=2)
    else:
        print("\nKeine neuen Modelle im Vergleich zum letzten Stand.")

if __name__ == "__main__":
    main()
