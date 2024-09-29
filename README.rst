==============================
facebook-page-info-scraper
==============================

Support the Project
===================

If you find this project helpful, consider buying me a coffee!

.. image:: https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png
   :alt: Buy Me A Coffee
   :height: 60px
   :width: 217px
   :target: https://www.buymeacoffee.com/sp0t__

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

`facebook-page-info-scraper` is a Python package that provides a convenient way to crawl information from Facebook pages. You'll have the power to scrape Facebook data with unlimited calls. Whether you're a researcher, a data enthusiast, or a developer building Facebook-related projects, this library can significantly simplify your data extraction process. It uses Selenium for web scraping and provides functionalities to retrieve page details such as page name, category, address, email, followers count, and more.

Dictionary Contents
-------------------

This section provides an overview of the dictionary contents.

### Dictionary Fields

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

### Dictionary Keys

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

```shell
pip install facebook_page_info_scraper
