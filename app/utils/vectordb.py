import os
import json
import pandas as pd
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceHubEmbeddings
from langchain.schema.document import Document
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AssessmentVectorDB:
    def __init__(self, data_path="app/data/shl_assessments.json", persist_dir="app/data/vectordb", hf_token=None):
        """Initialize the vector database"""
        self.data_path = data_path
        self.persist_dir = persist_dir
        
        # Try to get token from parameter, then environment
        self.hf_token = hf_token or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
        
        if not self.hf_token:
            print("WARNING: No Hugging Face token found. Vector operations will fail.")
            print("Set HUGGINGFACEHUB_API_TOKEN in your .env file or pass it as a parameter.")
            self.embeddings = None
        else:
            self.embeddings = HuggingFaceHubEmbeddings(
                repo_id="sentence-transformers/all-MiniLM-L6-v2",
                huggingfacehub_api_token=self.hf_token
            )
        
        self.vectordb = None
        
    def load_assessments(self):
        """Load assessments from JSON file"""
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Assessment data file not found: {self.data_path}")
            
        with open(self.data_path, 'r') as f:
            assessments = json.load(f)
            
        return assessments
        
    def create_documents(self, assessments):
        """Convert assessments to Document objects for the vector database"""
        documents = []
        
        for assessment in assessments:
            # Create a rich text representation of the assessment
            content = f"Assessment Name: {assessment.get('name', '')}\n"
            
            if assessment.get('test_type'):
                content += f"Test Type: {assessment.get('test_type', '')}\n"
                
            if assessment.get('remote_testing'):
                content += f"Remote Testing Support: {assessment.get('remote_testing', '')}\n"
                
            if assessment.get('adaptive_irt'):
                content += f"Adaptive/IRT Support: {assessment.get('adaptive_irt', '')}\n"
                
            if assessment.get('duration'):
                content += f"Duration: {assessment.get('duration', '')} minutes\n"
            
            # Add metadata
            metadata = {
                "name": assessment.get('name', ''),
                "url": assessment.get('url', ''),
                "remote_testing": assessment.get('remote_testing', 'No'),
                "adaptive_irt": assessment.get('adaptive_irt', 'No'),
                "test_type": assessment.get('test_type', ''),
                "duration": assessment.get('duration', '')
            }
            
            # Create document
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
            
        return documents
        
    def build_vectordb(self):
        """Build the vector database from assessments"""
        # Check if embeddings are available
        if not self.embeddings:
            raise ValueError("No embeddings available. Please provide a valid Hugging Face token.")
            
        # Load assessments
        assessments = self.load_assessments()
        
        # Convert to documents
        documents = self.create_documents(assessments)
        
        # Create and persist the vector database
        self.vectordb = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_dir
        )
        
        # Persist the database
        self.vectordb.persist()
        
        print(f"Vector database created with {len(documents)} documents and persisted to {self.persist_dir}")
        return self.vectordb
        
    def load_vectordb(self):
        """Load an existing vector database"""
        # Check if embeddings are available
        if not self.embeddings:
            raise ValueError("No embeddings available. Please provide a valid Hugging Face token.")
            
        if not os.path.exists(self.persist_dir):
            print(f"Vector database not found at {self.persist_dir}. Building new database.")
            return self.build_vectordb()
            
        self.vectordb = Chroma(
            persist_directory=self.persist_dir,
            embedding_function=self.embeddings
        )
        
        print(f"Loaded vector database from {self.persist_dir}")
        return self.vectordb
        
    def search(self, query, n_results=10, **kwargs):
        """Search the vector database"""
        if not self.vectordb:
            self.load_vectordb()
            
        # Increase search results to have more candidates for deduplication
        n_search_results = n_results * 10  # Get many more results to ensure high-quality after filtering
            
        # Search with metadata and scores
        results_with_scores = self.vectordb.similarity_search_with_relevance_scores(query, k=n_search_results)
        
        # Set minimum relevance threshold - only include results that are actually relevant
        # This value may need to be tuned based on the specific embeddings and use case
        min_relevance_threshold = 0.3
        
        # Convert results to a list of dictionaries with scores
        assessments = []
        seen_names = set()  # Track names to avoid duplicates
        
        for doc, score in results_with_scores:
            # Get the name and normalize it for comparison
            name = doc.metadata.get('name', '')
            normalized_name = name.lower().strip()
            
            # Skip duplicates by name (strict case insensitive)
            if normalized_name in seen_names:
                continue
                
            # Skip items below the relevance threshold - don't include irrelevant results
            if score < min_relevance_threshold:
                # Print debug info for threshold filtering
                print(f"Filtered out '{name}' with low relevance score: {score} (threshold: {min_relevance_threshold})")
                continue
                
            # Add this name to seen set
            seen_names.add(normalized_name)
            
            # Create assessment with relevance score
            assessment = doc.metadata.copy()
            assessment['relevance_score'] = score
            assessments.append(assessment)
            
        # Ensure list is properly sorted by relevance score (highest first)
        assessments = sorted(assessments, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Print the scoring and ranking info for debugging
        print(f"\n--- Semantic Search Results (Top {min(len(assessments), n_results)}) ---")
        for i, assessment in enumerate(assessments[:n_results]):
            print(f"{i+1}. {assessment['name']}: Score {assessment['relevance_score']:.4f}")
        print("-------------------------------")
        
        # Perform final filtering and deduplication
        final_assessments = []
        final_seen_names = set()
        
        for assessment in assessments:
            normalized_name = assessment.get('name', '').lower().strip()
            
            if normalized_name not in final_seen_names:
                final_seen_names.add(normalized_name)
                
                # Remove the score from the output copy but keep it for logging
                assessment_copy = assessment.copy()
                score = assessment_copy.get('relevance_score', 0)
                
                if 'relevance_score' in assessment_copy:
                    del assessment_copy['relevance_score']
                    
                final_assessments.append(assessment_copy)
                
                # Log the final selected assessment
                print(f"Selected: '{assessment.get('name', '')}' with relevance score: {score:.4f}")
            
            # Break if we have enough results
            if len(final_assessments) >= n_results:
                break
        
        # Only return results that passed the relevance threshold
        # This ensures we don't just fill the slots with irrelevant matches
        return final_assessments

if __name__ == "__main__":
    # Example usage
    vector_db = AssessmentVectorDB()
    
    # Build or load the database
    db = vector_db.load_vectordb()
    
    # Example search
    results = vector_db.search("technical skills assessment for Python developers", n_results=5)
    for i, result in enumerate(results):
        print(f"{i+1}. {result['name']} - {result['url']}") 