import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Discord webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/<CHANGE_THIS>"

# Flight monitoring configuration - Change this
flights_to_monitor = [
    {
        "url": "https://booking.flytap.com/booking/flights/deeplink?market=BR&language=en&origin=<CHANGE_THIS>&destination=<CHANGE_THIS>&flexibleDates=false&flightType=return&adt=1&chd=0&inf=0&yth=0&depDate=<CHANGE_THIS>&headerfooterhidden=false&retDate=<CHANGE_THIS>&x_tap_source=WEB&x_tap_username=&x_tap_correlationid=ed3723ab-8cae-41e8-99f9-4d71d6f3eae6",
        "outbound_departure_time": "<CHANGE_THIS>",
        "inbound_departure_time": "<CHANGE_THIS>",
        "min_price": <CHANGE_THIS>,
        "name":"<CHANGE_THIS>"
    }
]

def send_discord_notification(message):
    data = {"content": message}
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code != 204:
        print(f"Failed to send Discord notification: {response.text}")

def get_flight_price_from_page(flight_results, time_to_monitor):
    for flight in flight_results:
        try:
            # Check if it's a direct flight
            direct_span = flight.find_element(By.XPATH, ".//span[text()=' Direct ']")
            
            # Get departure time
            departure_time = flight.find_element(By.XPATH, 
                ".//div[contains(@class, 'flight-details__time-location') and contains(@class, 'is-departure')]//p[@class='bold']"
            ).text.strip()
            
            if departure_time == time_to_monitor:
                # Find the economy button and its price
                economy_button = flight.find_element(By.XPATH, 
                    ".//button[.//strong[contains(text(), 'Economy')]]"
                )
                price_element = economy_button.find_element(By.CLASS_NAME, "price")
                price_raw = price_element.text

                # Clean up the price string and convert to integer
                price_cleaned = price_raw.replace("BRL", "").replace(",", "").strip()
                return int(float(price_cleaned))
                
        except Exception:
            continue
        
    return None  # Return None if flight not found



def get_flight_price(flight):
    driver = webdriver.Chrome()
    driver.get(flight["url"])
    
    try:
        # Handle popup
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        ).click()
        
        # Wait for flight results to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "app-flight-result"))
        )
        
        # Find all flight results
        flight_results = driver.find_elements(By.TAG_NAME, "app-flight-result")
        
        outbound_price = get_flight_price_from_page(flight_results, flight["outbound_departure_time"])

        # Find and scroll to the economy button
        economy_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, 
            ".//button[.//strong[contains(text(), 'Economy')]]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", economy_button)
        time.sleep(1)  # Small pause to let the page settle after scrolling
        
        # Click using JavaScript
        driver.execute_script("arguments[0].click();", economy_button)
        
        # Wait for the discount option and scroll to it
        discount_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "brand__wrapper--discount"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", discount_section)
        time.sleep(1)
        
        # Find and click the Select button within the discount fare section
        select_button = discount_section.find_element(By.XPATH, 
            ".//button[contains(text(), 'Select')]"
        )
        driver.execute_script("arguments[0].click();", select_button)

        # Wait for and click the "Select return flight" button
        select_return_flight_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, 
            ".//button[contains(@class, 'button-accent') and contains(text(), 'Select return flight')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", select_return_flight_button)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", select_return_flight_button)

        
        # Wait for flight results to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "app-flight-result"))
        )
        
        # Find all flight results
        flight_results = driver.find_elements(By.TAG_NAME, "app-flight-result")
        
        # Get inbound flight price
        inbound_price = get_flight_price_from_page(flight_results, flight["inbound_departure_time"])

        # Calculate total price
        total_price = outbound_price + inbound_price

        return total_price
        
    finally:
        driver.quit()
        pass

def monitor_flights():
    while True:
        for flight in flights_to_monitor:
            try:
                price = get_flight_price(flight)
                if price is not None:
                    print(f"Flight with inbound time {flight['inbound_departure_time']} and outbound time {flight['outbound_departure_time']} - Price: {price}")
                    if price < flight["min_price"]:
                        send_discord_notification(
                            f"🚨 Price Alert! Flight {flight['name']}, with inbound time {flight['inbound_departure_time']} and outbound time {flight['outbound_departure_time']}, is now R$ {price}, below your threshold of R$ {flight['min_price']}!"
                        )
                else:
                    print(f"Flight with inbound time {flight['inbound_departure_time']} and outbound time {flight['outbound_departure_time']} not found.")
            except Exception as e:
                print(f"Error monitoring flight with inbound time {flight['inbound_departure_time']} and outbound time {flight['outbound_departure_time']}: {e}")
        
        print("Waiting for 30 minutes before next check...")
        time.sleep(1800)  # Wait 30 minutes

if __name__ == "__main__":
    monitor_flights()
