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

def create_splash(display):
    splash = displayio.Group()
    display.root_group = splash
    # Add your display elements here...
    return splash

def connect_to_wifi():
    ssid = os.getenv("WIFI_SSID")
    password = os.getenv("WIFI_PASSWORD")
    try:
        wifi.radio.connect(ssid, password)
        return wifi.radio.ipv4_address
    except Exception as e:
        return None

def create_osc_client(socket_pool):
    try:
        osc_client = microosc.OSCClient(socket_pool, "224.0.0.1", 5000)
        return osc_client
    except Exception as e:
        return None

def scroll_text(text_area, text, display, delay=0.3):
    if len(text) * 6 > 128:  # Estimate width of text
        for i in range(len(text) * 6 - 128 + 1):
            text_area.x = -i
            display.refresh()
            time.sleep(delay)
        text_area.x = 0  # Reset position after scrolling

def text(text_area, text, delay=0.3):
    text_area.x = 0
    display.refresh()
    time.sleep(delay)
    text_area.x = 0  # Reset position after scrolling
       

def main():
    display = init_oled()
    splash = create_splash(display)

    text_area = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=0, y=display.height // 2 - 3)
    splash.append(text_area)

    # WiFi and OSC Setup
    ip_address = connect_to_wifi()
    message = ""
    if ip_address:
        socket_pool = socketpool.SocketPool(wifi.radio)
        osc_client = create_osc_client(socket_pool)
        if osc_client:
            message = "Connected: {}\nOSC Ready".format(ip_address)
        else:
            message = "OSC Error"
    else:
        message = "WiFi Error"
    text_area.text = message
    scroll_text(text_area, message, display)  # Correctly passing the display object
    display.refresh()

    # Touch Pad Setup
    touch_pad = adafruit_mpr121.MPR121(board.I2C())

    last_touch_time = None

    while True:
        touch_detected = False
        for i in range(12):
            if touch_pad[i].value:
                touch_detected = True
                color = get_color_for_pad(i)
                fill_up_leds(color)  # Fill up LEDs with the color of the touched pad 
                text_area.text = 'Touched pad #{}!'.format(i)
                scroll_text(text_area, text_area.text, display.width)
                display.refresh()
                if osc_client:
                    msg = microosc.OscMsg("/touch", [i], ("i",))
                    osc_client.send(msg)
                    print(msg)
                last_touch_time = time.monotonic()
                break

        if not touch_detected and last_touch_time and (time.monotonic() - last_touch_time > 5):
            # Reset the text after 5 seconds of no activity
            text_area.text = "Touch a pad!"
            display.refresh()
            reset_leds()  # Reset LEDs after 5 seconds of no activity
            last_touch_time = None  # Reset the timer

        time.sleep(0.1)

if __name__ == "__main__":
    main()
