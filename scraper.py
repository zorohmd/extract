import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

SITEMAP_INDEX_URL = "https://alarbda.com/sitemap_index.xml"

headers = {
    "User-Agent": "Mozilla/5.0"
}


def get_sitemap_links(index_url):
    try:
        res = requests.get(index_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "xml")

        links = []
        for loc in soup.find_all("loc"):
            url = loc.text

            if "post-sitemap" in url:
                links.append(url)

        print(f"✅ Found {len(links)} post sitemaps")
        return links

    except Exception as e:
        print("❌ Error fetching sitemap index:", e)
        return []


def get_urls_from_sitemap(sitemap_url):
    try:
        res = requests.get(sitemap_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "xml")

        urls = [loc.text for loc in soup.find_all("loc")]
        print(f"   ↳ {len(urls)} URLs")

        return urls

    except Exception as e:
        print("❌ Error in sitemap:", sitemap_url, e)
        return []


def extract_data(page_url):
    try:
        res = requests.get(page_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "lxml")

        title = soup.title.text.strip() if soup.title else ""

        desc = ""
        tag = soup.find("meta", attrs={"name": "description"})
        if tag:
            desc = tag.get("content", "")

        video_url = ""
        video = soup.find("video")
        if video and video.get("src"):
            video_url = video.get("src")
        else:
            iframe = soup.find("iframe")
            if iframe:
                video_url = iframe.get("src", "")

        thumbnail = ""
        og = soup.find("meta", property="og:image")
        if og:
            thumbnail = og.get("content", "")

        date = ""
        time_str = ""
        date_tag = soup.find("time")
        if date_tag and date_tag.get("datetime"):
            try:
                dt = datetime.fromisoformat(date_tag.get("datetime"))
                date = dt.strftime("%d-%b-%Y")
                time_str = dt.strftime("%H:%M")
            except:
                pass

        categories = []
        for c in soup.select('a[rel="category tag"]'):
            categories.append(c.text.strip())

        return {
            "slug": page_url.rstrip("/").split("/")[-1],
            "title": title,
            "description": desc,
            "embed": video_url,
            "thumbnail": thumbnail,
            "date": date,
            "time": time_str,
            "categories": ",".join(categories)
        }

    except Exception as e:
        print("❌ Page error:", page_url, e)
        return None


def main():
    all_data = []

    print("🚀 START")

    sitemaps = get_sitemap_links(SITEMAP_INDEX_URL)

    total_urls = 0

    for sitemap in sitemaps:
        print("📦", sitemap)
        urls = get_urls_from_sitemap(sitemap)

        for url in urls:
            total_urls += 1
            print(f"[{total_urls}] Scraping:", url)

            result = extract_data(url)

            if result:
                all_data.append(result)

            # ⛔ مهم لتجنب الحظر
            time.sleep(0.3)

    print(f"📊 Total collected: {len(all_data)}")

    # ✅ حتى لو فاضي ينشئ الملف
    df = pd.DataFrame(all_data)

    if df.empty:
        print("⚠️ No data found, creating empty file")

    df.to_excel("output.xlsx", index=False)

    print("✅ Excel file created: output.xlsx")


if __name__ == "__main__":
    main()
