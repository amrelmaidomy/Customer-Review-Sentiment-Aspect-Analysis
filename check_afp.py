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

url = "https://factcheck.afp.com/"
driver.get(url)
print("⏳ بستنى الصفحة تتحمل...")
time.sleep(8)

# scroll
for _ in range(3):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

print(f"📄 Title: {driver.title}")

from bs4 import BeautifulSoup
soup = BeautifulSoup(driver.page_source, "html.parser")

# شوف الـ articles
print("\n🔍 بدور على الأخبار...")
articles = soup.find_all("article")
print(f"✅ لقيت {len(articles)} article")

for article in articles[:3]:
    print(f"\n--- Article ---")
    print(f"Classes: {article.get('class', [])}")
    print(f"Text: {article.get_text(strip=True)[:200]}")

# شوف الـ labels
print("\n🏷️ بدور على الـ labels...")
for tag in soup.find_all(True):
    text = tag.get_text(strip=True).lower()
    classes = " ".join(tag.get("class", []))
    if any(w in text for w in ["false", "true", "misleading", "rating", "verdict"]):
        if len(text) < 30 and classes:
            print(f"✅ {tag.name}.{classes}: '{text}'")

# شوف الصور
print("\n🖼️ أول 10 صور:")
for img in soup.find_all("img")[:10]:
    print(f"   alt='{img.get('alt','')[:40]}' src='{img.get('src','')[:80]}'")

with open("afp_page.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print("\n✅ اتحفظ في afp_page.html")

input("\nاضغط Enter للإغلاق...")
driver.quit()