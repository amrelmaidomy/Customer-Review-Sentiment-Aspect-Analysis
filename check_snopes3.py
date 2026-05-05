from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--lang=en")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
)

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

# ندخل على خبر واحد ونشوف شكله
url = "https://www.snopes.com/fact-check/house-resolution-piker-antisemitism/"
driver.get(url)
print("⏳ بستنى...")
time.sleep(6)

soup = BeautifulSoup(driver.page_source, "html.parser")

# دور على الـ Label
print("\n🏷️ بدور على الـ Label...")
for tag in soup.find_all(True):
    classes = " ".join(tag.get("class", []))
    text = tag.get_text(strip=True)
    if any(w in classes.lower() for w in ["rating", "label", "verdict", "claim", "status"]):
        if text and len(text) < 50:
            print(f"✅ {tag.name}.{classes}: '{text}'")

# دور على الصورة الرئيسية
print("\n🖼️ الصور:")
for img in soup.find_all("img")[:10]:
    src = img.get("src", "")
    alt = img.get("alt", "")
    if "media.snopes" in src or "mediaproxy" in src:
        print(f"   ✅ alt='{alt[:50]}' src='{src[:80]}'")

# العنوان
print(f"\n📰 العنوان: {driver.title}")

with open("snopes_article.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print("✅ اتحفظ في snopes_article.html")

input("\nاضغط Enter للإغلاق...")
driver.quit()