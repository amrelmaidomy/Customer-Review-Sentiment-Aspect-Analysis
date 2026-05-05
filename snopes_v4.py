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

def get_all_links(driver, max_pages=200):
    """جيب كل الـ links من صفحات القائمة العادية"""
    all_links = []
    seen = set()

    for page in range(1, max_pages + 1):
        if page == 1:
            url = "https://www.snopes.com/fact-check/"
        else:
            url = f"https://www.snopes.com/fact-check/page/{page}/"

        print(f"   📄 صفحة {page} — {url}")
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        # scroll
        for _ in range(4):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # جيب الـ links
        new_count = 0
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if ("/fact-check/" in href
                    and len(href) > 30
                    and not href.endswith("/fact-check/")
                    and "/page/" not in href
                    and "?" not in href
                    and href not in seen):
                seen.add(href)
                all_links.append(href)
                new_count += 1

        print(f"      ✅ {new_count} link جديد — الإجمالي: {len(all_links)}")

        if new_count == 0:
            print("      ⚠️ آخر صفحة!")
            break

        time.sleep(random.uniform(2, 3))

    return all_links

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

        # الـ Label
        label_el = soup.find("div", class_="rating_title_wrap")
        if not label_el:
            return None
        label_raw = label_el.get_text(strip=True).replace("About this rating", "").strip()

        # normalize
        label_lower = label_raw.lower()
        if any(w in label_lower for w in ["true", "mostly true", "mixture", "correct"]):
            label = "Real"
        elif any(w in label_lower for w in ["false", "mostly false", "fake",
                                             "legend", "misattributed", "outdated"]):
            label = "Fake"
        else:
            return None  # skip unclear labels

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

try:
    # الخطوة 1 — جيب كل الـ links
    print("\n📋 جاري جمع كل الـ links...")
    all_links = get_all_links(driver, max_pages=200)
    print(f"\n✅ إجمالي الـ links: {len(all_links)}")

    # الخطوة 2 — اعمل Scraping لكل خبر
    print("\n📰 جاري Scraping الأخبار...")
    for i, url in enumerate(all_links):
        print(f"   [{i+1}/{len(all_links)}]", end=" ")
        article = scrape_article(driver, url, i)

        if article:
            all_data.append(article)
            print(f"✅ [{article['label']}] {article['text'][:50]}...")
        else:
            print("❌ skip")

        # احفظ كل 100 خبر
        if len(all_data) % 100 == 0 and all_data:
            df_temp = pd.DataFrame(all_data)
            df_temp.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
            print(f"\n   💾 تم حفظ {len(all_data)} خبر\n")

        time.sleep(random.uniform(1.5, 3))

finally:
    driver.quit()

df = pd.DataFrame(all_data)
if len(df) > 0:
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\n{'='*50}")
    print(f"✅ خلص! اتحفظ {len(df)} خبر في {OUTPUT_CSV}")
    print(f"\n📊 توزيع الـ Labels:")
    print(df['label'].value_counts())
    print(f"\n🏷️ التفاصيل:")
    print(df['label_raw'].value_counts())
    print(f"\n🖼️ فيها صور: {df['image_path'].astype(bool).sum()}")
else:
    print("\n⚠️ مفيش داتا اتجمعت")