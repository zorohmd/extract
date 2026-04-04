import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import base64
from urllib.parse import urlparse, parse_qs, unquote_plus
import os

SITEMAP_INDEX_URL = "https://alarbda.com/sitemap_index.xml"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

OUTPUT_FILE = "output.xlsx"
CHECKPOINT_INTERVAL = 300          # حفظ كل 300 فيديو جديد

FIXED_QUALITIES = ["144", "240", "360", "480", "720", "1080", "1440", "2160"]

# =========================
# جلب sitemaps ورابط المقالات (نفس السابق)
# =========================
def get_sitemap_links(index_url):
    try:
        res = requests.get(index_url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, "xml")
        links = [loc.text.strip() for loc in soup.find_all("loc") if "post-sitemap" in loc.text]
        print(f"✅ Sitemaps found: {len(links)}")
        return links
    except Exception as e:
        print("❌ Sitemap index error:", e)
        return []

def get_urls_from_sitemap(sitemap_url):
    try:
        res = requests.get(sitemap_url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, "xml")
        return [loc.text.strip() for loc in soup.find_all("loc")]
    except Exception as e:
        print("❌ Sitemap error:", sitemap_url, e)
        return []

def get_meta(article, name):
    tag = article.find("meta", itemprop=name)
    return tag.get("content", "").strip() if tag else ""

# =========================
# استخراج البيانات (نفس السابق مع دعم other)
# =========================
def extract_data(page_url):
    # ... (الكود كامل نفس النسخة السابقة بدون أي تغيير)
    # (انسخ الدالة extract_data كاملة من الرد السابق هنا)
    try:
        # ... (كل الكود اللي كان في extract_data)
        # (أتركها كما هي للاختصار - فقط أعد نسخها من الرد السابق)
        pass  # استبدلها بالدالة الكاملة
    except Exception as e:
        print("❌ Page error:", page_url, e)
        return None

# =========================
# 🔹 MAIN مع نظام الإنقاذ (الجديد)
# =========================
def main():
    print("🚀 START - scraper resumable مع checkpoint كل 300 فيديو")

    # 1. جلب كل الروابط
    sitemap_links = get_sitemap_links(SITEMAP_INDEX_URL)
    all_urls = []
    for sitemap in sitemap_links:
        print("📦", sitemap)
        urls = get_urls_from_sitemap(sitemap)
        all_urls.extend(urls)

    print(f"📄 Total pages in sitemaps: {len(all_urls)}")

    # 2. تحميل البيانات السابقة (إن وجدت)
    if os.path.exists(OUTPUT_FILE):
        existing_df = pd.read_excel(OUTPUT_FILE)
        processed_slugs = set(existing_df["slug"].astype(str).tolist())
        print(f"✅ Resuming from previous run → {len(processed_slugs)} videos already done")
    else:
        existing_df = pd.DataFrame()
        processed_slugs = set()
        print("🆕 First run - no previous data")

    # 3. استخراج البيانات الجديدة فقط
    new_data = []
    for i, url in enumerate(all_urls):
        # slug من الـ URL (سريع جداً)
        potential_slug = url.rstrip("/").split("/")[-1]
        if potential_slug in processed_slugs:
            continue

        print(f"[{i+1}/{len(all_urls)}] Scraping: {url}")
        result = extract_data(url)

        if result and result["slug"] not in processed_slugs:
            new_data.append(result)
            processed_slugs.add(result["slug"])

        # checkpoint كل 300 فيديو جديد
        if len(new_data) % CHECKPOINT_INTERVAL == 0 and new_data:
            current_df = pd.concat([existing_df, pd.DataFrame(new_data)], ignore_index=True)
            current_df.to_excel(OUTPUT_FILE, index=False)
            print(f"💾 CHECKPOINT SAVED → {len(current_df)} videos total")

        time.sleep(0.3)

    # 4. حفظ النهائي
    if new_data:
        final_df = pd.concat([existing_df, pd.DataFrame(new_data)], ignore_index=True)
        final_df.to_excel(OUTPUT_FILE, index=False)
        print(f"✅ FINAL DONE → {len(final_df)} videos saved in {OUTPUT_FILE}")
    else:
        print("✅ No new videos to add - everything is already scraped!")

if __name__ == "__main__":
    main()
