from selenium import webdriver
from selenium.webdriver.common.by import By
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

url = "https://www.politifact.com/factchecks/list/"
driver.get(url)
print("⏳ بستنى الصفحة تتحمل...")
time.sleep(6)

print(f"📄 Title: {driver.title}")

soup = BeautifulSoup(driver.page_source, "html.parser")

# شوف الـ articles
print("\n🔍 بدور على الأخبار...")
divs = soup.find_all("div")
for div in divs:
    text = div.get_text(strip=True)
    classes = div.get("class", [])
    if len(text) > 30 and len(text) < 400 and classes:
        if any(w in text.lower() for w in ["true", "false", "pants", "mostly", "half"]):
            print(f"\n✅ Class: {classes}")
            print(f"   Text: {text[:200]}")
            print("---")

# شوف الصور
print("\n🖼️ أول 15 صورة:")
imgs = soup.find_all("img")
for img in imgs[:15]:
    print(f"   alt='{img.get('alt','')}' src='{img.get('src','')[:80]}'")

with open("politifact_page.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print("\n✅ اتحفظ في politifact_page.html")

input("\nاضغط Enter للإغلاق...")
driver.quit()