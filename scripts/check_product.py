import hashlib
import json
import os
import sys
import requests
from bs4 import BeautifulSoup

URL = "https://www.stiebel-eltron.de/de/produkte/heizen-und-kuehlen/waermepumpe/erdwaermepumpe/p/208906.html"
DATA_FILE = "data/stiebel_208906_specs.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_data():
    res = requests.get(URL, headers=HEADERS, timeout=20)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    
    extracted = {
        "url": URL,
        "product_id": "208906",
        "title": soup.title.string.strip() if soup.title else "",
        "specs": {},
        "documents": []
    }
    
    # 1. Technische Tabellen / Daten auslesen
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            if len(cols) == 2:
                extracted["specs"][cols[0]] = cols
                
    # 2. PDF-Downloads / Datenblätter erfassen
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            link = href if href.startswith("http") else f"https://www.stiebel-eltron.de{href}"
            extracted["documents"].append({
                "name": a.get_text(strip=True) or os.path.basename(href),
                "url": link
            })
            
    # Sortieren für konsistente Hashes / Diffs
    extracted["documents"] = sorted(extracted["documents"], key=lambda x: x["url"])
    return extracted

def main():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    new_data = fetch_data()
    
    # Speichern als formatiertes JSON
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
        
    print(f"Daten für 208906 erfolgreich aktualisiert ({len(new_data['specs'])} Kennwerte, {len(new_data['documents'])} PDFs).")

if __name__ == "__main__":
    main()
