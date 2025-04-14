import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import os
import re

# Define additional URLs outside the main block so they can be imported
additional_urls = [
    # Add any additional SHL catalog URLs here
    "https://www.shl.com/solutions/products/product-catalog/?start=12&type=2",
    "https://www.shl.com/solutions/products/product-catalog/?start=24&type=2",
    "https://www.shl.com/solutions/products/product-catalog/?start=36&type=2&type=2",
    "https://www.shl.com/solutions/products/product-catalog/?start=48&type=2&type=2",
    "https://www.shl.com/solutions/products/product-catalog/?start=60&type=2&type=2",
    "https://www.shl.com/solutions/products/product-catalog/?start=72&type=2&type=2",
    "https://www.shl.com/solutions/products/product-catalog/?start=84&type=2&type=2",
    "https://www.shl.com/solutions/products/product-catalog/?start=96&type=2&type=2",
    "https://www.shl.com/solutions/products/product-catalog/?start=108&type=2&type=2",
    "https://www.shl.com/solutions/products/product-catalog/?start=120&type=2&type=2",
    "https://www.shl.com/solutions/products/product-catalog/?start=132&type=2&type=2",
    "https://www.shl.com/solutions/products/product-catalog/?start=12&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=24&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=36&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=48&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=60&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=72&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=84&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=96&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=108&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=120&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=132&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=144&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=156&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=168&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=180&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=192&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=204&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=216&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=228&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=240&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=252&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=264&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=276&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=288&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=300&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=312&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=324&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=336&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=348&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=360&type=1&type=1",
    "https://www.shl.com/solutions/products/product-catalog/?start=372&type=1&type=1"
]

class SHLScraper:
    def __init__(self, base_url="https://www.shl.com/solutions/products/product-catalog/", additional_urls=None):
        self.base_url = base_url
        self.additional_urls = additional_urls or []
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.assessments = []
        
    def get_page_content(self, url):
        """Get content from a URL with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                return response.content
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retrying
                else:
                    return None

    def parse_assessment_table(self, content):
        """Parse the table of assessments from the catalog page"""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for tables in the content
        tables = soup.find_all('table')
        if not tables:
            print("No tables found on the page")
            return []
        
        assessments_found = 0
        for table in tables:
            rows = table.find_all('tr')
            # Skip header row
            for row in rows[1:]:
                assessment = {}
                cols = row.find_all('td')
                
                if len(cols) >= 1:
                    # Extract assessment name and URL
                    name_col = cols[0]
                    link = name_col.find('a')
                    if link:
                        assessment['name'] = link.text.strip()
                        assessment['url'] = link.get('href')
                        if not assessment['url'].startswith('http'):
                            assessment['url'] = f"https://www.shl.com{assessment['url']}"
                    else:
                        assessment['name'] = name_col.text.strip()
                        assessment['url'] = ""
                
                # Check for Remote Testing, Adaptive/IRT, and Test Type if available
                if len(cols) >= 2:
                    assessment['remote_testing'] = "Yes" if cols[1].text.strip() else "No"
                if len(cols) >= 3:
                    assessment['adaptive_irt'] = "Yes" if cols[2].text.strip() else "No"
                if len(cols) >= 4:
                    assessment['test_type'] = cols[3].text.strip()
                
                if assessment.get('name'):
                    self.assessments.append(assessment)
                    assessments_found += 1
        
        print(f"Found {assessments_found} assessments on the page")
        return self.assessments
    
    def find_pagination_links(self, content):
        """Find pagination links on the page"""
        soup = BeautifulSoup(content, 'html.parser')
        pagination = soup.find('nav', class_='pagination')
        
        if not pagination:
            return []
            
        links = []
        for a_tag in pagination.find_all('a', href=True):
            page_url = a_tag.get('href')
            if not page_url.startswith('http'):
                page_url = f"https://www.shl.com{page_url}"
            links.append(page_url)
            
        return links
    
    def scrape_assessment_details(self, assessment):
        """Scrape additional details from an assessment's page"""
        if not assessment.get('url'):
            return assessment
            
        content = self.get_page_content(assessment['url'])
        if not content:
            return assessment
            
        soup = BeautifulSoup(content, 'html.parser')
        
        # Try to find duration information
        duration_section = soup.find(string=re.compile("Approximate Completion Time|Assessment length", re.IGNORECASE))
        if duration_section:
            # Look for the duration value nearby
            parent = duration_section.parent
            duration_text = parent.get_text()
            # Extract number followed by "minutes"
            duration_match = re.search(r'(\d+)\s*minutes', duration_text, re.IGNORECASE)
            if duration_match:
                assessment['duration'] = duration_match.group(1)
            else:
                assessment['duration'] = duration_text.strip()
                
        return assessment
    
    def scrape_url(self, url):
        """Scrape a single URL and its pagination pages"""
        print(f"Scraping URL: {url}")
        content = self.get_page_content(url)
        if not content:
            print(f"Failed to get content from {url}")
            return
        
        # Parse the page
        self.parse_assessment_table(content)
        
        # Find and process pagination links
        pages_to_scrape = self.find_pagination_links(content)
        if pages_to_scrape:
            print(f"Found {len(pages_to_scrape)} additional pages to scrape for {url}")
            
            # Process each pagination page
            for page_url in pages_to_scrape:
                print(f"Scraping page: {page_url}")
                page_content = self.get_page_content(page_url)
                if page_content:
                    self.parse_assessment_table(page_content)
                time.sleep(2)  # Be nice to the server
    
    def scrape_catalog(self):
        """Scrape the main catalog and additional URLs, then get assessment details"""
        print(f"Starting to scrape the catalog from {self.base_url}")
        
        # Scrape the main catalog URL
        self.scrape_url(self.base_url)
        
        # Scrape any additional URLs provided
        for url in self.additional_urls:
            self.scrape_url(url)
        
        # Get detailed info for each assessment
        total_assessments = len(self.assessments)
        print(f"Total assessments found across all URLs: {total_assessments}")
        
        # Deduplicate assessments based on name or URL
        unique_assessments = []
        seen_names = set()
        seen_urls = set()
        
        for assessment in self.assessments:
            name = assessment.get('name', '')
            url = assessment.get('url', '')
            
            # Skip if we've seen this assessment before
            if name in seen_names or (url and url in seen_urls):
                continue
                
            if name:
                seen_names.add(name)
            if url:
                seen_urls.add(url)
                
            unique_assessments.append(assessment)
            
        self.assessments = unique_assessments
        print(f"Unique assessments after deduplication: {len(self.assessments)}")
        
        # Get detailed info for each unique assessment
        for i, assessment in enumerate(self.assessments):
            print(f"Scraping details for {assessment['name']} ({i+1}/{len(self.assessments)})")
            self.assessments[i] = self.scrape_assessment_details(assessment)
            # Avoid overloading the server
            time.sleep(1)
            
        return self.assessments
        
    def save_to_csv(self, filename="app/data/shl_assessments.csv"):
        """Save scraped assessments to CSV"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        df = pd.DataFrame(self.assessments)
        df.to_csv(filename, index=False)
        print(f"Saved {len(self.assessments)} assessments to {filename}")
        
    def save_to_json(self, filename="app/data/shl_assessments.json"):
        """Save scraped assessments to JSON"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(self.assessments, f, indent=2)
        print(f"Saved {len(self.assessments)} assessments to {filename}")

if __name__ == "__main__":
    # Example with additional URLs
    scraper = SHLScraper(additional_urls=additional_urls)
    assessments = scraper.scrape_catalog()
    scraper.save_to_csv()
    scraper.save_to_json() 
    