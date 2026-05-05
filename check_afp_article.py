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

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

# خبر من AFP
url = "https://factcheck.afp.com/"
driver.get(url)
time.sleep(8)

for _ in range(3):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

soup = BeautifulSoup(driver.page_source, "html.parser")

# اطبع كل الصور
print("🖼️ كل الصور:")
for img in soup.find_all("img"):
    src = img.get("src", "")
    alt = img.get("alt", "")
    if src:
        print(f"   alt='{alt[:40]}' src='{src[:100]}'")

# اطبع كل الـ links
print("\n🔗 أول 20 link:")
seen = set()
count = 0
for a in soup.find_all("a", href=True):
    href = a.get("href", "")
    text = a.get_text(strip=True)
    if href.startswith("https://factcheck.afp.com/") and href not in seen and len(href) > 35:
        seen.add(href)
        print(f"   {href}")
        print(f"   Text: {text[:60]}")
        count += 1
        if count >= 20:
            break

with open("afp_check.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print("\n✅ اتحفظ في afp_check.html")

input("\nاضغط Enter للإغلاق...")
driver.quit()