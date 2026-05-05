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

# ========== الإعدادات ==========
OUTPUT_CSV = "fakenews_dataset.csv"
IMAGES_FOLDER = "news_images"
MAX_PAGES = 20  # كل صفحة فيها ~30 خبر = 600 خبر
os.makedirs(IMAGES_FOLDER, exist_ok=True)
# ================================

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

def normalize_label(label):
    label = label.lower().strip()
    if label in ["true", "mostly true", "half true"]:
        return "Real"
    elif label in ["false", "mostly false", "pants on fire", "pants-on-fire", "barely true", "barely-true"]:
        return "Fake"
    return None

def download_image(url, filename):
    try:
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

def scrape_page(soup, page_num):
    items = []

    # كل خبر في الصفحة
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

            # الـ Label
            meter = article.find("img", class_="c-image__original")
            if not meter:
                meter = article.find("img", alt=True)

            label_raw = ""
            for img in article.find_all("img"):
                alt = img.get("alt", "").lower()
                if any(w in alt for w in ["true", "false", "pants", "mostly", "half", "barely"]):
                    label_raw = alt
                    break

            label = normalize_label(label_raw)
            if not label:
                continue

            # الصورة
            image_path = ""
            for img in article.find_all("img"):
                src = img.get("src", "")
                if "mugs" in src or "static.politifact" in src:
                    if src.startswith("//"):
                        src = "https:" + src
                    filename = f"news_{page_num}_{len(items)}.jpg"
                    image_path = download_image(src, filename)
                    if image_path:
                        break

            # الشخص / المصدر
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

        except Exception as e:
            continue

    return items

# ========== Main ==========
print("🚀 بدء الـ Scraping من PolitiFact...")
driver = get_driver()
all_data = []

try:
    for page in range(1, MAX_PAGES + 1):
        if page == 1:
            url = "https://www.politifact.com/factchecks/list/"
        else:
            url = f"https://www.politifact.com/factchecks/list/?page={page}"

        print(f"\n📄 صفحة {page}/{MAX_PAGES} — {url}")
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        soup = BeautifulSoup(driver.page_source, "html.parser")
        items = scrape_page(soup, page)
        all_data.extend(items)

        print(f"   📊 اتجمع {len(items)} خبر — الإجمالي: {len(all_data)}")
        time.sleep(random.uniform(2, 4))

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