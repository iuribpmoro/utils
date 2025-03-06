import traceback
import time
from datetime import datetime
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Discord webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/<CHANGE_THIS>"

# Flight monitoring configuration
flights_to_monitor = [
    {
        "url": "https://www.latamairlines.com/br/pt/oferta-voos?origin=<CHANGE_THIS>&outbound=<CHANGE_THIS>&destination=<CHANGE_THIS>&inbound=<CHANGE_THIS>&adt=1&chd=0&inf=0&trip=RT&cabin=Economy&redemption=false&sort=RECOMMENDED",
        "outbound_departure_time": "<CHANGE_THIS>",
        "outbound_arrival_time": "<CHANGE_THIS>",
        "inbound_departure_time": "<CHANGE_THIS>",
        "inbound_arrival_time": "<CHANGE_THIS>",
        "min_price": <CHANGE_THIS>,
        "name":"<CHANGE_THIS>"
    }
]

def send_discord_notification(message):
    data = {"content": message}
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code != 204:
        print(f"Failed to send Discord notification: {response.text}")

def get_flight_price_from_element(flight_element):
    flight_info_wrapper = flight_element.find_element(By.CSS_SELECTOR, '[id^="FlightInfoComponent"]')
    price_element = flight_info_wrapper.find_element(By.CSS_SELECTOR, '[data-testid^="flight-info-"][data-testid$="-amount"] span[class*="CurrencyAmount"]')
    price_raw = price_element.get_attribute("textContent")
    price_cleaned = price_raw.replace("\n", "").replace("\xa0", "").strip()
    price_numeric = price_cleaned.replace("brl ", "").split(",")[0]
    price_numeric = price_numeric.replace(".", "")
    return int(float(price_numeric))


def get_flight_element_from_page(flight_results, departure, arrival):
    for flight in flight_results:
        try:
            flight_info_wrapper = flight.find_element(By.CSS_SELECTOR, '[id^="FlightInfoComponent"]')
            
            # Extract departure time
            departure_time_element = flight_info_wrapper.find_element(By.CSS_SELECTOR, '[data-testid^="flight-info-"][data-testid$="-origin"] span[class*="TextHourFlight"]')
            departure_time = departure_time_element.text.strip()

            # Extract arrival time
            arrival_time_element = flight_info_wrapper.find_element(By.CSS_SELECTOR, '[data-testid^="flight-info-"][data-testid$="-destination"] span[class*="TextHourFlight"]')
            arrival_time = arrival_time_element.text.strip()
            arrival_time = arrival_time_element.text.split("\n")[0].strip()

            if departure_time == departure and arrival_time == arrival:
                # print(f"Accepted departure at {departure_time} and arrival at {arrival_time}")
                return flight
                
        except Exception:
            continue
        
    return None  # Return None if flight not found


def get_flight_price(flight):
    driver = webdriver.Chrome()
    driver.get(flight["url"])
            
    try:
        # Handle popup
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "country-suggestion-reject-change"))
        ).click()

        # Handle cookie banner
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "cookies-politics-button"))
        ).click()
        
        # Wait for the flight list to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'ol[aria-label="Voos disponíveis."]'))
        )
        
        # Locate the list of flights
        flight_list = driver.find_element(By.CSS_SELECTOR, 'ol[aria-label="Voos disponíveis."]')
        flights = flight_list.find_elements(By.TAG_NAME, "li")
        flight_element = get_flight_element_from_page(flights, flight["outbound_departure_time"], flight["outbound_arrival_time"])
        
        outbound_price = get_flight_price_from_element(flight_element)

        #return outbound_price
        if (flight["inbound_departure_time"]) == "":
            return outbound_price

        ### IF RETURN FLIGHT ####

        # Get and click on flight card button
        flight_element.find_element(By.CSS_SELECTOR, 
        'div[class*="CardExpander"]').click()
        
        # Find and scroll to the economy button
        economy_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, 
            ".//button[.//span[contains(text(), 'Light')]]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", economy_button)
        time.sleep(1)  # Small pause to let the page settle after scrolling
        # Click using JavaScript
        driver.execute_script("arguments[0].click();", economy_button)
        

        # Wait for the flight list to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, ".//span[.//strong[contains(text(), 'voo de volta')]]"))
        )
        # Wait for the flight list to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'ol[aria-label="Voos disponíveis."]'))
        )

        # Locate the list of flights
        flight_list_inbound = driver.find_element(By.CSS_SELECTOR, 'ol[aria-label="Voos disponíveis."]')
        flights_inbound = flight_list_inbound.find_elements(By.TAG_NAME, "li")
        flight_element_inbound = get_flight_element_from_page(flights_inbound, flight["inbound_departure_time"], flight["inbound_arrival_time"])
        
        inbound_price = get_flight_price_from_element(flight_element_inbound)

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
                    print(f"Current time: {datetime.now().strftime('%d-%b %H:%M:%S')}")
                    print(f"Flight {flight['name']} - Price: {price}")
                    if price < flight["min_price"]:
                        send_discord_notification(
                            f"🚨 Price Alert! Flight {flight['name']}, with outbound time {flight['outbound_departure_time']} and inbound time {flight['inbound_departure_time']}, is now R$ {price}, below your threshold of R$ {flight['min_price']}!"
                        )
                else:
                    print(f"Flight with inbound time {flight['inbound_departure_time']} and outbound time {flight['outbound_departure_time']} not found.")
            except Exception as e:
                print(f"Error monitoring flight with inbound time {flight['inbound_departure_time']} and outbound time {flight['outbound_departure_time']}: {e}")
        
        print("Waiting for 30 minutes before next check...\n")
        time.sleep(1800)  # Wait 30 minutes

if __name__ == "__main__":
    monitor_flights()
