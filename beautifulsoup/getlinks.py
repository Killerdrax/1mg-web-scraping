import requests
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime

# Base URL format
base_url = "https://www.1mg.com/drugs-all-medicines?page={page}&label={label}"

# Log files
log_file_path = "scrape_log.txt"
error_log_path = "error_log.txt"
output_file_path = "links.txt"

# Function to load last known state from the log file
def load_last_state():
    if os.path.exists(log_file_path):
        with open(log_file_path, "r") as log_file:
            lines = log_file.readlines()
            last_completed_page = 1
            current_letter = 'A'

            for line in lines:
                if line.startswith("[") and "STATE:" in line:
                    # Extract state information
                    state_part = line.split("STATE:")[1].split("-")[0].strip()
                    letter, page = state_part.split(',')
                    # Update only if it's a completed page
                    if "URLs found:" in line:
                        current_letter = letter
                        last_completed_page = int(page)

            # Return the next page to process
            return current_letter, last_completed_page + 1
    return 'A', 1  # Default start

# Logging functions
def log_state(letter, page, urls_found=0):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file_path, "a") as log_file:
        log_file.write(f"[{timestamp}] STATE: {letter},{page} - URLs found: {urls_found}\n")

def log_error(error_type, message, url=None, retry_count=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_entry = f"[{timestamp}] {error_type}: "
    if url:
        error_entry += f"URL: {url} - "
    error_entry += message
    if retry_count is not None:
        error_entry += f" (Retry attempt: {retry_count})"
    error_entry += "\n"

    # Write to both error and main log
    with open(error_log_path, "a") as error_file:
        error_file.write(error_entry)
    with open(log_file_path, "a") as log_file:
        log_file.write(error_entry)

# Load last state to resume if the script stopped
current_letter, current_page = load_last_state()
print(f"Resuming from letter {current_letter}, page {current_page}")

# Open the file to write links (append mode so we don't overwrite previous data)
with open(output_file_path, "a", encoding="utf-8") as file:
    try:
        for char in range(ord(current_letter), ord('Z') + 1):
            label = chr(char)
            # Only use current_page for the resuming letter, start from 1 for new letters
            page = current_page if label == current_letter else 1
            retry_count = 0
            max_retries = 3

            while True:
                try:
                    url = base_url.format(page=page, label=label.lower())
                    print(f"Scraping page: {url}")

                    response = requests.get(url)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, "html.parser")

                    # Find the JSON-LD script tag
                    json_ld_tag = soup.find("script", {"type": "application/ld+json"})
                    if not json_ld_tag:
                        log_error("DATA_ERROR", "No JSON-LD data found", url)
                        break

                    # Load JSON-LD data
                    data = json.loads(json_ld_tag.string)
                    urls_found = 0

                    # Extract and save only the product URLs
                    for item in data.get("itemListElement", []):
                        product_url = item.get("url")
                        if product_url:
                            file.write(product_url + "\n")
                            urls_found += 1

                    # Log success state with URL count
                    log_state(label, page, urls_found)
                    retry_count = 0  # Reset retry count after successful request

                    # Check if there's a "next" page
                    next_link = soup.find("link", {"rel": "next"})
                    if not next_link:
                        print(f"No more pages for label {label}")
                        break

                    page += 1
                    time.sleep(2)

                except requests.exceptions.RequestException as e:
                    retry_count += 1
                    log_error("NETWORK_ERROR", str(e), url, retry_count)

                    if retry_count >= max_retries:
                        log_error("MAX_RETRIES", f"Maximum retry attempts ({max_retries}) reached", url)
                        break

                    wait_time = retry_count * 10  # Exponential backoff
                    print(f"Request error: {e}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue

                except json.JSONDecodeError as e:
                    log_error("JSON_ERROR", f"Failed to parse JSON-LD: {str(e)}", url)
                    break

                except Exception as e:
                    log_error("UNEXPECTED_ERROR", str(e), url)
                    print(f"An unexpected error occurred: {e}. Exiting...")
                    break

    except KeyboardInterrupt:
        # Save the current state before exiting
        log_error("USER_INTERRUPT", f"Script interrupted by user at letter {label}, page {page}")
        print(f"\nScript interrupted at letter {label}, page {page}. You can resume from where it left off.")

print("All links have been saved to links.txt")
