import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def get_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,800")
    return webdriver.Chrome(options=opts)

def scrape_titles(url: str):
    driver = get_driver()
    try:
        driver.get(url)
        time.sleep(2)  # be polite, rate limit
        return [h.text for h in driver.find_elements(By.TAG_NAME, "h2")]
    finally:
        driver.quit()

if __name__ == "__main__":
    print(scrape_titles("https://example.com"))