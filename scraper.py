import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import base64
from urllib.parse import urlparse, parse_qs, unquote_plus

SITEMAP_INDEX_URL = "https://alarbda.com/sitemap_index.xml"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# =========================
# 🔹 الدقات الثابتة (من الأصغر إلى الأكبر)
# =========================
FIXED_QUALITIES = ["144", "240", "360", "480", "720", "1080", "1440", "2160"]

# =========================
# 🔹 جلب sitemap الفرعية (post فقط)
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
# 🔹 استخراج البيانات مع عمود other
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
        # Schema extraction
        # ======================
        title = get_meta(article, "name")
        description = get_meta(article, "description")
        thumbnail = get_meta(article, "thumbnailUrl")
        duration = get_meta(article, "duration")
        upload_date = get_meta(article, "uploadDate")

        date = ""
        time_str = ""
        if upload_date:
            try:
                dt = datetime.fromisoformat(upload_date.replace("+02:00", "").replace("Z", ""))
                date = dt.strftime("%d-%b-%Y")
                time_str = dt.strftime("%H:%M")
            except:
                pass

        categories = [c.text.strip() for c in article.select(".tags a")]
        categories_text = ",".join(categories)

        # ======================
        # استخراج الفيديو + الدقات
        # ======================
        video_url = ""
        iframe_src = ""
        quality_sources = {}   # mp4_XXX + other

        # 1. iframe clean-tube-player
        for iframe in article.find_all("iframe"):
            src = iframe.get("src", "")
            if src and "player-x.php" in src and "q=" in src:
                iframe_src = src
                parsed = urlparse(src)
                q_encoded = parse_qs(parsed.query).get("q", [None])[0]
                if q_encoded:
                    try:
                        decoded_str = base64.b64decode(q_encoded).decode("utf-8")
                        inner_params = parse_qs(decoded_str)
                        tag_encoded = inner_params.get("tag", [None])[0]
                        if tag_encoded:
                            video_tag_html = unquote_plus(tag_encoded)
                            tag_soup = BeautifulSoup(video_tag_html, "html.parser")
                            for source in tag_soup.find_all("source"):
                                s = source.get("src", "").strip()
                                label = source.get("label") or source.get("title") or ""
                                if s and s.startswith("http"):
                                    if label.isdigit() and label in FIXED_QUALITIES:
                                        col_name = f"mp4_{label}"
                                    else:
                                        col_name = "other"          # بدون دقة أو دقة غير معروفة
                                    quality_sources[col_name] = s
                    except Exception as decode_err:
                        print(f"❌ Decode q error: {decode_err}")
                break

        # 2. <video> مباشرة في الصفحة
        for video_tag in article.find_all("video"):
            for source in video_tag.find_all("source"):
                s = source.get("src", "").strip()
                label = source.get("label") or source.get("title") or ""
                if s and s.startswith("http"):
                    if label.isdigit() and label in FIXED_QUALITIES:
                        col_name = f"mp4_{label}"
                    else:
                        col_name = "other"
                    quality_sources[col_name] = s

        # 3. video_url = أعلى دقة أو other
        if quality_sources:
            qual_dict = {}
            for col, url in quality_sources.items():
                if col.startswith("mp4_"):
                    try:
                        num = int(col.replace("mp4_", ""))
                        qual_dict[num] = url
                    except:
                        pass
            if qual_dict:
                max_qual = max(qual_dict.keys())
                video_url = qual_dict[max_qual]
            else:
                video_url = list(quality_sources.values())[0]

        # 4. fallback schema (أي رابط مباشر)
        schema_embed = get_meta(article, "contentURL")
        if not video_url and schema_embed and schema_embed.startswith("http"):
            quality_sources["other"] = schema_embed
            video_url = schema_embed

        # ======================
        # النتيجة النهائية
        # ======================
        result = {
            "slug": slug,
            "title": title,
            "description": description,
            "video_url": video_url,
            "iframe_src": iframe_src,
        }

        # الدقات الثابتة
        for q in FIXED_QUALITIES:
            col = f"mp4_{q}"
            result[col] = quality_sources.get(col, "")

        # العمود الجديد لكل الحالات الأخرى
        result["other"] = quality_sources.get("other", "")

        # باقي الحقول
        result.update({
            "thumbnail": thumbnail,
            "duration": duration,
            "date": date,
            "time": time_str,
            "categories": categories_text
        })

        return result

    except Exception as e:
        print("❌ Page error:", page_url, e)
        return None

# =========================
# 🔹 main
# =========================
def main():
    print("🚀 START - استخراج فيديوهات alarbda.com مع عمود other")
    sitemap_links = get_sitemap_links(SITEMAP_INDEX_URL)
    all_urls = []
    for sitemap in sitemap_links:
        print("📦", sitemap)
        urls = get_urls_from_sitemap(sitemap)
        all_urls.extend(urls)

    print(f"📄 Total pages: {len(all_urls)}")
    data = []
    for i, url in enumerate(all_urls):
        print(f"[{i+1}/{len(all_urls)}] Scraping:", url)
        result = extract_data(url)
        if result:
            data.append(result)
        time.sleep(0.3)

    df = pd.DataFrame(data)
    df.to_excel("output.xlsx", index=False)
    print("✅ DONE -> output.xlsx")
    print(f"📊 Total videos: {len(data)}")
    print("   • mp4_144 | mp4_240 | ... | mp4_2160  → الدقات المعروفة")
    print("   • other       → أي فيديو بدون دقة أو دقة غير معروفة أو صيغة غير mp4")
    print("   • iframe_src  → رابط المشغل (player-x.php)")
    print(f"   • Total columns: {len(df.columns)}")

if __name__ == "__main__":
    main()
