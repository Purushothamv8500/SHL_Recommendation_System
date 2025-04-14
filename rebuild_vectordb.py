"""
Script to rebuild the vector database after scraping assessments.
"""
import os
import sys
import time
from dotenv import load_dotenv
from app.utils.vectordb import AssessmentVectorDB

def rebuild_vectordb():
    # Load environment variables
    load_dotenv()
    
    # Get Hugging Face token
    hf_token = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    
    if not hf_token:
        print("ERROR: HUGGINGFACEHUB_API_TOKEN not found in environment variables.")
        print("Please add it to your .env file or set it in your environment.")
        user_token = input("Alternatively, enter your Hugging Face token now: ").strip()
        if user_token:
            hf_token = user_token
        else:
            print("No token provided. Exiting.")
            sys.exit(1)
    
    # Initialize the vector database
    print(f"Initializing vector database with token: {hf_token[:5]}...")
    
    try:
        # Create the vector database
        vector_db = AssessmentVectorDB(hf_token=hf_token)
        
        # Check if the assessments file exists
        if not os.path.exists(vector_db.data_path):
            print(f"ERROR: Assessment data file not found at {vector_db.data_path}")
            print("Please run the scraper first to generate the data file.")
            sys.exit(1)
        
        print("Building vector database. This may take a few minutes...")
        start_time = time.time()
        
        # Build the vector database
        vector_db.build_vectordb()
        
        end_time = time.time()
        print(f"Vector database built successfully in {end_time - start_time:.2f} seconds!")
        
        # Test a sample query
        print("\nTesting a sample query...")
        results = vector_db.search("technical skills assessment for Python developers", n_results=3)
        for i, result in enumerate(results):
            print(f"{i+1}. {result['name']} - {result.get('test_type', 'N/A')}")
        
        print("\nVector database is ready for use!")
        
    except Exception as e:
        print(f"ERROR building vector database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    rebuild_vectordb() 