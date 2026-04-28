import requests
import re
import os
import json
from datetime import datetime
from tqdm import tqdm
import concurrent.futures

print("=== Advanced IPTV Series / VOD Scraper ===\n")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

urls_to_scrape = [
    "https://iptv-org.github.io/iptv/index.m3u",
    "https://iptv-org.github.io/iptv/categories/series.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    "https://raw.githubusercontent.com/jromero88/iptv/master/VOD.m3u",
]

# ---------------- CLEAN TITLE ----------------
def clean_title(title):
    title = re.sub(r's\d{1,2}e\d{1,2}', '', title, flags=re.I)
    title = re.sub(r'\d{1,2}x\d{1,2}', '', title, flags=re.I)
    title = re.sub(r'season \d+', '', title, flags=re.I)
    title = re.sub(r'episode \d+', '', title, flags=re.I)
    title = re.sub(r'\(.*?\)', '', title)
    return title.strip()

# ---------------- CLASSIFY ----------------
def classify(title):
    text = title.lower()

    match = re.search(r's(\d{1,2})e(\d{1,2})', text)
    if match:
        return "series", int(match.group(1)), int(match.group(2)), clean_title(title)

    match = re.search(r'(\d{1,2})x(\d{1,2})', text)
    if match:
        return "series", int(match.group(1)), int(match.group(2)), clean_title(title)

    if "season" in text or "series" in text:
        return "series", None, None, clean_title(title)

    if any(x in text for x in ["movie", "1080p", "720p", "bluray", "webrip"]):
        return "movie", None, None, clean_title(title)

    return "unknown", None, None, clean_title(title)

# ---------------- STREAM TEST ----------------
def test_stream(url, timeout=10, retries=2):
    for _ in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
            if r.status_code in (200, 206):
                for chunk in r.iter_content(1024):
                    if chunk:
                        return True
        except:
            pass
    return False

# ---------------- PARSE ----------------
def download_and_parse(url):
    streams = []
    try:
        print(f"[+] Downloading: {url}")
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()

        lines = r.text.splitlines()

        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                title_match = re.search(r',(.+)', lines[i])
                title = title_match.group(1).strip() if title_match else "Unknown"

                if i + 1 < len(lines):
                    link = lines[i + 1].strip()

                    if link and not link.startswith("#"):
                        t, season, ep, clean = classify(title)

                        streams.append({
                            "title": title,
                            "clean": clean,
                            "url": link,
                            "type": t,
                            "season": season,
                            "episode": ep
                        })

    except Exception as e:
        print(f"[-] Error: {e}")

    return streams

# ================= MAIN =================
if __name__ == "__main__":
    all_streams = []

    print("Step 1: Scraping...\n")
    for url in urls_to_scrape:
        all_streams.extend(download_and_parse(url))

    print(f"\nFound {len(all_streams)} streams")

    # REMOVE DUPES
    unique = {}
    for s in all_streams:
        unique[s["url"]] = s
    all_streams = list(unique.values())

    print(f"After removing duplicates: {len(all_streams)}")

    # TEST STREAMS
    print("\nStep 2: Testing streams...")
    working = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(test_stream, s["url"]): s for s in all_streams}

        for f in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            s = futures[f]
            try:
                if f.result():
                    working.append(s)
            except:
                pass

    print(f"\nWorking streams: {len(working)}")

    # GROUP
    grouped = {"series": {}, "movies": {}, "unknown": []}

    for s in working:
        if s["type"] == "series":
            grouped["series"].setdefault(s["clean"], {}).setdefault(s["season"], []).append(s)
        elif s["type"] == "movie":
            grouped["movies"].setdefault(s["clean"], []).append(s)
        else:
            grouped["unknown"].append(s)

    # OUTPUT FOLDER
    folder = f"IPTV_Output_{datetime.now().strftime('%Y%m%d_%H%M')}"
    os.makedirs(folder, exist_ok=True)

    # ---------------- SERIES M3U ----------------
    with open(f"{folder}/series.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for show, seasons in grouped["series"].items():
            for season in sorted(seasons.keys()):
                eps = seasons[season]
                eps.sort(key=lambda x: (x["episode"] or 0))

                for e in eps:
                    label = f"{show} S{season or 0:02d}E{e['episode'] or 0:02d}"
                    f.write(f"#EXTINF:-1,{label}\n{e['url']}\n")

    # ---------------- MOVIES M3U ----------------
    with open(f"{folder}/movies.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, items in grouped["movies"].items():
            for i in items:
                f.write(f"#EXTINF:-1,{name}\n{i['url']}\n")

    # ---------------- UNKNOWN ----------------
    with open(f"{folder}/unknown.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for i in grouped["unknown"]:
            f.write(f"#EXTINF:-1,{i['title']}\n{i['url']}\n")

    print(f"\n✅ Done. Files saved in: {folder}")
    print("   • series.m3u")
    print("   • movies.m3u")
    print("   • unknown.m3u")