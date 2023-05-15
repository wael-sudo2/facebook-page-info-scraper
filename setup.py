from setuptools import setup, find_packages
setup(
    name='facebook-page-info-scraper',
    version='1.0.0',
    author='sp0T',
    author_email='wael.hkiri.dev@gmail.com',
    description='a python package capable of crawling facebook page information',
    packages=find_packages(),
    install_requires=[
        'geopy==2.2.0',
        'retry~=0.9.2',
        'selenium~=4.8.2',
        'googletrans~=3.1.0a0'
    ],
)