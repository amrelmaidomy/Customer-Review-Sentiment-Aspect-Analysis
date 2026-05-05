from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

url = "https://www.snopes.com/fact-check/"
driver.get(url)
print("⏳ بستنى الصفحة تتحمل...")
time.sleep(10)

# scroll للأسفل عشان يحمل المحتوى
print("📜 بعمل scroll...")
for i in range(5):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

print(f"📄 Title: {driver.title}")

soup = BeautifulSoup(driver.page_source, "html.parser")

# جرب selectors مختلفة
print("\n🔍 بدور على المحتوى...")

selectors = [
    ("article", {}),
    ("div", {"class": "card"}),
    ("div", {"class": "article"}),
    ("li", {"class": "article"}),
    ("a", {"href": lambda x: x and "/fact-check/" in x and len(x) > 20}),
]

for tag, attrs in selectors:
    try:
        if callable(list(attrs.values())[0]) if attrs else False:
            els = soup.find_all(tag, href=attrs.get("href"))
        else:
            els = soup.find_all(tag, attrs)
        if els:
            print(f"✅ <{tag} {attrs}> → لقيت {len(els)}")
            print(f"   مثال: {els[0].get_text(strip=True)[:100]}")
    except:
        pass

# جيب كل الـ links الخاصة بالأخبار
print("\n🔗 الـ links الموجودة:")
links = soup.find_all("a", href=True)
news_links = [a for a in links if "/fact-check/" in a.get("href", "") and len(a.get("href", "")) > 25]
print(f"✅ لقيت {len(news_links)} link للأخبار")
for link in news_links[:5]:
    print(f"   - {link.get('href', '')[:80]}")
    print(f"     Text: {link.get_text(strip=True)[:60]}")

with open("snopes_page2.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print("\n✅ اتحفظ في snopes_page2.html")

input("\nاضغط Enter للإغلاق...")
driver.quit()