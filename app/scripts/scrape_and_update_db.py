#!/usr/bin/env python3
"""
Script to scrape all SHL assessments and update the vector database.
Usage:
    python -m app.scripts.scrape_and_update_db [additional_url1] [additional_url2] ...
"""
import os
import sys
import time
import argparse

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the scraper and vector DB classes
from utils.scraper import SHLScraper
from utils.vectordb import AssessmentVectorDB

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape SHL assessments and update the vector database')
    parser.add_argument('urls', nargs='*', help='Additional URLs to scrape')
    parser.add_argument('--use-default-additional-urls', action='store_true', 
                       help='Use the default additional URLs defined in scraper.py')
    parser.add_argument('--huggingface-token', type=str, help='HuggingFace API token')
    args = parser.parse_args()
    
    # Set environment variable for HuggingFace
    if args.huggingface_token:
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = args.huggingface_token
        print(f"Set HUGGINGFACEHUB_API_TOKEN environment variable")
    
    # Get additional URLs
    additional_urls = args.urls
    
    # Import additional URLs from scraper.py if requested
    if args.use_default_additional_urls:
        try:
            # Access the additional_urls directly from the scraper module
            from utils.scraper import additional_urls as default_urls
            additional_urls.extend(default_urls)
            print(f"Added {len(default_urls)} default additional URLs from scraper.py")
        except (ImportError, AttributeError):
            # Fall back to importing manually
            print("Unable to access default additional URLs from scraper.py")
    
    print("Starting SHL assessment scraping process...")
    if additional_urls:
        print(f"Additional URLs to scrape: {len(additional_urls)}")
        for i, url in enumerate(additional_urls[:3]):
            print(f"  - {url}")
        if len(additional_urls) > 3:
            print(f"  - ... and {len(additional_urls) - 3} more")
    
    # Step 1: Run the scraper to get all assessments
    scraper = SHLScraper(additional_urls=additional_urls)
    assessments = scraper.scrape_catalog()
    
    # Step 2: Save the scraped data
    scraper.save_to_json()
    scraper.save_to_csv()  # Optional, for backup
    
    print(f"Successfully scraped {len(assessments)} assessments!")
    
    # Check if HuggingFace token is set
    if "HUGGINGFACEHUB_API_TOKEN" not in os.environ:
        print("\nWARNING: HUGGINGFACEHUB_API_TOKEN environment variable is not set.")
        print("Vector database rebuilding will fail without this token.")
        print("You can provide it using --huggingface-token parameter.")
        user_response = input("Do you want to continue anyway? (y/n): ")
        if user_response.lower() != 'y':
            print("Exiting without rebuilding vector database.")
            return
    
    # Step 3: Rebuild the vector database
    print("\nRebuilding the vector database...")
    try:
        vector_db = AssessmentVectorDB()
        
        # Force rebuild by deleting the existing database first
        import shutil
        if os.path.exists(vector_db.persist_dir):
            print(f"Removing existing vector database at {vector_db.persist_dir}")
            shutil.rmtree(vector_db.persist_dir)
        
        # Build new database
        vector_db.build_vectordb()
        
        print("\nScraping and database update completed successfully!")
        print(f"Total assessments in database: {len(assessments)}")
    except Exception as e:
        print(f"\nError rebuilding vector database: {e}")
        print("The assessments were scraped and saved successfully, but the vector database was not updated.")

if __name__ == "__main__":
    start_time = time.time()
    main()
    elapsed_time = time.time() - start_time
    print(f"\nTotal execution time: {elapsed_time:.2f} seconds") 