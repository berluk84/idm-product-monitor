import os
import re
import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.idm-energie.at/produkte/waermepumpen/sole-wasser-waermepumpen/"
HISTORY_FILE = "known_models.json"
WEBHOOK_URL = os.environ.get("ALERT_WEBHOOK_URL")

def get_current_models():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(URL, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    found_models = set()

    for elem in soup.find_all(["h2", "h3", "h4", "p", "a"]):
        text = elem.get_text(strip=True)
        if "TERRA" in text or "Sole" in text or "SW" in text:
            matches = re.findall(r'(\d+[\.,]?\d*)\s*kW', text, re.IGNORECASE)
            for m in matches:
                kw_val = float(m.replace(",", "."))
                if kw_val >= 20:
                    found_models.add(f"{text} ({kw_val} kW)")
            
            if any(kw in text.upper() for kw in ["TWIN", "MAX", "GROSSWÄRMEPUMPE"]):
                found_models.add(text)

    return sorted(list(found_models))

def send_alert(new_items):
    if not WEBHOOK_URL:
        print("Kein Webhook konfiguriert. Gefundene Neuerungen:\n", new_items)
        return

    message = "🚨 **Neue iDM Sole/Wasser-Wärmepumpe (>20 kW) entdeckt!**\n\n"
    message += "\n".join([f"- {item}" for item in new_items])
    message += f"\n\n🔗 Link: {URL}"

    requests.post(WEBHOOK_URL, json={"content": message})

def main():
    known_models = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            known_models = json.load(f)

    current_models = get_current_models()
    print(f"Gefundene Modelle aktuell: {len(current_models)}")

    new_models = [m for m in current_models if m not in known_models]

    if new_models:
        print(f"Neuerungen gefunden: {new_models}")
        send_alert(new_models)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(set(known_models + new_models))), f, ensure_ascii=False, indent=2)
    else:
        print("Keine neuen Modelle gefunden.")

if __name__ == "__main__":
    main()
