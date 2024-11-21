from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
import random
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='scraping.log'
)

class MedicationScraper:
    def __init__(self):
        self.setup_driver()
        self.drugs_data = {"drugs": []}

#All the driver setting, made it so that it runs faster and no UI
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_argument("--disable-plugins")

        # Disable logging
        chrome_options.add_argument("--log-level=3")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

    def safe_get_text(self, xpath, wait=True):
        try:
            if wait:
                element = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
            else:
                element = self.driver.find_element(By.XPATH, xpath)
            return element.text.strip()
        except (TimeoutException, NoSuchElementException) as e:
            logging.warning(f"Could not find element with xpath: {xpath}")
            return ""

    def safe_get_list(self, xpath):
        try:
            elements = self.wait.until(
                EC.presence_of_all_elements_located((By.XPATH, xpath))
            )
            return [elem.text.strip() for elem in elements if elem.text.strip()]
        except (TimeoutException, NoSuchElementException) as e:
            logging.warning(f"Could not find list elements with xpath: {xpath}")
            return []

#To over come the location pop ups
    def handle_location_popup(self):
        try:
            popup_cancel = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[data-auto-updatecity-cancel='true']")
            ))
            popup_cancel.click()
        except TimeoutException:
            print("No location popup found or already handled")

    def scrape_drug_page(self, url):
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                self.driver.get(url)
                time.sleep(random.uniform(1, 3))  # Random delay

                #self.handle_location_popup() #It only appears when u run the code for first time, if you want activate here for evey links

                drug_data = {
                    "name": self.safe_get_text("//div[@id='drug_header']//h1"),
                    "uses": [
                        {
                            "condition": use.find_element(By.XPATH, ".//a").text.strip(),
                            #"details": ""  # You can add more detailed scraping if needed
                        }
                        for use in self.driver.find_elements(By.XPATH, "//div[@id='uses_and_benefits']//div[contains(@class, 'DrugOverview__content___22ZBX')]//ul/li")
                    ],
                    "benefits": [
                        {
                            "condition": benefit.find_element(By.XPATH, ".//h3").text.strip(),
                            "description": benefit.find_element(By.XPATH, ".//div[not(h3)]").text.strip()
                        }
                        for benefit in self.driver.find_elements(By.XPATH, "//div[@id='uses_and_benefits']//div[contains(@class, 'ShowMoreArray__tile___2mFZk')]")
                    ],
                    "sideEffects": {
                        "generalInfo": self.safe_get_text("//div[@id='side_effects']//div[contains(@class, 'DrugOverview__content___22ZBX')][1]"),
                        "common": self.safe_get_list("//div[@id='side_effects']//h3[contains(text(), 'Common side effects')]/..//ul/li"),
                        #"severe": []  # Add xpath for severe side effects if available
                    },
                    "mechanism": {
                        "description": self.safe_get_text("//div[@id='how_drug_works']//div[contains(@class, 'DrugOverview__content___22ZBX')]")
                    },
                    "administration": {
                        "instructions": self.safe_get_text("//div[@id='how_to_use']//div[contains(@class, 'DrugOverview__content___22ZBX')]"),
                        #"warnings": [] # Add xpath for warnings if available
                    },
                    "metadata": {
                        "lastUpdated": datetime.now().isoformat(),
                        "sourceUrl": url
                    }
                }

                return drug_data

            except Exception as e:
                retry_count += 1
                logging.error(f"Error scraping {url}: {str(e)}")
                time.sleep(random.uniform(5, 10))  # Longer delay between retries

        logging.error(f"Failed to scrape {url} after {max_retries} attempts")
        return None

#getting the links from links.txt
    def scrape_all_drugs(self):
        with open('links.txt', 'r') as file:
            urls = file.readlines()

        for url in urls:
            url = url.strip()
            logging.info(f"Scraping: {url}")

            drug_data = self.scrape_drug_page(url)
            if drug_data:
                self.drugs_data["drugs"].append(drug_data)

            # Save progress after each successful scrape
            self.save_data()

            # Random delay between requests
            time.sleep(random.uniform(2, 5))

    def save_data(self):
        with open('drugs_data.json', 'w', encoding='utf-8') as f:
            json.dump(self.drugs_data, f, ensure_ascii=False, indent=2)

    def close(self):
        self.driver.quit()

def main():
    scraper = MedicationScraper()
    try:
        scraper.scrape_all_drugs()
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
