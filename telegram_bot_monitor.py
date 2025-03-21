import time
import asyncio
import ssl
import os
import subprocess
import sys

# Попытка импортировать aiohttp, если не установлен — установить
try:
    from aiohttp import web
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
    from aiohttp import web

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ModuleNotFoundError as e:
    print(f"Ошибка: {e}. Убедитесь, что Selenium и webdriver_manager установлены: pip install selenium webdriver-manager")
    webdriver = None

try:
    from telegram import Bot
except ModuleNotFoundError:
    print("Ошибка: Модуль 'telegram' не установлен. Установите его командой: pip install python-telegram-bot")
    Bot = None

# Настройки бота
CHAT_ID = "-1002662895817"
BOT_CHAT_ID = "716082742"
BOT_TOKEN = "8139250747:AAFKjsqB-RkNvyQAefzVFZU2LvCSSXhPC5E"
URL_1 = "https://hypurrscan.io/address/0xf3f496c9486be5924a93d67e98298733bb47057c"
URL_2 = "https://hypurrscan.io/address/0x20C2d95a3Dfdca9e9AD12794D5fa6FaD99dA44f5"
CHECK_INTERVAL = 300
POSITIONS_FILE_1 = r"C:\\BOT\\positions\\sent_positions_1.txt"
POSITIONS_FILE_2 = r"C:\\BOT\\positions\\sent_positions_2.txt"

print("Бот запускается...")

bot = None
if Bot:
    try:
        bot = Bot(token=BOT_TOKEN)
        print("Бот успешно инициализирован")
    except Exception as e:
        print(f"Ошибка инициализации Telegram бота: {e}")

ssl._create_default_https_context = ssl._create_unverified_context
options = Options()
options.binary_location = "/usr/bin/chromium-browser"
options.add_argument("--disable-software-rasterizer")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-features=VizDisplayCompositor")
options.add_argument("--disable-features=SurfaceSynchronization")
options.add_argument("--window-size=1920,1080")
options.add_argument("--headless=new")

try:
    service = Service(ChromeDriverManager().install())
    print("ChromeDriver установлен успешно")
except Exception as e:
    print(f"Ошибка установки ChromeDriver: {e}")
    service = None

def load_sent_positions(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as file:
            return set(file.read().splitlines())
    return set()

def save_sent_positions(filename, positions):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(positions))

async def send_telegram_message(message):
    if bot and message.strip() and "No data" not in message:
        try:
            print(f"Отправка сообщения: {message}")
            await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
            await bot.send_message(chat_id=BOT_CHAT_ID, text=message, parse_mode="Markdown")
        except Exception as e:
            print(f"Ошибка при отправке сообщения в Telegram: {e}")

def fetch_perps_positions(url):
    if webdriver is None or service is None:
        print("Ошибка: Selenium не установлен или не настроен ChromeDriver")
        return set()

    print(f"Загрузка данных с {url}")
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(5)

        perps_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@role='tab' and @value='perps']"))
        )
        perps_tab.click()
        time.sleep(5)

        perps_rows_xpath = "//div[contains(@class, 'v-table__wrapper')]//table//tbody/tr"
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.XPATH, perps_rows_xpath))
        )
        positions_elements = driver.find_elements(By.XPATH, perps_rows_xpath)
        positions = {" ".join(pos.text.strip().split()[:2]) for pos in positions_elements if pos.text.strip()}
        print(f"Полученные позиции: {positions}")
    except Exception as e:
        print(f"Ошибка при получении данных с {url}: {e}")
        positions = set()
    finally:
        driver.quit()
    return positions

async def monitor_perps():
    sent_positions_1 = load_sent_positions(POSITIONS_FILE_1)
    sent_positions_2 = load_sent_positions(POSITIONS_FILE_2)

    while True:
        current_positions_1 = fetch_perps_positions(URL_1)
        new_positions_1 = current_positions_1 - sent_positions_1
        if new_positions_1:
            await send_telegram_message(f"Новые позиции ([Кошелёк 1]({URL_1})): {', '.join(new_positions_1)}")
            sent_positions_1.update(new_positions_1)
            save_sent_positions(POSITIONS_FILE_1, sent_positions_1)

        current_positions_2 = fetch_perps_positions(URL_2)
        new_positions_2 = current_positions_2 - sent_positions_2
        if new_positions_2:
            await send_telegram_message(f"Новые позиции ([Кошелёк 2]({URL_2})): {', '.join(new_positions_2)}")
            sent_positions_2.update(new_positions_2)
            save_sent_positions(POSITIONS_FILE_2, sent_positions_2)

        await asyncio.sleep(CHECK_INTERVAL)

async def handle(request):
    return web.Response(text="Bot is running")

async def start_app():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=int(os.getenv('PORT', 10000)))
    await site.start()
    print("Веб-сервер запущен")

    await monitor_perps()

if __name__ == "__main__":
    try:
        asyncio.run(start_app())
    except Exception as e:
        print(f"Ошибка при запуске: {e}")
