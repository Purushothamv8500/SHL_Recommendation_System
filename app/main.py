from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from typing import Optional, List, Dict, Any
import uvicorn
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import json
import google.generativeai as genai
import sys  # Add import for flushing stdout

# Import our custom modules
from .utils.vectordb import AssessmentVectorDB

# Load environment variables
load_dotenv()

# Configure Gemini API
gemini_model = None # Revert to using gemini_model
try:
    gemini_api_key = os.environ.get("GOOGLE_API_KEY")
    if not gemini_api_key:
        print("Warning: GOOGLE_API_KEY not found in environment variables. Gemini features will be disabled.")
    else:
        # Revert to genai.configure and GenerativeModel
        genai.configure(api_key=gemini_api_key)
        gemini_model = genai.GenerativeModel('gemini-2.0-flash') # Keep the new model name
        print("Gemini Model Initialized with gemini-2.0-flash.") # Optional: Confirmation
except Exception as e:
    # Revert error message context
    print(f"Error configuring Gemini: {e}. Gemini features will be disabled.")
    gemini_model = None # Ensure model is None on error

# Initialize FastAPI app
app = FastAPI(
    title="SHL Assessment Recommendation API",
    description="API for recommending SHL assessments based on job descriptions",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Initialize vector database
vector_db = AssessmentVectorDB()

# Models
class QueryRequest(BaseModel):
    query: str
    max_results: int = 10

class AssessmentResponse(BaseModel):
    name: str
    url: str
    remote_testing: str
    adaptive_irt: str
    test_type: str
    duration: str
    gemini_summary: Optional[str] = None # Add field for Gemini's summary

class RecommendationResponse(BaseModel):
    recommendations: List[AssessmentResponse]
    gemini_raw_output: Optional[str] = None
    gemini_overall_explanation: Optional[str] = None # Add field for overall explanation

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    # Load the vector database
    try:
        global vector_db
        vector_db.load_vectordb()
    except Exception as e:
        print(f"Error loading vector database: {e}")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the HTML home page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/recommend", response_model=RecommendationResponse)
async def recommend(request: QueryRequest):
    """Recommend assessments based on a query, refined by Gemini if available"""
    try:
        # 1. Initial search from vector database - now relevance-aware
        initial_results = vector_db.search(request.query, n_results=request.max_results * 3) 

        # If we got no results due to relevance filtering
        if not initial_results:
            return RecommendationResponse(
                recommendations=[],
                gemini_overall_explanation="No semantically relevant assessments were found for this query."
            )

        # Remove any duplicates by name from initial results - strict case-insensitive deduplication
        seen_names = set()
        unique_initial_results = []
        for result in initial_results:
            # Normalize the name for comparison (lowercase and remove extra whitespace)
            normalized_name = result['name'].lower().strip()
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_initial_results.append(result)
        
        # Initial results are already relevance-filtered and deduplicated from vectordb.search
        initial_results = unique_initial_results
        final_recommendations = initial_results
        gemini_raw_output = None
        gemini_overall_explanation = None
        gemini_summaries = {} # Dictionary to hold summaries keyed by name

        # 2. Refine with Gemini if available and configured
        if gemini_model:
            try:
                # Format results for the prompt
                formatted_results_for_prompt = "\n".join([
                    f"{i+1}. Name: {res['name']}, Type: {res.get('test_type', 'N/A')}, Duration: {res.get('duration', 'N/A')} min" 
                    for i, res in enumerate(initial_results)
                ])
                
                # Updated prompt emphasizing proper ranking and no duplicates
                prompt = f"""User Query: '{request.query}'

Initial assessment recommendations based on similarity search:
{formatted_results_for_prompt}

Please analyze the user query and the initial recommendations. Identify the most relevant assessments from the provided list.

VERY IMPORTANT INSTRUCTIONS:
1. Rank the assessments from most relevant (#1) to least relevant for this specific query
2. Each assessment MUST appear EXACTLY ONCE in your recommendations
3. DO NOT recommend the same assessment multiple times with the same name
4. YOUR NUMBER ONE PRIORITY is to ensure there are NO DUPLICATE RECOMMENDATIONS
5. Check your final list carefully before submitting to ensure every name is unique
6. The ranking should be based on how well each assessment matches the user's specific needs
7. ONLY include genuinely relevant assessments - do not fill up space with irrelevant ones
8. It is better to recommend fewer but more relevant assessments than to include irrelevant ones

Then, provide:
1. An overall explanation (1-2 sentences) of why this selection is relevant to the user's query.
2. For EACH assessment you identified, provide a brief 2-line summary explaining its specific relevance to the user's query.

IMPORTANT: Use the EXACT assessment names as shown in the list above - do not change or abbreviate them. Make sure each name appears only once in your final recommendations.

Structure your response EXACTLY like this:

Overall Explanation: [Your 1-2 sentence explanation here]

Recommendations:
1. Name: [EXACT Assessment Name 1]
   Summary: [Your 2-line summary for assessment 1]
2. Name: [EXACT Assessment Name 2]
   Summary: [Your 2-line summary for assessment 2]
...
(Continue for all relevant unique recommendations)

If none of the initial recommendations seem relevant, respond ONLY with 'NONE'."""

                gemini_response = gemini_model.generate_content(prompt)
                gemini_raw_output = gemini_response.text.strip() # Store the raw output
                print(f"\n--- Raw Gemini Output ---\n{gemini_raw_output}\n-------------------------") # LOG 1: Raw Output
                sys.stdout.flush()  # Ensure output is flushed

                # --- Parse Gemini's Structured Response (Revised Logic) --- 
                if gemini_raw_output and gemini_raw_output != 'NONE':
                    lines = gemini_raw_output.split('\n')
                    recommended_names_ordered = []
                    gemini_summaries = {} # Reset summaries dict for parsing
                    current_summary_name = None
                    in_recommendations_section = False
                    current_summary_lines = []
                    gemini_overall_explanation = None # Ensure it starts as None
                    
                    print("Beginning to parse Gemini response...")
                    sys.stdout.flush()  # Ensure output is flushed

                    for i, line in enumerate(lines):
                        stripped_line = line.strip()
                        
                        # Print each line for debugging
                        print(f"Line {i}: '{stripped_line}'")

                        # Detect the overall explanation section
                        if stripped_line.startswith("Overall Explanation:"):
                            gemini_overall_explanation = stripped_line.replace("Overall Explanation:", "").strip()
                            print(f"Found Overall Explanation: {gemini_overall_explanation}")
                            in_recommendations_section = False
                            if current_summary_name and current_summary_lines:
                                gemini_summaries[current_summary_name] = "\n".join(current_summary_lines).strip()
                            current_summary_name = None
                            current_summary_lines = []

                        # Detect the recommendations section
                        elif stripped_line == "Recommendations:":
                            print("Found Recommendations section marker")
                            in_recommendations_section = True
                            if current_summary_name and current_summary_lines:
                                gemini_summaries[current_summary_name] = "\n".join(current_summary_lines).strip()
                            current_summary_name = None
                            current_summary_lines = []

                        # Handle numbered items with Name: prefix  
                        elif in_recommendations_section and (
                                stripped_line.startswith("Name:") or 
                                any(stripped_line.startswith(f"{num}. Name:") for num in range(1, 11))
                            ):
                            # Extract name from either "Name: X" or "1. Name: X" format
                            print(f"Found potential name line: '{stripped_line}'")
                            
                            # Finalize previous summary if any
                            if current_summary_name and current_summary_lines:
                                gemini_summaries[current_summary_name] = "\n".join(current_summary_lines).strip()
                                print(f"Saved summary for '{current_summary_name}'")
                            
                            # Extract name, handling numbered format
                            if any(stripped_line.startswith(f"{num}. Name:") for num in range(1, 11)):
                                # Skip the number prefix
                                name_part = stripped_line.split(". Name:", 1)[1].strip()
                            else:
                                name_part = stripped_line.replace("Name:", "", 1).strip()
                            
                            current_summary_name = name_part
                            print(f"Extracted name: '{current_summary_name}'")
                            
                            if current_summary_name:
                                recommended_names_ordered.append(current_summary_name)
                                current_summary_lines = []
                            else:
                                current_summary_name = None
                                current_summary_lines = []

                        # Handle summary lines
                        elif in_recommendations_section and current_summary_name and (
                                stripped_line.startswith("Summary:") or 
                                stripped_line.startswith("   Summary:")
                            ):
                            summary_text = stripped_line.replace("Summary:", "", 1).strip()
                            print(f"Found summary line: '{summary_text}'")
                            if summary_text:
                                current_summary_lines.append(summary_text)

                        # Capture additional summary lines that don't have a prefix
                        elif in_recommendations_section and current_summary_name and stripped_line and not any(
                                stripped_line.startswith(prefix) for prefix in ["Name:", "1.", "2.", "3.", "4.", "5."]
                            ):
                            # This is likely continuation of the summary
                            print(f"Adding to summary: '{stripped_line}'")
                            current_summary_lines.append(stripped_line)

                    # Finalize the very last summary
                    if current_summary_name and current_summary_lines:
                        gemini_summaries[current_summary_name] = "\n".join(current_summary_lines).strip()

                    print(f"\n--- Parsed Gemini Data ---") # LOG 2: Parsed Data
                    print(f"Overall Explanation: {gemini_overall_explanation}")
                    print(f"Recommended Names Ordered: {recommended_names_ordered}")
                    print(f"Summaries Dict: {json.dumps(gemini_summaries, indent=2)}")
                    print(f"--------------------------")
                    sys.stdout.flush()  # Ensure output is flushed to console
                    
                    # Filter initial results based on Gemini's recommendations + maintain order
                    if recommended_names_ordered:
                        # Create a case-insensitive mapping for better matching
                        initial_results_map = {res['name'].lower().strip(): res for res in initial_results}
                        initial_results_map_original = {res['name']: res for res in initial_results}
                        
                        print(f"Initial results map keys: {list(initial_results_map.keys())}")
                        print(f"Looking for these names: {recommended_names_ordered}")
                        sys.stdout.flush()  # Flush output
                        
                        # Create a set to track names already seen to prevent duplicates
                        seen_recommendations = set()
                        filtered_results = []
                        
                        # First, deduplicate the recommended_names_ordered list itself
                        unique_recommended_names = []
                        seen_recommended_names = set()
                        
                        for name in recommended_names_ordered:
                            normalized_name = name.lower().strip()
                            if normalized_name not in seen_recommended_names:
                                seen_recommended_names.add(normalized_name)
                                unique_recommended_names.append(name)
                        
                        # Now process the deduplicated recommended names list
                        for name in unique_recommended_names:
                            # Skip if we've already seen this name (prevent duplicates)
                            normalized_name = name.lower().strip()
                            if normalized_name in seen_recommendations:
                                print(f"Skipping duplicate: {name}")
                                continue
                            
                            # Try direct match first
                            if name in initial_results_map_original:
                                filtered_results.append(initial_results_map_original[name])
                                seen_recommendations.add(normalized_name)
                                print(f"Found direct match for: {name}")
                            # Then try case-insensitive match
                            elif normalized_name in initial_results_map:
                                filtered_results.append(initial_results_map[normalized_name])
                                seen_recommendations.add(normalized_name)
                                print(f"Found case-insensitive match for: {name}")
                            else:
                                print(f"Warning: Could not find match for recommended name: {name}")
                        
                        # If we still have no matches, something is wrong with the name extraction
                        if not filtered_results:
                            print("WARNING: No matches found between Gemini recommendations and initial results!")
                            # Use the unique_initial_results as fallback - these are already relevance filtered
                            filtered_results = unique_initial_results[:request.max_results]
                        
                        # Instead of automatically filling up to max_results, only add supplements if they're likely relevant
                        # Check if we need to supplement
                        if len(filtered_results) < request.max_results:
                            # We'll only supplement if we have genuinely relevant items
                            remaining_needed = request.max_results - len(filtered_results)
                            existing_names = set(res['name'].lower().strip() for res in filtered_results)
                            
                            supplement = []
                            for res in initial_results:
                                normalized_name = res['name'].lower().strip()
                                if normalized_name not in existing_names and len(supplement) < remaining_needed:
                                    supplement.append(res)
                                    existing_names.add(normalized_name)
                            
                            # Only add supplements if they exist in initial_results (which is already relevance-filtered)
                            if supplement:
                                filtered_results.extend(supplement)
                                print(f"Added {len(supplement)} relevant supplements to recommendations")

                        # Final recommendations are already relevance-filtered
                        final_recommendations = filtered_results
                    else:
                        # Parsing failed or Gemini didn't return names as expected
                        print("Warning: No recommended names extracted from Gemini response. Raw response follows:")
                        print(gemini_raw_output[:500])  # Print first 500 chars
                        # Use initial results which are already relevance-filtered
                        final_recommendations = initial_results[:request.max_results]
                        gemini_overall_explanation = "Could not extract assessment names from Gemini's response. Using semantically relevant search results."
                        gemini_summaries = {}
                
                elif gemini_raw_output == 'NONE':
                    final_recommendations = []
                    gemini_overall_explanation = "Gemini determined that none of the initial recommendations were relevant to the query."
                else:
                    # Gemini returned empty or unexpected response, fall back
                    print("Warning: Gemini returned an empty or unexpected response. Falling back.")
                    # Use initial results which are already relevance-filtered
                    final_recommendations = initial_results[:request.max_results]
                    # Update explanation for this case
                    if not gemini_overall_explanation:
                         gemini_overall_explanation = "Gemini did not provide a structured response or it was empty. Using semantically relevant search results."
                    gemini_summaries = {}

            except Exception as gemini_error:
                print(f"Error during Gemini API call or parsing: {gemini_error}. Falling back to vector search results.")
                # Use initial results which are already relevance-filtered
                final_recommendations = initial_results[:request.max_results] # Fallback on error
                gemini_overall_explanation = f"An error occurred during Gemini processing: {gemini_error}. Using semantically relevant search results."
                gemini_summaries = {}
        else:
             # Gemini not configured, use initial results which are already relevance-filtered
             final_recommendations = unique_initial_results[:request.max_results]
             gemini_summaries = {} # Ensure summaries are empty if Gemini wasn't used

        # 3. Convert final results to response model, adding summaries
        output_recommendations = []
        seen_output_names = set()  # Track seen names to prevent duplicates in final output
        print("\n--- Populating Final Recommendations ---") # LOG before loop
        sys.stdout.flush()  # Flush output
        
        for result in final_recommendations:
            assessment_name = result.get("name", "N/A")
            
            # Normalize the name for comparison (lowercase and remove extra whitespace)
            normalized_name = assessment_name.lower().strip()
            
            # Skip if we've already seen this name (case insensitive)
            if normalized_name in seen_output_names:
                print(f"Skipping duplicate in final output: {assessment_name}")
                continue
            
            seen_output_names.add(normalized_name)
            summary = gemini_summaries.get(assessment_name) # Add summary if found
            print(f"Lookup Summary for '{assessment_name}': '{summary}'") # LOG 3: Summary Lookup
            sys.stdout.flush()  # Flush each lookup
            output_recommendations.append(AssessmentResponse(
                name=assessment_name,
                url=result.get("url", ""),
                remote_testing=result.get("remote_testing", "N/A"),
                adaptive_irt=result.get("adaptive_irt", "N/A"),
                test_type=result.get("test_type", "N/A"),
                duration=str(result.get("duration", "N/A")), # Ensure duration is string
                gemini_summary=summary 
            ))
        print("--------------------------------------") # LOG after loop
        
        # Additional safety check to ensure no duplicates in the final output
        final_unique_recommendations = []
        seen_final_names = set()
        
        for rec in output_recommendations:
            normalized_name = rec.name.lower().strip()
            if normalized_name not in seen_final_names:
                seen_final_names.add(normalized_name)
                final_unique_recommendations.append(rec)
        
        # Include the raw Gemini output and explanation in the final response
        return RecommendationResponse(
            recommendations=final_unique_recommendations[:request.max_results], 
            gemini_raw_output=gemini_raw_output,
            gemini_overall_explanation=gemini_overall_explanation
        )
        
    except Exception as e:
        # Log the exception details for debugging
        print(f"Error processing recommendation: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing recommendation: {str(e)}")

@app.post("/recommend/text")
async def recommend_text(query: str = Form(...), max_results: int = Form(10)):
    """Recommend assessments based on a text query submitted via form"""
    request = QueryRequest(query=query, max_results=max_results)
    return await recommend(request)

@app.post("/recommend/file")
async def recommend_file(file: UploadFile = File(...), max_results: int = Form(10)):
    """Recommend assessments based on a job description file"""
    try:
        content = await file.read()
        text = content.decode("utf-8")
        
        request = QueryRequest(query=text, max_results=max_results)
        return await recommend(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

if __name__ == "__main__":
    # Run the FastAPI app
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 