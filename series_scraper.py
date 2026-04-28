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

    # REMOVE DUPES (faster + safer)
    unique = {}
    for s in all_streams:
        unique[s["url"]] = s
    all_streams = list(unique.values())

    print(f"After removing duplicates: {len(all_streams)}")

    # TEST STREAMS (faster + cleaner)
    print("\nStep 2: Testing streams...")
    working = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=80) as ex:
        futures = {ex.submit(test_stream, s["url"]): s for s in all_streams}

        for f in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            try:
                if f.result():
                    working.append(futures[f])
            except:
                pass

    print(f"\nWorking streams: {len(working)}")

    # OUTPUT FOLDER
    folder = f"IPTV_Output_{datetime.now().strftime('%Y%m%d_%H%M')}"
    os.makedirs(folder, exist_ok=True)

    # ================= CLEAN M3U EXPORT =================
    def write_m3u(path, items):
        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for i in items:
                f.write(f"#EXTINF:-1,{i['title']}\n{i['url']}\n")

    # BUILD FINAL LISTS
    series_list = []
    movies_list = []
    unknown_list = []

    for s in working:
        if s["type"] == "series":
            label = f"{s['clean']} S{s['season'] or 0:02d}E{s['episode'] or 0:02d}"
            series_list.append({"title": label, "url": s["url"]})

        elif s["type"] == "movie":
            movies_list.append({"title": s["clean"], "url": s["url"]})

        else:
            unknown_list.append({"title": s["title"], "url": s["url"]})

    # WRITE FILES
    write_m3u(f"{folder}/series.m3u", series_list)
    write_m3u(f"{folder}/movies.m3u", movies_list)
    write_m3u(f"{folder}/unknown.m3u", unknown_list)

    # FULL PLAYLIST (FOR SMARTERS)
    all_clean = series_list + movies_list + unknown_list
    write_m3u(f"{folder}/playlist.m3u", all_clean)

    print(f"\n✅ DONE - SAVED IN: {folder}")
    print("✔ series.m3u")
    print("✔ movies.m3u")
    print("✔ unknown.m3u")
    print("✔ playlist.m3u (USE THIS IN IPTV SMARTERS)")
