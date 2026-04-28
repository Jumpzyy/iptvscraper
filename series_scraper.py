import requests
import re
import os
from datetime import datetime
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

print("=== FAST IPTV SERIES / VOD SCRAPER ===\n")

HEADERS = {"User-Agent": "Mozilla/5.0"}

URLS = [
    "https://iptv-org.github.io/iptv/index.m3u",
    "https://iptv-org.github.io/iptv/categories/series.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
]

# ---------------- CLEAN ----------------
def clean_title(t):
    t = re.sub(r's\d{1,2}e\d{1,2}', '', t, flags=re.I)
    t = re.sub(r'\d{1,2}x\d{1,2}', '', t, flags=re.I)
    t = re.sub(r'season \d+|episode \d+', '', t, flags=re.I)
    t = re.sub(r'\(.*?\)', '', t)
    return t.strip()

# ---------------- CLASSIFY ----------------
def classify(t):
    low = t.lower()

    if re.search(r's\d{1,2}e\d{1,2}', low) or re.search(r'\d{1,2}x\d{1,2}', low):
        m = re.search(r's(\d{1,2})e(\d{1,2})|(\d{1,2})x(\d{1,2})', low)
        if m:
            s = m.group(1) or m.group(3)
            e = m.group(2) or m.group(4)
            return "series", int(s), int(e), clean_title(t)

    if any(x in low for x in ["movie", "1080p", "720p", "bluray"]):
        return "movie", None, None, clean_title(t)

    return "unknown", None, None, clean_title(t)

# ---------------- PARSE ----------------
def parse(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        lines = r.text.splitlines()
        out = []

        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                title = lines[i].split(",", 1)[-1]
                if i + 1 < len(lines):
                    link = lines[i + 1].strip()
                    if link.startswith("http"):
                        t, s, e, clean = classify(title)
                        out.append((title, clean, link, t, s, e))
        return out
    except:
        return []

# ---------------- FAST STREAM CHECK (NO DOWNLOAD) ----------------
def alive(url):
    try:
        r = requests.head(url, headers=HEADERS, timeout=4, allow_redirects=True)
        if r.status_code in [200, 206]:
            return True
    except:
        pass

    try:
        r = requests.get(url, headers=HEADERS, timeout=4, stream=True)
        return r.status_code in [200, 206]
    except:
        return False

# ---------------- MAIN ----------------
all_streams = []

print("Scraping...")
for u in URLS:
    all_streams += parse(u)

# dedupe early
seen = set()
unique = []
for s in all_streams:
    if s[2] not in seen:
        seen.add(s[2])
        unique.append(s)

print(f"Total streams: {len(unique)}")

print("\nTesting (FAST MODE)...")
working = []

with ThreadPoolExecutor(max_workers=80) as ex:
    fut = {ex.submit(alive, s[2]): s for s in unique}

    for f in tqdm(as_completed(fut), total=len(fut)):
        s = fut[f]
        try:
            if f.result():
                working.append(s)
        except:
            pass

print(f"Working: {len(working)}")

# ---------------- GROUP ----------------
series, movies, unknown = [], [], []

for t, clean, url, typ, s, e in working:
    if typ == "series":
        series.append((clean, s, e, url))
    elif typ == "movie":
        movies.append((clean, url))
    else:
        unknown.append((t, url))

# ---------------- OUTPUT ----------------
folder = f"IPTV_CLEAN_{datetime.now().strftime('%Y%m%d_%H%M')}"
os.makedirs(folder, exist_ok=True)

def write_m3u(path, items, mode):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        if mode == "series":
            items.sort(key=lambda x: (x[0], x[1] or 0, x[2] or 0))
            for c, s, e, u in items:
                f.write(f"#EXTINF:-1,{c} S{s or 0:02d}E{e or 0:02d}\n{u}\n")

        elif mode == "movies":
            for c, u in items:
                f.write(f"#EXTINF:-1,{c}\n{u}\n")

        else:
            for t, u in items:
                f.write(f"#EXTINF:-1,{t}\n{u}\n")

write_m3u(f"{folder}/series.m3u", series, "series")
write_m3u(f"{folder}/movies.m3u", movies, "movies")
write_m3u(f"{folder}/unknown.m3u", unknown, "unknown")

# SMARTERS MASTER LIST
with open(f"{folder}/playlist.m3u", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for c, s, e, u in series:
        f.write(f"#EXTINF:-1,{c}\n{u}\n")
    for c, u in movies:
        f.write(f"#EXTINF:-1,{c}\n{u}\n")
    for t, u in unknown:
        f.write(f"#EXTINF:-1,{t}\n{u}\n")

print("\nDONE")
print("✔ series.m3u")
print("✔ movies.m3u")
print("✔ unknown.m3u")
print("✔ playlist.m3u (use in Smarters)")
