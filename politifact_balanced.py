from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import requests
import os
import time
import random

OUTPUT_CSV = "fakenews_balanced.csv"
IMAGES_FOLDER = "news_images"
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# URLs لكل label
RULING_URLS = {
    "Real": [
        "https://www.politifact.com/factchecks/list/?ruling=true",
        "https://www.politifact.com/factchecks/list/?ruling=mostly-true",
        "https://www.politifact.com/factchecks/list/?ruling=half-true",
    ],
    "Fake": [
        "https://www.politifact.com/factchecks/list/?ruling=false",
        "https://www.politifact.com/factchecks/list/?ruling=pants-fire",
        "https://www.politifact.com/factchecks/list/?ruling=mostly-false",
    ]
}

PAGES_PER_RULING = 7  # 7 صفحات × 3 rulings = ~600 لكل label

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--lang=en")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver

def download_image(url, filename):
    try:
        if url.startswith("//"):
            url = "https:" + url
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            path = os.path.join(IMAGES_FOLDER, filename)
            with open(path, 'wb') as f:
                f.write(r.content)
            return path
    except:
        pass
    return ""

def scrape_page(soup, label, page_num, item_offset):
    items = []
    articles = soup.find_all("li", class_="o-listicle__item")

    for article in articles:
        try:
            # النص
            statement = article.find("div", class_="m-statement__quote")
            if not statement:
                continue
            text = statement.get_text(strip=True)
            if not text or len(text) < 10:
                continue

            # الصورة
            image_path = ""
            for img in article.find_all("img"):
                src = img.get("src", "")
                if "mugs" in src or "static.politifact" in src:
                    if src.startswith("//"):
                        src = "https:" + src
                    filename = f"{label}_{page_num}_{item_offset + len(items)}.jpg"
                    image_path = download_image(src, filename)
                    if image_path:
                        break

            # الـ label الأصلي
            label_raw = ""
            for img in article.find_all("img"):
                alt = img.get("alt", "").lower()
                if any(w in alt for w in ["true", "false", "pants", "mostly", "half", "barely"]):
                    label_raw = alt
                    break

            # المصدر
            speaker = ""
            speaker_el = article.find("a", class_="m-statement__name")
            if speaker_el:
                speaker = speaker_el.get_text(strip=True)

            items.append({
                "text": text,
                "label": label,
                "label_raw": label_raw,
                "speaker": speaker,
                "image_path": image_path,
            })

            print(f"   ✅ [{label}] {text[:60]}...")

        except:
            continue

    return items

# ========== Main ==========
print("🚀 بدء الـ Scraping المتوازن من PolitiFact...")
driver = get_driver()
all_data = []

try:
    for label, urls in RULING_URLS.items():
        print(f"\n{'='*50}")
        print(f"🏷️ جاري جمع: {label}")

        for base_url in urls:
            ruling = base_url.split("ruling=")[1]
            print(f"\n   📌 Ruling: {ruling}")

            for page in range(1, PAGES_PER_RULING + 1):
                url = f"{base_url}&page={page}"
                print(f"\n   📄 صفحة {page}/{PAGES_PER_RULING}")

                driver.get(url)
                time.sleep(random.uniform(3, 5))

                soup = BeautifulSoup(driver.page_source, "html.parser")
                items = scrape_page(soup, label, page, len(all_data))
                all_data.extend(items)

                print(f"   📊 اتجمع {len(items)} — الإجمالي: {len(all_data)}")

                if not items:
                    print("   ⚠️ مفيش داتا — ممكن آخر صفحة")
                    break

                time.sleep(random.uniform(2, 3))

finally:
    driver.quit()

# حفظ الداتا
df = pd.DataFrame(all_data)

if len(df) > 0:
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')

    print(f"\n{'='*50}")
    print(f"✅ خلص! اتحفظ {len(df)} خبر في {OUTPUT_CSV}")
    print(f"\n📊 توزيع الـ Labels:")
    print(df['label'].value_counts())
    print(f"\n🏷️ التفاصيل:")
    print(df['label_raw'].value_counts())
    print(f"\n🖼️ أخبار فيها صور: {df['image_path'].astype(bool).sum()}")
else:
    print("\n⚠️ مفيش داتا اتجمعت")