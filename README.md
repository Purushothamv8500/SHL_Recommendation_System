# SHL Assessment Recommendation System

This project builds an intelligent recommendation system for SHL assessments. It helps hiring managers find the most appropriate assessments for their job openings by analyzing job descriptions or natural language queries.

## Features

- Web scraper to extract assessment data from SHL's product catalog
- Vector database for semantic search capabilities
- FastAPI backend for serving recommendations
- Modern HTML/CSS/JS web interface with improved UX and dark/light mode toggle
- Support for text queries, job descriptions, and file uploads

## Project Structure

```
├── app/
│   ├── data/          # Data storage for assessments and vector database
│   ├── models/        # Data models
│   ├── utils/         # Utility functions including scraper and vector database
│   ├── static/        # Static assets for web UI (CSS, JS, images)
│   │   ├── css/       # CSS stylesheets
│   │   ├── js/        # JavaScript files
│   │   └── img/       # Images and icons
│   ├── templates/     # HTML templates for the web UI
│   └── main.py        # FastAPI application
├── requirements.txt   # Dependencies
├── run.py             # Script to run the entire system
└── README.md          # This file
```

## Detailed Installation Guide

### Prerequisites

Before you begin, ensure you have the following installed on your machine:

- Python 3.8 or higher
- pip (Python package installer)
- Git (optional, for cloning the repository)

### Step 1: Get the Code

Either clone the repository using Git:

```bash
git clone https://github.com/yourusername/shl-assessment-recommender.git
cd shl-assessment-recommender
```

Or download and extract the ZIP file from the repository and navigate to the extracted folder.

### Step 2: Set Up a Virtual Environment (Recommended)

It's recommended to use a virtual environment to avoid conflicts with other Python projects:

For Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

For macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Configure Google API Key (for Gemini Integration)

Create a .env file in the project root directory:

```bash
# Windows
echo GOOGLE_API_KEY=your_google_api_key > .env

# macOS/Linux
echo "GOOGLE_API_KEY=your_google_api_key" > .env
```

Replace `your_google_api_key` with your actual Google API key for Gemini. You can obtain a key from the [Google AI Studio](https://makersuite.google.com/).

### Step 4: Run the Application

The application comes with a convenience script that handles installation of dependencies, builds the vector database, and starts the server:

```bash
python run.py
```

During first run, the script will:

1. Install all required dependencies automatically
2. Ask if you want to run the scraper to collect the latest assessment data (recommended for first-time setup)
3. Build the vector database from the assessment data
4. Start the FastAPI server on http://localhost:8000

You can now access the web interface by opening http://localhost:8000 in your browser.

### Step 5: Using the Application

1. Once the application is running, you'll see the modern web interface in your browser.
2. You can:
   - Enter simple queries in the search box
   - Switch to "Job Description" mode to paste longer job descriptions
   - Upload files (PDF, DOCX, TXT) containing job descriptions
3. Toggle between dark and light modes using the icon in the upper right corner.

## Troubleshooting

### Common Issues

1. **Dependencies fail to install**
   - Try installing them manually:
   ```bash
   pip install -r requirements.txt
   pip install sentence-transformers==2.2.2
   pip install jinja2
   ```

2. **Port 8000 is already in use**
   - Edit the port in `run.py` by changing `--port 8000` to a different number (e.g., 8080)

3. **Vector database errors**
   - Make sure you have sufficient disk space
   - Try deleting the `app/data/vectordb` directory and rebuilding:
   ```bash
   python rebuild_vectordb.py
   ```

4. **File upload issues**
   - Ensure you're using supported file formats (PDF, DOCX, TXT)
   - Check file size (limit: 10MB)

### Advanced Configuration

- The application can be configured to run on a different port by modifying the `start_api` function in `run.py`
- For production deployment, consider using a proper WSGI server like Gunicorn and a reverse proxy like Nginx

## API Endpoints

The system provides the following API endpoints:

- `GET /`: Root endpoint returning the web UI
- `POST /recommend`: Recommends assessments based on a JSON query
- `POST /recommend/text`: Recommends assessments based on a form-submitted text query
- `POST /recommend/file`: Recommends assessments based on an uploaded file

## Approach

1. **Data Collection**: The system scrapes assessment data from SHL's product catalog, including details like assessment name, URL, remote testing support, adaptive testing support, test type, and duration.

2. **Vector Database**: Assessment descriptions are embedded into vector space using Hugging Face's sentence-transformers model, enabling semantic search.

3. **Recommendation Engine**: When a query is submitted, it's converted to the same vector space and compared with assessment vectors to find the most relevant matches.

4. **User Interface**: A modern, responsive web interface with dark/light mode toggle for enhanced user experience.

## Future Improvements

- Add filters for assessment parameters (duration, test type, etc.)
- Implement user feedback loop to improve recommendations
- Add authentication for API access
- Deploy to cloud platform with CI/CD pipeline 