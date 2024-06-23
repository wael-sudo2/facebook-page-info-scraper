==============================
facebook-page-info-scraper
==============================

.. image:: https://img.shields.io/pypi/v/facebook-page-info-scraper.svg
    :target: https://pypi.python.org/pypi/facebook-page-info-scraper
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/pyversions/facebook-page-info-scraper.svg
    :target: https://pypi.python.org/pypi/facebook-page-info-scraper
    :alt: Supported Python Versions

.. image:: https://static.pepy.tech/badge/facebook-page-info-scraper
    :target: https://pepy.tech/project/facebook-page-info-scraper
    :alt: Downloads

.. image:: https://static.pepy.tech/badge/facebook-page-info-scraper/month
    :target: https://pepy.tech/project/facebook-page-info-scraper
    :alt: Monthly Downloads

.. image:: https://static.pepy.tech/badge/facebook-page-info-scraper/week
    :target: https://pepy.tech/project/facebook-page-info-scraper
    :alt: Weekly Downloads

Introduction
------------

facebook-page-info-scraper is a Python package that provides a convenient way to crawl information from Facebook pages.
You'll have the power to scrape Facebook data with unlimited calls.
Whether you're a researcher, a data enthusiast, or a developer building Facebook-related projects, this library can significantly simplify your data extraction process.
It uses Selenium for web scraping and provides functionalities to retrieve page details such as page name, category, address, email, followers count, and more.

Dictionary Contents
-------------------

This section provides an overview of the dictionary contents.

Dictionary Fields
~~~~~~~~~~~~~~~~~

- `page_name`: The name of the page.
- `location`: The location of the page.
- `email`: The email associated with the page.
- `phone_number`: The phone number associated with the page.
- `social_media_links`: Links to the page's social media accounts.
- `page_website`: The website link associated with the page.
- `page_category`: The category of the page.
- `page_followers`: The number of followers.
- `page_following`: The number of following.
- `page_likes`: The number of likes.
- `page_rate`: The page rate.
- `review_number`: The number of reviews.

This section provides an overview of the dictionary keys and types.

Dictionary Keys
~~~~~~~~~~~~~~~

- `page_name`: string
- `location`: string or None
- `email`: string or None
- `phone_number`: string or list of strings or None
- `social_media_links`: string or list of strings or None
- `page_website`: string or list of strings or None
- `page_category`: string
- `page_followers`: string
- `page_following`: string
- `page_likes`: string
- `page_rate`: string
- `review_number`: string

Installation
------------

Use pip to install the package:

.. code-block:: shell

    pip install facebook_page_info_scraper

Usage
-----

To use the package, import the `FacebookPageInfoScraper` class and create an instance:

.. code-block:: python

    from facebook_page_info_scraper import FacebookPageInfoScraper
    
    # providing the page URL
    page_url = 'https://www.facebook.com/example-page'
    
    # Create an instance of the scraper
    scraper = FacebookPageInfoScraper(link=page_url)
    
    page_info = scraper.get_page_info()

    # Print page details
    print(page_info)

    page_info = {
       'page_name': 'Example Page', 
       'location': 'Some Location', 
       'email': 'example@example.com', 
       'phone_number': '+33 536337',
       'social_media_links': 'www.instagram.com/example',
       'page_website': 'http://example.com',
       'page_category': 'Some category',
       'page_likes': '36,565',
       'page_followers': '38,225'
       'page_following': '120'
       'page_rate': '33'
       'review_number': '4.6'
   }

To use the `facebook_page_info_scraper` with a specific user profile:

.. code-block:: python

    from facebook_page_info_scraper import FacebookPageInfoScraper
        
    # providing the page URL
    page_url = 'https://www.facebook.com/example-page'

    # provide location where Chrome stores profiles
    profiles_path = r'C:\Users\<username>\AppData\Local\Google\Chrome\User Data' # make sure to prefix the path with r'' to create a raw string 

    # provide the profile name with which we want to open browser
    profile = r'Profile 1' # make sure to prefix it with r'' to create a raw string 

    # Create an instance of the scraper
    scraper = FacebookPageInfoScraper(link=page_url, browser_profiles_path=profiles_path, profile_name=profile)

    page_info = scraper.get_page_info()

* To locate your Chrome profile path, you can usually find it at:

    - **Windows:**
      ``C:\Users\<username>\AppData\Local\Google\Chrome\User Data``
    - **macOS:**
      ``/Users/<username>/Library/Application Support/Google/Chrome/``
    - **Linux:**
      ``~/.config/google-chrome/`` (replace `~` with your home directory)

Contributing
------------

Contributions are welcome! If you find any issues or have suggestions for improvement, please feel free to open an issue or submit a pull request on the GitHub repository.

License
-------

This project is licensed under the MIT License. See the LICENSE file for more information.
