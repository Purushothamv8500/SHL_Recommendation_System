import subprocess
import sys
import os
import time
from dotenv import load_dotenv

def check_requirements():
    """Check if requirements are installed"""
    try:
        print("Installing packages from requirements.txt...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Ensuring sentence-transformers is installed...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers==2.2.2"])
        # Additional packages for the web UI
        print("Installing FastAPI dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "jinja2"])
        print("Requirements checked/installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install requirements: {e}. Please install them manually.")
        sys.exit(1)

def run_scraper():
    """Run the web scraper to collect assessment data"""
    print("Running SHL catalog scraper...")
    try:
        from app.utils.scraper import SHLScraper
        scraper = SHLScraper()
        assessments = scraper.scrape_catalog()
        scraper.save_to_csv()
        scraper.save_to_json()
        print(f"Scraping completed. Collected {len(assessments)} assessments.")
    except Exception as e:
        print(f"Error running scraper: {str(e)}")
        sys.exit(1)

def build_vector_database():
    """Build the vector database from scraped data"""
    print("Building vector database...")
    try:
        from app.utils.vectordb import AssessmentVectorDB
        vector_db = AssessmentVectorDB()
        vector_db.build_vectordb()
        print("Vector database built successfully.")
    except Exception as e:
        print(f"Error building vector database: {str(e)}")
        sys.exit(1)

def start_api():
    """Start the FastAPI server"""
    print("Starting API server...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    )
    time.sleep(2)  # Give it time to start
    return api_process

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Setup
    check_requirements()
    
    # Ask if user wants to run the scraper (it can take time)
    run_scrape = input("Do you want to run the scraper to collect latest assessment data? (y/n): ").lower()
    if run_scrape == 'y':
        run_scraper()
    
    # Build vector database
    build_vector_database()
    
    # Start services
    api_process = start_api()
    
    print("System is running!")
    print("API is available at http://localhost:8000")
    print("Web UI is available at http://localhost:8000")
    print("Press Ctrl+C to stop...")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        api_process.terminate()
        print("Done!") 