import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

SITEMAP_INDEX_URL = "https://alarbda.com/sitemap_index.xml"

headers = {
    "User-Agent": "Mozilla/5.0"
}


# =========================
# 🔹 جلب sitemap الفرعية (post فقط)
# =========================
def get_sitemap_links(index_url):
    try:
        res = requests.get(index_url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, "xml")

        links = []

        for loc in soup.find_all("loc"):
            url = loc.text.strip()

            if "post-sitemap" in url:
                links.append(url)

        print(f"✅ Sitemaps found: {len(links)}")
        return links

    except Exception as e:
        print("❌ Sitemap index error:", e)
        return []


# =========================
# 🔹 جلب روابط المقالات
# =========================
def get_urls_from_sitemap(sitemap_url):
    try:
        res = requests.get(sitemap_url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, "xml")

        return [loc.text.strip() for loc in soup.find_all("loc")]

    except Exception as e:
        print("❌ Sitemap error:", sitemap_url, e)
        return []


# =========================
# 🔹 meta helper
# =========================
def get_meta(article, name):
    tag = article.find("meta", itemprop=name)
    return tag.get("content", "").strip() if tag else ""


# =========================
# 🔹 استخراج البيانات
# =========================
def extract_data(page_url):
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, "lxml")

        article = soup.find("article")
        if not article:
            return None

        # slug
        slug = article.get("id", "").replace("post-", "")
        if not slug:
            slug = page_url.rstrip("/").split("/")[-1]

        # ======================
        # 🔥 Schema extraction
        # ======================
        title = get_meta(article, "name")
        description = get_meta(article, "description")

        # 🔗 روابط فقط للفيديو
        embed = get_meta(article, "contentURL")
        thumbnail = get_meta(article, "thumbnailUrl")
        preview = embed

        duration = get_meta(article, "duration")
        upload_date = get_meta(article, "uploadDate")

        # ======================
        # date + time
        # ======================
        date = ""
        time_str = ""

        if upload_date:
            try:
                dt = datetime.fromisoformat(upload_date.replace("+02:00", ""))
                date = dt.strftime("%d-%b-%Y")
                time_str = dt.strftime("%H:%M")
            except:
                pass

        # ======================
        # 🔥 categories (TEXT ONLY)
        # ======================
        categories = []
        for c in article.select(".tags a"):
            categories.append(c.text.strip())

        categories_text = ",".join(categories)  # بدون روابط نهائياً

        return {
            "slug": slug,
            "title": title,
            "description": description,

            # روابط فقط
            "embed": embed,
            "preview": preview,
            "thumbnail": thumbnail,

            "duration": duration,
            "date": date,
            "time": time_str,

            # نص فقط
            "categories": categories_text
        }

    except Exception as e:
        print("❌ Page error:", page_url, e)
        return None


# =========================
# 🔹 main
# =========================
def main():
    print("🚀 START")

    sitemap_links = get_sitemap_links(SITEMAP_INDEX_URL)

    all_urls = []

    for sitemap in sitemap_links:
        print("📦", sitemap)
        urls = get_urls_from_sitemap(sitemap)
        all_urls.extend(urls)

    print(f"📄 Total pages: {len(all_urls)}")

    data = []

    for i, url in enumerate(all_urls):
        print(f"[{i+1}] Scraping:", url)

        result = extract_data(url)

        if result:
            data.append(result)

        time.sleep(0.2)

    # ======================
    # 🔥 Excel output
    # ======================
    df = pd.DataFrame(data)

    df.to_excel("output.xlsx", index=False)

    print("✅ DONE -> output.xlsx")
    print("📊 Total:", len(data))


if __name__ == "__main__":
    main()
