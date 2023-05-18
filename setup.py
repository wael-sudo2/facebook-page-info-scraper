from setuptools import setup, find_packages

with open('README.rst', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='facebook_page_info_scraper',
    version='1.0.6',
    author='Wael hkiri',
    author_email='wael.hkiri.dev@gmail.com',
    description='A Python package capable of crawling Facebook page information',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    packages=find_packages(),
    install_requires=[
    'geopy==2.2.0',
    'retry~=0.9.2',
    'selenium~=4.8.2',
    'googletrans~=3.1.0a0'
],
)
