import argparse
import math
import os
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://www.welcometothejungle.com/fr/companies?page={}&aroundQuery=France%2C%20France&query=machine%20learning&refinementList%5Boffices.country_code%5D%5B%5D=FR&refinementList%5Blanguages%5D%5B%5D=fr"


class presence_of_n_element_located():
    def __init__(self, locator, comp='__eq__', n=1):
        self.locator = locator
        self.n = n
        self.comp = comp

    def __call__(self, driver):
        elements = driver.find_elements(*self.locator)
        if getattr(len(elements), self.comp)(self.n):
            return elements
        else:
            return False


def wait_page_to_load(driver, ec, delay=10):
    try:
        WebDriverWait(driver, delay).until(ec)
    except TimeoutException:
        print("Loading took too much time!")
        return False
    return True


class Bot:
    def __init__(self, args):
        self.args = args
        self.keyword = args.keyword
        self.language = args.language
        self.companies = []
        self.sent_error = 0
        self.service = webdriver.chrome.service.Service(
            ChromeDriverManager().install())
        self.service.start()

    @property
    def url(self):
        keyword = self.keyword.replace(" ", "%20")
        query = "aroundQuery=&query={}".format(keyword) if keyword else ""
        language = "refinementList%5Blanguages%5D%5B%5D={}".format(
            self.language)
        page = "page={}"
        return "https://www.welcometothejungle.com/fr/companies?" + "&".join([query, language, page])

    @property
    def blacklisted_companies(self):
        blacklisted_companies = ["fr", "wttj"]
        blacklist_path = self.args.blacklist_path
        if os.path.exists(blacklist_path):
            with open(blacklist_path, "r") as f:
                blacklisted_companies += f.read().split("\n")
        
        return blacklisted_companies

    def _build_driver(self, headless=True):
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-exteneusions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-browser-side-navigation")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-features=NetworkService")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-features=Translate")
        options.add_argument(
            "--disable-features=AutofillEnableAccountWalletStorage")
        options.add_argument("--disable-features=AutofillServerCommunication")
        options.add_argument(
            "--disable-features=AutofillEnableAccountWalletStorage")

        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--profile-directory=Default")
        options.add_argument(
            "--user-data-dir=/tmp/Default")

        driver = webdriver.Remote(self.service.service_url, options=options)

        return driver

    def _get_total_pages(self):
        driver = self._build_driver()

        driver.get(self.url.format(1))
        soup = BeautifulSoup(driver.page_source, "html.parser")

        wait_page_to_load(driver, presence_of_n_element_located(
            (By.CLASS_NAME, "ais-Hits-list-item"), '__gt__', 6))

        soup = BeautifulSoup(driver.page_source, "html.parser")

        total_pages = 1
        nav_bar = soup.find("ul", class_="hGfuih")
        if nav_bar is None:
            driver.close()
            return total_pages

        total_pages = max(int(li.text) for li in nav_bar.find_all("li") if li.text.isdigit())
        driver.close()

        return total_pages

    def get_companies(self):
        total_pages = self._get_total_pages()
        driver = self._build_driver()

        print("Scanning {} pages...".format(total_pages))
        for page in tqdm(range(0, total_pages)):
            driver.get(self.url.format(page+1))
            wait_page_to_load(driver, presence_of_n_element_located(
                (By.CLASS_NAME, "ais-Hits-list-item"), '__gt__', 6))
            soup = BeautifulSoup(driver.page_source, "html.parser")
    
            new_companies = [
                a["href"].split("/")[-2]
                for a in soup.find_all("a", href=True)
                if "/jobs" in a["href"]
            ]
            if not new_companies:
                break

            self.companies += new_companies
        self.companies = list(set(self.companies))

        driver.close()

        self.companies = [
            company for company in self.companies if company not in self.blacklisted_companies]

        if args.output_companies:
            with open(args.output_companies, "w") as f:
                f.write("\n".join(self.companies))
        return self.companies

    def ask_for_login(self):
        driver = self._build_driver(headless=False)

        driver.get("https://www.welcometothejungle.com/fr/companies")
        wait_page_to_load(driver, presence_of_n_element_located(
            (By.CLASS_NAME, "hrVedz"), '__gt__', 0), math.inf)
        driver.close()

    def send_application(self, company):
        driver = self._build_driver()
        driver.maximize_window()

        url = "https://www.welcometothejungle.com/fr/companies/" + company + "/jobs"
        driver.get(url)
        accept_candidate = wait_page_to_load(
            driver, EC.presence_of_element_located((By.CLASS_NAME, "fSKVjM")), 3)
        try:
            if not accept_candidate:
                raise("Could not find candidate button")

            dialog_btn = driver.find_element(By.CLASS_NAME, "fSKVjM")
            if dialog_btn.tag_name == "a":
                raise("Redirect to extern enterprise website")
            
            dialog_btn.click()
            wait_page_to_load(driver, EC.presence_of_element_located(
                (By.CLASS_NAME, "eRjJOf")))
                
            textarea = driver.find_element(By.CLASS_NAME, "eRjJOf")
            textarea.clear()

            if os.path.exists(self.args.cover_letter_path):
                with open(self.args.cover_letter_path, "r") as f:
                    textarea.send_keys(f.read())

            driver.find_element(By.ID, "terms").click()
            driver.find_element(By.ID, "consent").click()
        
            driver.find_element(By.CLASS_NAME, "eklxSQ").click()
            time.sleep(2) # too lazy to touch this
        except Exception as e:
            print(f"Error while sending application to {company}: {e}")
            self.sent_error += 1
        finally:
            driver.close()


argparser = argparse.ArgumentParser()

argparser.add_argument("-k", "--keyword", type=str, required=True)
argparser.add_argument("-l", "--language", type=str, choices=["fr", "en"])
argparser.add_argument("-b", "--blacklist-path", type=str)
argparser.add_argument("-c", "--cover-letter-path", type=str)
argparser.add_argument("-o", "--output-companies", type=str)

args = argparser.parse_args()

bot = Bot(args)

if args.cover_letter_path is not None:
    if not os.path.exists(args.cover_letter_path):
        print("Could not find motivation letter")
        exit(1)

    bot.ask_for_login()

companies = bot.get_companies()

if args.cover_letter_path is not None:
    print("Sending application to {} companies...".format(len(companies)))
    for company in tqdm(companies):
        bot.send_application(company)

    print("Done: {} companies have not been applied due to errors".format(bot.sent_error))
