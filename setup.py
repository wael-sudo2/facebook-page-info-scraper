from setuptools import setup, find_packages

with open('README.rst', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='facebook-page-info-scraper',
    version='1.0.2',
    author='Wael hkiri',
    author_email='wael.hkiri.dev@gmail.com',
    description='A Python package capable of crawling Facebook page information',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    packages=find_packages(),
    install_requires=[
        'geopy @ https://files.pythonhosted.org/packages/9f/ab/1274d2bda70aa733d5a150aecc9fc64fc41df8c1654cd397a9307253161e/geopy-2.2.0.tar.gz',
        'retry @ https://files.pythonhosted.org/packages/9d/72/75d0b85443fbc8d9f38d08d2b1b67cc184ce35280e4a3813cda2f445f3a4/retry-0.9.2.tar.gz',
        'selenium @ https://files.pythonhosted.org/packages/fd/e2/0e5bee6762a7bf7852b47a79c5b12f9e526e6962958dbb9719fa490ba24c/selenium-4.9.1.tar.gz',
        'googletrans @ https://files.pythonhosted.org/packages/19/3d/4e3a1609bf52f2f7b00436cc751eb977e27040665dde2bd57e7152989672/googletrans-3.1.0a0.tar.gz'
    ],
)
