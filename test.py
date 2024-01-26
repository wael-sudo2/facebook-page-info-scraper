from facebook_page_info_scraper import FacebookPageInfoScraper

# providing the page URL
page_url = 'https://www.facebook.com/alexpoffisiell/'

# Create an instance of the scraper
scraper = FacebookPageInfoScraper(link=page_url)

page_info = scraper.get_page_info()

# Print page details
print(page_info)