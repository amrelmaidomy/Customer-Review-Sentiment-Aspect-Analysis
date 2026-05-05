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

def normalize_label(text):
    text = text.lower().strip()
    if any(w in text for w in ["false", "fake", "misleading", "manipulated",
                                "incorrect", "no proof", "misattributed"]):
        return "Fake"
    elif any(w in text for w in ["true", "correct", "accurate", "verified"]):
        return "Real"
    return "Fake"  # AFP غالباً كله Fake News

def get_article_links(driver, page):
    if page == 1:
        url = "https://factcheck.afp.com/"
    else:
        url = f"https://factcheck.afp.com/?page={page}"

    driver.get(url)
    time.sleep(random.uniform(4, 6))

    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        # AFP links شكلها /yyyy/mm/...
        if (href.startswith("https://factcheck.afp.com/") 
                and len(href) > 35
                and href not in seen
                and "page=" not in href
                and href != "https://factcheck.afp.com/"):
            seen.add(href)
            links.append(href)

    return links

def scrape_article(driver, url, idx):
    try:
        driver.get(url)
        time.sleep(random.uniform(2, 4))

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # العنوان
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title or len(title) < 10:
            return None

        # الـ Label — AFP غالباً بيكون في badge أو tag
        label_raw = "False"  # AFP كله fact-checks = Fake بشكل أساسي
        label = "Fake"

        for tag in soup.find_all(True):
            classes = " ".join(tag.get("class", []))
            text = tag.get_text(strip=True).lower()
            if any(w in classes.lower() for w in ["rating", "verdict", "label", "badge", "tag"]):
                if text and len(text) < 40:
                    label_raw = text
                    label = normalize_label(text)
                    break

        # الصورة الرئيسية
        image_path = ""
        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "")
            if src and ("afp" in src.lower() or "factcheck" in src.lower()):
                if any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    filename = f"afp_{idx}.jpg"
                    image_path = download_image(src, filename)
                    if image_path:
                        break

        # لو مش لاقي جرب أول صورة كبيرة
        if not image_path:
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if src and any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png"]):
                    if "logo" not in src.lower() and "icon" not in src.lower():
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
print("🚀 بدء الـ Scraping من AFP Fact Check...")
driver = get_driver()
all_links = []
all_data = []

try:
    # الخطوة 1 — جيب كل الـ links
    print("\n📋 جاري جمع الـ links...")
    page = 1
    while True:
        print(f"   📄 صفحة {page}", end=" → ")
        links = get_article_links(driver, page)
        new_links = [l for l in links if l not in all_links]
        all_links.extend(new_links)
        print(f"لقيت {len(new_links)} link جديد — الإجمالي: {len(all_links)}")

        if not new_links:
            print("   ⚠️ آخر صفحة!")
            break

        page += 1
        time.sleep(random.uniform(2, 3))

    print(f"\n✅ إجمالي الـ links: {len(all_links)}")

    # الخطوة 2 — اعمل Scraping لكل خبر
    print("\n📰 جاري Scraping الأخبار...")
    for i, url in enumerate(all_links):
        print(f"   [{i+1}/{len(all_links)}]", end=" ")
        article = scrape_article(driver, url, i)

        if article:
            all_data.append(article)
            print(f"✅ [{article['label']}] {article['text'][:55]}...")
        else:
            print("❌ skip")

        # احفظ كل 50 خبر
        if len(all_data) % 50 == 0 and all_data:
            pd.DataFrame(all_data).to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
            print(f"\n   💾 تم حفظ {len(all_data)} خبر مؤقتاً\n")

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