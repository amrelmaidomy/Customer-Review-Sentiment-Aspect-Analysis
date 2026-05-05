from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import requests
import os
import time
import random

OUTPUT_CSV = "snopes_dataset.csv"
IMAGES_FOLDER = "news_images"
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# URLs مباشرة لكل label
LABEL_URLS = {
    "Real": [
        "https://www.snopes.com/fact-check/?category=&type=&rating=true",
        "https://www.snopes.com/fact-check/?category=&type=&rating=mostly-true",
        "https://www.snopes.com/fact-check/?category=&type=&rating=mixture",
    ],
    "Fake": [
        "https://www.snopes.com/fact-check/?category=&type=&rating=false",
        "https://www.snopes.com/fact-check/?category=&type=&rating=mostly-false",
        "https://www.snopes.com/fact-check/?category=&type=&rating=legend",
    ]
}

MAX_PAGES = 30

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

def get_links_from_page(driver, url):
    driver.get(url)
    time.sleep(random.uniform(4, 6))

    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # جيب كل الـ links
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if ("/fact-check/" in href
                and len(href) > 30
                and not href.endswith("/fact-check/")
                and "page" not in href
                and href not in seen):
            seen.add(href)
            links.append(href)

    print(f"      🔗 لقيت {len(links)} link")
    return links

def scrape_article(driver, url, label, idx):
    try:
        driver.get(url)
        time.sleep(random.uniform(2, 4))

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # العنوان
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else driver.title.replace("| Snopes.com", "").strip()
        if not title or len(title) < 10:
            return None

        # الـ Label الأصلي
        label_el = soup.find("div", class_="rating_title_wrap")
        label_raw = label_el.get_text(strip=True).replace("About this rating", "").strip() if label_el else label

        # الصورة
        image_path = ""
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if "mediaproxy.snopes" in src or "media.snopes" in src:
                filename = f"snopes_{idx}.jpg"
                image_path = download_image(src, filename)
                if image_path:
                    break

        return {
            "text": title,
            "label": label,
            "label_raw": label_raw,
            "image_path": image_path,
            "source": "Snopes",
            "url": url
        }
    except:
        return None

# ========== Main ==========
print("🚀 بدء الـ Scraping من Snopes...")
driver = get_driver()
all_data = []
all_links = {"Real": [], "Fake": []}

try:
    # الخطوة 1 — جيب الـ links لكل label
    print("\n📋 جاري جمع الـ links...")
    for label, urls in LABEL_URLS.items():
        print(f"\n🏷️ {label}:")
        for base_url in urls:
            rating = base_url.split("rating=")[1]
            print(f"   📌 {rating}")
            for page in range(1, MAX_PAGES + 1):
                if page == 1:
                    page_url = base_url
                else:
                    page_url = f"{base_url}&page={page}"

                links = get_links_from_page(driver, page_url)
                new_links = [l for l in links if l not in all_links[label]]
                all_links[label].extend(new_links)

                if not new_links:
                    break

                time.sleep(random.uniform(2, 3))

        print(f"   ✅ إجمالي {label}: {len(all_links[label])} link")

    # الخطوة 2 — جيب داتا كل خبر
    print("\n📰 جاري Scraping الأخبار...")
    for label, links in all_links.items():
        print(f"\n🏷️ {label} — {len(links)} خبر:")
        for i, url in enumerate(links):
            article = scrape_article(driver, url, label, len(all_data))
            if article:
                all_data.append(article)
                print(f"   ✅ [{i+1}/{len(links)}] {article['text'][:55]}...")
            else:
                print(f"   ❌ [{i+1}/{len(links)}] skip")

            # احفظ كل 50 خبر
            if len(all_data) % 50 == 0 and all_data:
                pd.DataFrame(all_data).to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
                print(f"   💾 تم حفظ {len(all_data)} خبر مؤقتاً")

finally:
    driver.quit()

df = pd.DataFrame(all_data)
if len(df) > 0:
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\n{'='*50}")
    print(f"✅ خلص! اتحفظ {len(df)} خبر")
    print(f"\n📊 توزيع الـ Labels:")
    print(df['label'].value_counts())
    print(f"\n🖼️ فيها صور: {df['image_path'].astype(bool).sum()}")
else:
    print("\n⚠️ مفيش داتا اتجمعت")