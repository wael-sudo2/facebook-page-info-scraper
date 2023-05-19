==============================
facebook-page-info-scraper
==============================


.. image:: https://img.shields.io/pypi/v/facebook-page-info-scraper.svg
    :target: https://pypi.python.org/pypi/facebook-page-info-scraper
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/pyversions/facebook-page-info-scraper.svg
    :target: https://pypi.python.org/pypi/facebook-page-info-scraper
    :alt: Supported Python Versions

Introduction
------------

facebook-page-info-scraper is a Python package that provides a convenient way to crawl information from Facebook pages. It uses Selenium for web scraping and provides functionalities to retrieve page details such as page name, Category, Address, email, followers count, and more.

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
    
    page_url = 'https://www.facebook.com/example-page'
    
    # Create an instance of the scraper
    scraper = FacebookPageInfoScraper(link=page_url)
    # Scrape page information by providing the page URL
    
    page_info = scraper.get_page_info()

    # Print page details
    print(f'Page Name: {page_info["page_name"]}')
    print(f'Page Category: {page_info["page_category"]}')
    print(f'Page website: {page_info["page_website"]}')

Contributing
------------

Contributions are welcome! If you find any issues or have suggestions for improvement, please feel free to open an issue or submit a pull request on the GitHub repository.

License
-------

This project is licensed under the MIT License. See the LICENSE file for more information.
