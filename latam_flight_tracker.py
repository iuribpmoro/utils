import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Discord webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/xxxxxx"

# Flight monitoring configuration
flights_to_monitor = [
    {
        "url": "https://www.latamairlines.com/br/pt/oferta-voos?origin=xxxxxx",
        "departure_time": "8:10",
        "min_price": 5000,
        "name":"XXX -> XXX"
    },
    {
        "url": "https://www.latamairlines.com/br/pt/oferta-voos?origin=xxxxxx",
        "departure_time": "20:20",
        "min_price": 5000,
        "name":"YYY <-> YYY"
    },
    {
        "url": "https://www.latamairlines.com/br/pt/oferta-voos?origin=xxxxxx",
        "departure_time": "12:30",
        "min_price": 5000,
        "name":"ZZZ -> ZZZ"
    },
]

def send_discord_notification(message):
    data = {"content": message}
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code != 204:
        print(f"Failed to send Discord notification: {response.text}")

def get_flight_price(url, target_departure_time):
    driver = webdriver.Chrome()  # Ensure 'chromedriver' is in your PATH or provide its path here
    driver.get(url)
    
    try:
        # Handle popup
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "country-suggestion-reject-change"))
        ).click()
        
        # Wait for the flight list to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'ol[aria-label="Voos disponíveis."]'))
        )
        
        # Locate the list of flights
        flight_list = driver.find_element(By.CSS_SELECTOR, 'ol[aria-label="Voos disponíveis."]')
        flights = flight_list.find_elements(By.TAG_NAME, "li")
        
        for flight in flights:
            try:
                flight_info_wrapper = flight.find_element(By.CSS_SELECTOR, 
                    "div.flightInfostyle__FlightInfoComponent-sc__sc-169zitd-1.jDjWUw")
                
                # Extract departure time
                time_element = flight_info_wrapper.find_element(By.CSS_SELECTOR, 
                    "div.flightInfostyle__ContainerFlightInfo-sc__sc-169zitd-3.fybJPx.flight-information span.flightInfostyle__TextHourFlight-sc__sc-169zitd-4")
                departure_time = time_element.text.strip()
                
                if departure_time == target_departure_time:
                    price_element = flight_info_wrapper.find_element(By.CSS_SELECTOR, 
                        "div.flightInfostyle__AmountInfoContainer-sc__sc-169zitd-0 span.displayCurrencystyle__CurrencyAmount-sc__sc-hel5vp-2")
                    price_raw = price_element.get_attribute("textContent")
                    price_cleaned = price_raw.replace("\n", "").replace("\xa0", "").strip()
                    price_numeric = price_cleaned.replace("brl ", "").split(",")[0]
                    price_numeric = price_numeric.replace(".", "")  # Remove the thousands separator
                    return int(price_numeric)
            except Exception:
                continue
        
        return None  # Return None if flight not found
    
    finally:
        driver.quit()

def monitor_flights():
    while True:
        for flight in flights_to_monitor:
            try:
                price = get_flight_price(flight["url"], flight["departure_time"])
                if price is not None:
                    print(f"Flight at {flight['departure_time']} - Price: {price}")
                    if price < flight["min_price"]:
                        send_discord_notification(
                            f"🚨 Price Alert! Flight {flight['name']}, departing at {flight['departure_time']}, is now R$ {price}, below your threshold of R$ {flight['min_price']}!"
                        )
                else:
                    print(f"Flight at {flight['departure_time']} not found.")
            except Exception as e:
                print(f"Error monitoring flight at {flight['departure_time']}: {e}")
        
        print("Waiting for 30 minutes before next check...")
        time.sleep(1800)  # Wait 30 minutes

if __name__ == "__main__":
    monitor_flights()
