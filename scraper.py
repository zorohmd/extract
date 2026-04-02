import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

SITEMAP_URL = "https://alarbda.com/sitemap_index.xml"

headers = {
    "User-Agent": "Mozilla/5.0"
}


def get_urls_from_sitemap(url):
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "xml")
    return [loc.text for loc in soup.find_all("loc")]


def extract_data(page_url):
    try:
        res = requests.get(page_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")

        # العنوان
        title = soup.title.text.strip() if soup.title else ""

        # الوصف
        desc = ""
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            desc = desc_tag.get("content", "")

        # الفيديو
        video_url = ""
        video = soup.find("video")
        if video and video.get("src"):
            video_url = video.get("src")
        else:
            iframe = soup.find("iframe")
            if iframe:
                video_url = iframe.get("src", "")

        # thumbnail
        thumbnail = ""
        og_img = soup.find("meta", property="og:image")
        if og_img:
            thumbnail = og_img.get("content", "")

        # preview (نفس الفيديو غالباً)
        preview = video_url

        # duration
        duration = ""
        if video and video.get("duration"):
            duration = video.get("duration")

        # التاريخ
        date = ""
        time = ""
        date_tag = soup.find("time")
        if date_tag:
            try:
                dt = datetime.fromisoformat(date_tag.get("datetime"))
                date = dt.strftime("%d-%b-%Y")
                time = dt.strftime("%H:%M")
            except:
                pass

        # الكاتيجوري
        categories = []
        cats = soup.select('a[rel="category tag"]')
        for c in cats:
            categories.append(c.text.strip())

        return {
            "slug": page_url.split("/")[-2] if "/" in page_url else page_url,
            "title": title,
            "description": desc,
            "embed": video_url,
            "preview": preview,
            "thumbnail": thumbnail,
            "duration": duration,
            "date": date,
            "time": time,
            "categories": ",".join(categories)
        }

    except Exception as e:
        print(f"Error: {page_url} -> {e}")
        return None


def main():
    urls = get_urls_from_sitemap(SITEMAP_URL)

    data = []
    for url in urls:
        print("Scraping:", url)
        result = extract_data(url)
        if result:
            data.append(result)

    df = pd.DataFrame(data)
    df.to_excel("output.xlsx", index=False)
    print("Done!")


if __name__ == "__main__":
    main()
