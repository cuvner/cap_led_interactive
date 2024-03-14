import time
import os
import board
import displayio
import terminalio
import wifi
import socketpool
import microosc
import adafruit_mpr121
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import neopixel

# NeoPixel LED Setup
num_leds = 44  # Total number of LEDs
led_pin = board.D7  # Update with your actual pin
pixels = neopixel.NeoPixel(led_pin, num_leds, brightness=0.5)

def fill_up_leds(color, fill_speed=0.05):
    for i in range(num_leds):
        pixels[i] = color
        pixels.show()
        time.sleep(fill_speed)

def reset_leds():
    pixels.fill((0, 0, 0))
    pixels.show()


# Function to return color based on pad number
def get_color_for_pad(pad_number):
    colors = [
        (139, 69, 19),   # Color for pad 1: Brown, like earth
        (47, 79, 79),    # Color for pad 2: Dark Slate Gray, river stones
        (102, 205, 170), # Color for pad 3: Medium Aquamarine, shallow water
        (0, 100, 0),     # Color for pad 4: Dark Green, algae
        (32, 178, 170),  # Color for pad 5: Light Sea Green, clean river water
        (218, 165, 32),  # Color for pad 6: Golden Rod, pollution
        (95, 158, 160),  # Color for pad 7: Cadet Blue, river reflection
        (70, 130, 180),  # Color for pad 8: Steel Blue, deep river water
        (240, 248, 255), # Color for pad 9: Alice Blue, foam and bubbles
        (128, 128, 0),   # Color for pad 10: Olive, murky water
        (255, 228, 196), # Color for pad 11: Bisque, human skin tone
        (255, 127, 80)   # Color for pad 12: Coral, warning or pollution indicator
    ]
    if 0 <= pad_number < 12:
        return colors[pad_number]
    else:
        return (0, 0, 0)  # Default color if out of range



def init_oled():
    displayio.release_displays()
    oled_reset = board.D9
    i2c = board.I2C()
    display_bus = displayio.I2CDisplay(i2c, device_address=0x3C, reset=oled_reset)
    display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=32)
    return display

def init_wifi_status_label(display):
    # Initialize the WiFi status label with empty text
    wifi_status_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF)
    display.show(wifi_status_label)
    return wifi_status_label

def update_wifi_status(display, wifi_status_label, text):
    # Update the text and adjust position for right justification
    wifi_status_label.text = text
    wifi_status_label.x = display.width - len(text) * 6  # 6 is an approximation for char width


def create_splash(display):
    splash = displayio.Group()
    display.root_group = splash
    # Add your display elements here...
    return splash

def connect_to_wifi(display):
    ssid = os.getenv("WIFI_SSID")
    password = os.getenv("WIFI_PASSWORD")
    try:
        wifi.radio.connect(ssid, password)
        # You can update the display within this function, if you wish
        return True
    except Exception as e:
        return False


def create_osc_client(socket_pool):
    try:
        osc_client = microosc.OSCClient(socket_pool, "224.0.0.1", 5000)
        return osc_client
    except Exception as e:
        return None      
    
def send_osc_message(osc_client, message):
    try:
        osc_client.send(message)
    except BrokenPipeError:
        # Attempt to reconnect and resend the message
        try:
            # Recreate the OSC client or reinitialize the connection
            osc_client = create_osc_client(socketpool.SocketPool(wifi.radio))
            osc_client.send(message)
        except Exception as e:
            print("Error re-establishing OSC connection:", e)

def check_wifi_connection():
    try:
        # Attempt to get the current IP address as a way to check connectivity
        ip_address = wifi.radio.ipv4_address
        return ip_address is not None
    except Exception as e:
        # Handle exceptions if WiFi module is not responding
        return False  

def reconnect_to_wifi(display):
    try:
        ssid = os.getenv("WIFI_SSID")
        password = os.getenv("WIFI_PASSWORD")
        wifi.radio.connect(ssid, password)
        return True
    except Exception as e:
        # Update the display with an error message if needed
        return False
          


def main():
    display = init_oled()
    splash = create_splash(display)

    # check wifi
    wifi_connected = True  # Initial assumption
    last_check_time = time.monotonic()
    check_interval = 10  # Time in seconds between checks


    # Display the initial "WiFi connecting...." message
    initial_message_label = label.Label(terminalio.FONT, text="WiFi connecting....", color=0xFFFFFF, x=0, y=display.height // 2 - 3)
    splash.append(initial_message_label)
    display.show(splash)

    # Connect to WiFi and update WiFi status label
    ip_address = connect_to_wifi(display)

    # Initialize WiFi status label
    wifi_status_label = label.Label(terminalio.FONT, text="W-Osc" if ip_address else "No WiFi", color=0xFFFFFF, x=display.width - 35, y=6)
    splash.append(wifi_status_label)

    # Initialize the touch pad message label and remove the initial message
    touch_message_label = label.Label(terminalio.FONT, text="Touch a pad!", color=0xFFFFFF, x=0, y=display.height // 2 + 3 )
    splash.append(touch_message_label)
    splash.remove(initial_message_label)

    display.refresh()

    # Setup OSC client if connected to WiFi
    osc_client = create_osc_client(socketpool.SocketPool(wifi.radio)) if ip_address else None

    # Touch Pad Setup
    touch_pad = adafruit_mpr121.MPR121(board.I2C())
    last_touch_time = None
    last_wifi_check = time.monotonic()
    wifi_check_interval = 5  # Time in seconds to check WiFi status

    while True:

        current_time = time.monotonic()

        # Periodically check WiFi status
        if current_time - last_wifi_check > wifi_check_interval:
            wifi_connected = check_wifi_connection()
            if not wifi_connected:
                wifi_connected = reconnect_to_wifi(display)
            wifi_status_label.text = "W-Osc" if wifi_connected else "No WiFi"
            last_wifi_check = current_time
            
        # Touch pad detection logic
        touch_detected = False
        for i in range(12):
            if touch_pad[i].value:
                touch_detected = True
                touch_message_label.text = f'Touched pad #{i + 1}!'
                fill_up_leds(get_color_for_pad(i))  # Fill up LEDs with the color of the touched pad

                if osc_client and touch_detected:
                    osc_message = microosc.OscMsg("/touch", [i], ("i",))
                    send_osc_message(osc_client, osc_message)

                last_touch_time = time.monotonic()
                break

        if not touch_detected and last_touch_time and (time.monotonic() - last_touch_time > 5):
            touch_message_label.text = "Touch a pad!"
            reset_leds()
            last_touch_time = None

        display.refresh()
        time.sleep(0.2)

if __name__ == "__main__":
    main()