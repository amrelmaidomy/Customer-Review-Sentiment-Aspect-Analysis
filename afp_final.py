from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import requests
import os
import time
import random

OUTPUT_CSV = "afp_dataset.csv"
IMAGES_FOLDER = "news_images"
os.makedirs(IMAGES_FOLDER, exist_ok=True)

BASE_URL = "https://factcheck.afp.com"

# Categories الموجودة
CATEGORIES = [
    "/list/US-politics",
    "/list/Artificial-intelligence",
    "/list/Climate",
    "/list/Vaccines",
    "/list/War-Ukraine",
    "/list/regions/Africa",
    "/list/regions/Asia-Pacific",
    "/list/regions/Europe",
    "/list/regions/Latin-America",
    "/list/regions/Middle-East",
    "/list/regions/North-America",
    "/list/topics/135",
    "/list/topics/146",
    "/list/topics/134",
]

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
        if url.startswith("/"):
            url = BASE_URL + url
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

def get_links_from_category(driver, category):
    links = []
    seen = set()
    page = 0

    while True:
        if page == 0:
            url = BASE_URL + category
        else:
            url = BASE_URL + category + f"?page={page}"

        print(f"      📄 صفحة {page+1} — {url}")
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        new_links = []
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            # AFP article links شكلها /doc/... أو /afp-...
            if (href.startswith("/") 
                    and len(href) > 10
                    and "/list/" not in href
                    and "/How" not in href
                    and "/AFP" not in href
                    and "/corrections" not in href
                    and "/afp-fact" not in href
                    and href not in seen):
                full_url = BASE_URL + href
                seen.add(href)
                new_links.append(full_url)

        if not new_links:
            break

        links.extend(new_links)
        print(f"         ✅ {len(new_links)} link — الإجمالي: {len(links)}")
        page += 1
        time.sleep(random.uniform(2, 3))

    return links

def scrape_article(driver, url, idx):
    try:
        driver.get(url)
        time.sleep(random.uniform(2, 3))

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # العنوان
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title or len(title) < 10:
            return None

        # الـ Label — AFP كله Fake News
        label = "Fake"
        label_raw = "false"

        # الصورة — الـ src ناقصه BASE_URL
        image_path = ""
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if "/sites/default/files/" in src:
                if src.startswith("/"):
                    src = BASE_URL + src
                filename = f"afp_{idx}.jpg"
                image_path = download_image(src, filename)
                if image_path:
                    break

        return {
            "text": title,
            "label": label,
            "label_raw": label_raw,
            "image_path": image_path,
            "source": "AFP",
            "url": url
        }

    except:
        return None

# ========== Main ==========
print("🚀 بدء الـ Scraping من AFP...")
driver = get_driver()
all_links = []
all_data = []

try:
    # الخطوة 1 — جيب الـ links من كل category
    print("\n📋 جاري جمع الـ links من كل category...")
    seen_links = set()

    for cat in CATEGORIES:
        print(f"\n   📁 Category: {cat}")
        links = get_links_from_category(driver, cat)
        new_links = [l for l in links if l not in seen_links]
        seen_links.update(new_links)
        all_links.extend(new_links)
        print(f"   ✅ {len(new_links)} link جديد — الإجمالي: {len(all_links)}")
        time.sleep(random.uniform(2, 3))

    print(f"\n✅ إجمالي الـ links: {len(all_links)}")

    # الخطوة 2 — اعمل Scraping لكل خبر
    print("\n📰 جاري Scraping الأخبار...")
    for i, url in enumerate(all_links):
        print(f"   [{i+1}/{len(all_links)}]", end=" ")
        article = scrape_article(driver, url, i)

        if article:
            all_data.append(article)
            print(f"✅ {article['text'][:60]}...")
        else:
            print("❌ skip")

        # احفظ كل 100 خبر
        if len(all_data) % 100 == 0 and all_data:
            pd.DataFrame(all_data).to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
            print(f"\n   💾 تم حفظ {len(all_data)} خبر\n")

        time.sleep(random.uniform(1.5, 2.5))

finally:
    driver.quit()

df = pd.DataFrame(all_data)
if len(df) > 0:
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\n{'='*50}")
    print(f"✅ خلص! اتحفظ {len(df)} خبر في {OUTPUT_CSV}")
    print(f"\n📊 توزيع الـ Labels:")
    print(df['label'].value_counts())
    print(f"\n🖼️ فيها صور: {df['image_path'].astype(bool).sum()}")
else:
    print("\n⚠️ مفيش داتا اتجمعت")