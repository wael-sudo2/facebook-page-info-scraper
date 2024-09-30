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
`facebook-page-info-scraper` is a Python package that provides a convenient way to crawl information from Facebook pages. With this package, you can scrape Facebook data with unlimited calls. Whether you're a researcher, a data enthusiast, or a developer working on Facebook-related projects, this library simplifies the data extraction process. It uses Selenium for web scraping and retrieves Facebook page details such as the page name, category, address, email, follower count, and more.

Support the Project
-------------------
If you find this project helpful, consider supporting by buying me a sandwich! 🥪

.. image:: https://github.com/wael-sudo2/bumecoffe/blob/main/buy-me-a-sandiwch-button.png
   :alt: Buy Me A Sandwich
   :target: https://www.buymeacoffee.com/sp0t__

Dictionary Contents
-------------------
This section provides an overview of the dictionary fields returned by the scraper.

### Dictionary Fields
- `page_name`: The name of the Facebook page.
- `location`: The location of the page.
- `email`: The email address associated with the page.
- `phone_number`: The phone number associated with the page.
- `social_media_links`: Social media account links of the page.
- `page_website`: The website link associated with the page.
- `page_category`: The category of the Facebook page.
- `page_followers`: The number of followers.
- `page_following`: The number of accounts the page is following.
- `page_likes`: The total number of likes on the page.
- `page_rate`: The rating of the page.
- `review_number`: The total number of reviews for the page.

### Dictionary Keys
- `page_name`: string
- `location`: string or None
- `email`: string or None
- `phone_number`: string, list of strings, or None
- `social_media_links`: string, list of strings, or None
- `page_website`: string, list of strings, or None
- `page_category`: string
- `page_followers`: string
- `page_following`: string
- `page_likes`: string
- `page_rate`: string
- `review_number`: string

Installation
------------
To install the package, run the following command:

```bash
pip install facebook_page_info_scraper
