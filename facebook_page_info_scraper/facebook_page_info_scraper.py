from __future__ import annotations

import logging

from retry import retry
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, \
    StaleElementReferenceException
from selenium import webdriver
from typing import Optional, List, Any, Tuple, Union
from selenium.webdriver.remote.webelement import WebElement
import re
from geopy.geocoders import Nominatim
import urllib.parse
from googletrans import Translator

logger = logging.getLogger(__name__)


class FacebookPageInfoScraper:
    driver = None
    old_layout_web_element = None
    info_web_element = None

    def __init__(self, link):
        if not FacebookPageInfoScraper.driver:
            FacebookPageInfoScraper.driver = self.__private_webdriver_setup()
            self.background_image_followers = "https://static.xx.fbcdn.net/rsrc.php/v3/y9/r/arPWOVoq57s.png"
            self.background_image_likes = "https://static.xx.fbcdn.net/rsrc.php/v3/y9/r/arPWOVoq57s.png"
        self.link = link
        self.page_css_layout = self.__private_fetch_css_layout()
        self.info_web_element = self.__private_fetch_basic_info_web_element()
        self.old_layout_web_element = self.__private_fetch_old_layout_web_element()
        if self.old_layout_web_element:
            self.old_layout_text = self.__private_get_old_layout_text()
            self.old_layout_links = self.__private_get_old_layout_links()
        if self.info_web_element:
            self.new_layout_text = self.info_web_element.text
            self.new_layout_links = self.__private_get_new_layout_links()

    @staticmethod
    def __private_webdriver_setup() -> webdriver:
        try:
            options = Options()

            # Code to disable notifications pop up of Chrome Browser
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-infobars")
            options.add_argument("--mute-audio")
            options.add_argument("--start-maximized")
            options.add_argument("headless")

            web_driver = webdriver.Chrome(options=options)
            return web_driver
        except Exception as e:
            print("Error setting up webdriver.", e)
            exit(1)

    def __private_fetch_old_layout_web_element(self) -> list:
        try:
            web_element = self.driver.find_elements(By.CLASS_NAME,
                                                    value='x9orja2')
            return web_element
        except NoSuchElementException:
            logger.info("can't provide page webelements (old layout)")

    def __private_fetch_page_name(self) -> str | None:
        head = self.driver.find_element(By.TAG_NAME, value='head')
        title = head.find_element(By.TAG_NAME, value='title').get_attribute(
            'innerHTML')
        page_name = title.replace(' | Facebook', '')
        if page_name:
            return page_name
        else:
            return None

    def __private_fetch_basic_info_web_element(self) -> WebElement | None:

        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        try:
            web_element = self.driver.find_element(By.CLASS_NAME,
                                                   value='x1yztbdb')
            web_element = web_element.find_element(By.CLASS_NAME,
                                                   value='x1iyjqo2')
            return web_element
        except NoSuchElementException:
            logger.info("can't find page webelements (new layout)")
            return None

    # fetch css layout 1 or 2
    def __private_fetch_css_layout(self):
        self.driver.get(self.__private_clean(self.link))
        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        try:
            layout_2 = self.driver.find_element(By.CLASS_NAME,
                                                value='x1yztbdb')
            return layout_2.get_attribute('class')

        except NoSuchElementException:
            try:
                layout_1 = self.driver.find_element(By.CLASS_NAME,
                                                    value='x9orja2')
                return layout_1.get_attribute('class')
            except NoSuchElementException:
                return None

    @staticmethod
    def __private_link_redirection(link):
        try:
            if link[-1] == '/':
                link = link + 'about'
                return link
            else:
                link = link + '/about'
                return link
        except Exception:
            print('error getting link')

    def __private_clean(self, link):
        if 'profile.php' in link:
            link = 'https://www.facebook.com/' + (
                re.search('(?<=id=)([0-9]*)', link)).group(1)

        if '&id=' in link:
            link = 'https://www.facebook.com/' + (
                re.search('(?<=&id=)([0-9]*)', link)).group(1)

        if '?id=' in link:
            link = 'https://www.facebook.com/' + (
                re.search('(?<=\?id=)([0-9]*)', link)).group(1)

        if 'comment_id=' in link:
            link = 'https://www.facebook.com/' + (
                re.search('(?<=www.facebook.com/)([^/]*)', link)).group(1)

        link = re.sub('/pages/', '/', link)
        link = re.sub('facebook.com/category\/(.*?)\/', 'facebook.com/', link)
        link = re.sub('/posts/', '/', link)
        link = re.sub('\/photos/(.*)', '', link)
        link = re.sub('\/public/', '/', link)
        link = re.sub('\/videos/(.*)', '', link)

        link = re.sub('/posts', '/', link)
        link = re.sub('(\?)(.*)', '', link)

        link = re.sub('//pages.', '//www.', link)

        # REMOVE LINKS

        if '/people/' in link:
            return self.__private_link_redirection(link)

        if '/commerce/products/' in link or '/groups/' in link or '/hashtag/' in link or 'query=' in link:
            return self.__private_link_redirection(link)

        # REMOVE LINKS END

        try:
            link = 'https://www.facebook.com/' + (
                re.search('(?<=www.facebook.com/)([^/]*)', link)).group(1)
        except (AttributeError, TypeError):
            link = None
            pass
        return self.__private_link_redirection(link)

    @staticmethod
    def __private_translate_to_english(default_text:str):
        translator = Translator()
        translation = translator.translate(default_text, dest='en')
        return translation.text

    def __private_fetch_likes_followers_from_text_old_layout(self,default_web_element: list[WebElement]):
        found_like = False
        found_follow = False
        page_followers = None
        page_likes = None
        pattern = r"[-+]?([0-9]*(?:[,.][0-9]+|[0-9]+))"

        for element in default_web_element:
            if element.get_attribute('class') == "x78zum5 xdt5ytf xl56j7k":
                if element.text:
                    trans_text = self.__private_translate_to_english(element.text)
                    if 'like' in trans_text and not found_like:
                        page_likes = re.findall(pattern, trans_text)[0]
                        found_like = True
                    if 'follow' in trans_text and not found_follow:
                        page_followers = re.findall(pattern, trans_text)[0]
                        found_follow = True
            if found_like and found_follow:
                break

        return {'page_likes': page_likes, 'page_followers': page_followers}

    # fetch likes,followers,category at once since they
    # belong to the same parent element
    def __private_get_category_likes_followers_old_layout(self):
        parent_element = None
        category = None
        for web_element in self.old_layout_web_element:
            try:
                web_elements = web_element.find_elements(By.CLASS_NAME,
                                                         value='x78zum5')
            except NoSuchElementException:
                return None
            for element in web_elements:
                if element.get_attribute('class') == 'x78zum5':
                    category = element.text
                    dict_return = {'page_category': category}
                    parent_element = element.find_element(By.XPATH,
                                                          value='..')
                    if parent_element:

                        elements = parent_element.find_elements(By.TAG_NAME,
                                                                value="div")

                        dict_likes_followers = self.__private_fetch_likes_followers_from_text_old_layout(
                            elements)
                        dict_return.update(dict_likes_followers)
                        return dict_return
        return {'page_category': category, 'page_likes': None,
                'page_followers': None}

    def __private_get_location_old_layout(self):
        try:
            web_elements = self.driver.find_elements(By.CLASS_NAME,
                                                     value='x5yr21d')

            for element in web_elements:
                if element.get_attribute('class') == 'x5yr21d xh8yej3':
                    location_element = element.find_element(By.CLASS_NAME,
                                                            value='x1n2onr6')
                    location_div = location_element.find_element(By.TAG_NAME,
                                                                 value='div')
                    location = self.__private_geolocation(location_div)
                    return location

            return None
        except NoSuchElementException:
            logger.info("can't fetch location")

    def __private_get_old_layout_text(self):
        text = ''
        for element in self.old_layout_web_element:
            text += '\n' + element.text
        return text

    def __private_fetch_follower_likes_new_layout(self):
        all_a = self.driver.find_elements(By.TAG_NAME, value='a')
        like, following, followers = None, None, None
        counter = 0
        for a in all_a:
            if a.get_attribute('href') and 'followers' in a.get_attribute('href'):
                trans_text = self.__private_translate_to_english(a.text)
                followers = trans_text.replace('followers', '')
                counter += 1
            if a.get_attribute('href') and 'likes' in a.get_attribute('href'):
                trans_text = self.__private_translate_to_english(a.text)
                like = trans_text.replace('likes', '')
                counter += 1
            if a.get_attribute('href') and 'following' in a.get_attribute('href'):
                trans_text = self.__private_translate_to_english(a.text)
                following = trans_text.replace('following', '')
                counter += 1
            if counter > 1 :
                return {'page_likes': like, 'page_followers': followers,
                        'following': following}
        return {'page_likes': like, 'page_followers': followers,
                'following': following}

    def __private_get_new_layout_links(self):
        try:
            all_a = self.info_web_element.find_elements(By.TAG_NAME, value='a')
            return all_a
        except NoSuchElementException:
            logger.info("NoSuchElementException while fetching layout links")

    def __private_get_old_layout_links(self):
        social_media_elements = list()
        web_elements = self.driver.find_elements(By.CLASS_NAME, value='x78zum5'
                                                 )
        for element in web_elements:
            if element.get_attribute('class') == 'x78zum5':
                social_media_elements.append(element)
        all_links = list()
        for element in social_media_elements:
            links_web_element = element.find_elements(By.TAG_NAME, value='a')
            for link in links_web_element:
                all_links.append(link)
        return all_links

    def __private_get_category(self) -> Optional[str | None]:
        try:
            category_web_element = self.info_web_element.find_element(
                By.CLASS_NAME, value='xat24cr')
            category = category_web_element.text
        except NoSuchElementException:
            category = None
        return category

    @staticmethod
    def __private_fetch_phone_regex(default_text: str) -> Optional[str | None]:
        text = default_text
        try:
            phone = re.findall(
                r'([+]?[+(][0-9]{1,4}[)]?[-\s]?[0-9]{2,7}[-\s]?[0-9]{2,'
                r'7}[-\s]?[0-9]{4,10})|([\d]{2,4}-[\d]{2,4}-[\d]{2,4})',
                text)[0][0]
            if len(phone) == 1:
                return phone[0]
            return phone or None
        except IndexError:
            return None

    @staticmethod
    def __private_fetch_email_regex(default_text: str) -> list[Any]:

        text = default_text
        emails = re.findall(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)

        if len(emails) == 1:
            return emails[0]
        return emails or None

    @staticmethod
    def __private_fetch_website_regex(default_text: str) -> Union[list, str, None]:
        text = default_text
        urls = re.findall(r"(?i)\b(?:https?://|www\.)\S+\.\S+\b", text)
        if len(urls) == 1:
            return urls[0]
        return urls or None

    @staticmethod
    def __private_fetch_social_media_links(default_list: list):
        links = list()
        regex_patterns = [
            r'(https?%3A%2F%2F(?:www\.)?instagram\.com%2F[\w.-]+)',
            r'(https?%3A%2F%2F(?:www\.)?linkedin\.com%2F[\w.-]+)',
            r'(https?%3A%2F%2F(?:www\.)?youtube\.com%2F[\w.-]+)',
            r'(https?%3A%2F%2F(?:www\.)?twitter\.com%2F[\w.-]+)',
            r'(https?%3A%2F%2F(?:www\.)?pinterest\.com%2F[\w.-]+)'
        ]

        for a in default_list:
            for regex in regex_patterns:
                compiled_regex = re.compile(regex)
                link = compiled_regex.findall(a.get_attribute('href'))
                if link:
                    encoded_url = link[0]
                    decoded_url = urllib.parse.unquote(encoded_url)
                    links.append(decoded_url)
        if len(links) == 1:
            return links[0]
        return links or None

    @staticmethod
    def __private_geolocation(default_div):
        loc = default_div.get_attribute('style')
        if 'background-image:' in loc:
            pattern = r'center=([-+]?\d+\.\d+)%2C([-+]?\d+\.\d+)'
            coordinates = re.findall(pattern, loc)
            latitude = coordinates[0][0]
            longitude = coordinates[0][1]
            geolocator = Nominatim(user_agent="geoapi")
            location = geolocator.reverse(latitude + "," + longitude, timeout=10)
            location = location.raw.get('address').get('country')
            return location

    def __private_fetch_location(self):
        try:
            web_element = self.info_web_element.find_element(
                By.CLASS_NAME, value='x1hq5gj4')
            if web_element.text.endswith('Address'):
                location = web_element.text[:-len('Address ')]
                return location

            location_web_element = web_element.find_element(By.CLASS_NAME,
                                                            value='x1n2onr6')
            attrs = self.driver.execute_script(
                'var items = {}; for (index = 0; index < arguments['
                '0].attributes.length; ++index) { items[arguments['
                '0].attributes[ '
                'index].name] = arguments[0].attributes[index].value }; '
                'return '
                'items;',
                location_web_element)
            if attrs.get('style'):
                location_div = location_web_element.find_element(By.TAG_NAME,
                                                                 value='div')
                location = self.__private_geolocation(location_div)
                return location
            else:
                return None
        except NoSuchElementException:
            logging.Logger('NoSuchElementException while fetching  location')

    @staticmethod
    def __private_fetch_rate_and_reviews_regex(default_text: str):

        patterns = [r'Rating\s*·\s*(\d+(?:\.\d+)?)\s*\((\d+)\s+Reviews?\)']
        for pattern in patterns:
            match = re.search(pattern, default_text)
            if match:
                rate = match.group(1)
                reviews = match.group(2) if match.group(2) else None
                return [rate, reviews]
        return None

    @retry(exceptions=(StaleElementReferenceException, NoSuchElementException),
           delay=3, tries=3,
           logger=logger.warning("retrying to scrape link...")
           )
    def fetch_functions(self):

        layout = self.page_css_layout

        if layout == 'x1yztbdb':

           
            page_name = self.__private_fetch_page_name()
            print('scraping:', page_name)
            links = self.__private_fetch_social_media_links(
                self.new_layout_links)
            category = self.__private_get_category()
            phone = self.__private_fetch_phone_regex(self.new_layout_text)
            email = self.__private_fetch_email_regex(self.new_layout_text)
            urls = self.__private_fetch_website_regex(self.new_layout_text)
            location = self.__private_fetch_location()
            rate_reviews = self.__private_fetch_rate_and_reviews_regex(
                self.new_layout_text)
            if rate_reviews:
                review_number, rate = rate_reviews[0], rate_reviews[1]
            else:
                review_number, rate = None, None

            data_collected = {
                "page_name": page_name,
                "page_category": category,
                "email": email,
                "page_website": urls,
                "social_media_links": links,
                'phone_number': phone,
                'location': location,
                'rate_': rate,
                'review_number': review_number
            }
            likes_follow_followers = self.__private_fetch_follower_likes_new_layout()
            data_collected.update(likes_follow_followers)
            return data_collected
        elif layout == 'x9orja2':
            page_name = self.__private_fetch_page_name()
            print('scraping:', page_name)
            data_collected = {
                'page_name': page_name,
                'location': self.__private_get_location_old_layout(),
                'email': self.__private_fetch_email_regex(self.old_layout_text),
                'phone_number' : self.__private_fetch_phone_regex(self.old_layout_text),
                'social_media_links': self.__private_fetch_social_media_links(self.old_layout_links),
                'page_website': self.__private_fetch_website_regex(self.old_layout_text),
                }
            data_collected.update(
                self.__private_get_category_likes_followers_old_layout()
            )
            return data_collected
        else:
            logger.warning('the link you followed is private or not a page: ',
                           self.driver.current_url)

    def get_page_info(self):
        try:
            return self.fetch_functions()
        except (StaleElementReferenceException, NoSuchElementException) as e:
            logger.warning("Failed to fetch page data due the error", e)

