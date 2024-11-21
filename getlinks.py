from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import json
import os

class MedicineLinksScraper:
    def __init__(self):
      #disabled few things in order to run faster (using less UI)
        self.chrome_options = Options()
        self.chrome_options.add_argument("start-maximized")
        self.chrome_options.add_argument("disable-infobars")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2
        })

        self.browser = webdriver.Chrome(options=self.chrome_options)
        self.wait = WebDriverWait(self.browser, 10)
        self.progress_file = "scraping_progress.json"

    def load_progress(self):
        #Load previous progress if exists
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {"current_alphabet": 0, "collected_links": []}

    def save_progress(self, current_alphabet_index, links):
        #Save current progress
        progress = {
            "current_alphabet": current_alphabet_index,
            "collected_links": links
        }
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f)

    def handle_location_popup(self):
        #Handle location popup if it appears
        try:
            popup_cancel = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[data-auto-updatecity-cancel='true']")
            ))
            popup_cancel.click()
        except TimeoutException:
            print("No location popup found or already handled")

    def handle_notification_bar(self):
        #Handle notification bar if it appears
        try:
            iframe = self.wait.until(EC.presence_of_element_located(
                (By.ID, "notify-visitors-notification-bar-iframe_13453")
            ))
            self.browser.execute_script("""
                var element = document.getElementById('notify-visitors-notification-bar-iframe_13453');
                if(element) element.remove();
            """)
        except Exception as e:
            print(f"Error handling notification bar: {e}")

    def get_links(self):
        # Load previous progress
        progress = self.load_progress()
        links = progress["collected_links"]
        start_alphabet_index = progress["current_alphabet"]

        # Navigate to the main page
        self.browser.get("https://www.1mg.com/drugs-all-medicines")
        time.sleep(5)

        # Handle location popup and notification bar
        self.handle_location_popup()
        self.handle_notification_bar()

        # Get alphabet links
        alphabets = self.wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "div.style__chips___2T95q a")
        ))[1:] #By default the A starts

        print(f"Starting from alphabet index: {start_alphabet_index}")

        if start_alphabet_index == 0:
            self.scrape_current_alphabet_page(links)

        # Process each alphabet starting from where we left off
        for idx, alphabet in enumerate(alphabets[start_alphabet_index:], start=start_alphabet_index):
            try:
                # Click on the alphabet link to load its page
                alphabet.click()
                time.sleep(2)

                # Scrape pages for the current alphabet
                self.scrape_current_alphabet_page(links)

            except StaleElementReferenceException:
                # Refresh alphabet list if elements go stale
                alphabets = self.wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.style__chips___2T95q a")
                ))[1:]
                alphabet = alphabets[idx]
                alphabet.click()
                time.sleep(2)
                self.scrape_current_alphabet_page(links)

            except Exception as e:
                print(f"Error processing alphabet: {e}")
                continue

        self.browser.quit()
        return links

    def scrape_current_alphabet_page(self, links):
        #Scrape all pages for the current alphabet
        while True:
            # Get products on the current page
            products = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "a.style__product-name___HASYw")
            ))

            # Extract links
            for product in products:
                try:
                    link = product.get_attribute("href")
                    if link and link not in links:
                        links.append(link)
                        with open("links.txt", "a+") as f:
                            f.write(link + "\n")
                except Exception as e:
                    print(f"Error extracting link: {e}")
                    continue

            print(f"Total links collected: {len(links)}")

            # Try to go to the next page
            try:
                current_url = self.browser.current_url
                next_buttons = self.wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "a.button-text.link-next")
                ))

                # Find the Next button
                next_button = next_buttons[-1]

                if "page" not in next_button.get_attribute("href"):
                    print("No more pages for current alphabet")
                    break

                next_button.click()
                time.sleep(2)

                # Check if the page actually changed
                if current_url == self.browser.current_url:
                    print("Page didn't change, moving to next alphabet")
                    break

            except Exception as e:
                print(f"Error in pagination: {e}")
                break


if __name__ == "__main__":
    scraper = MedicineLinksScraper()
    try:
        links = scraper.get_links()
        print(f"Scraping completed. Total links collected: {len(links)}")
    except Exception as e:
        print(f"Scraping interrupted: {e}")
    finally:
        scraper.browser.quit()
