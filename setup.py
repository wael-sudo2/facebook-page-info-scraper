from setuptools import setup, find_packages
setup(
    name='facebook_page_scrape_test1',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'geopy==2.2.0',
        'retry~=0.9.2',
        'selenium~=4.8.2',
        'googletrans~=3.1.0a0'
    ],
)