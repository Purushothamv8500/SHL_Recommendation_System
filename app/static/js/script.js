// Initialize global variable for results display function
window.displayResults = null;

document.addEventListener('DOMContentLoaded', () => {
    // API endpoint
    const API_ENDPOINT = "http://localhost:8000";

    // DOM elements
    const themeToggle = document.querySelector('.theme-toggle');
    const searchInput = document.getElementById('search-input');
    const searchButtons = document.querySelectorAll('.search-action-btn');
    const searchSubmitBtn = document.getElementById('search-submit');
    const fileUploadArea = document.getElementById('file-upload-area');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const removeFileBtn = document.getElementById('remove-file');
    const resultsSection = document.getElementById('results-section');
    const loadingSpinner = document.getElementById('loading-spinner');
    const resultsContent = document.getElementById('results-content');
    const resultsTbody = document.getElementById('results-tbody');
    const noResults = document.getElementById('no-results');
    const explanationText = document.getElementById('explanation-text');
    const browseLink = document.querySelector('.browse-link');

    // Current action state
    let currentAction = 'query';
    let fileSelected = false;

    // Initialize theme from localStorage or default to dark mode
    const savedTheme = localStorage.getItem('lightMode');
    if (savedTheme === 'true') {
        document.body.classList.add('light-mode');
        document.body.classList.remove('dark-mode');
        themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
    } else {
        // Default is dark mode
        document.body.classList.add('dark-mode');
        document.body.classList.remove('light-mode');
        themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    }

    // Add initial animations
    setTimeout(() => {
        document.querySelectorAll('.animate-fadeIn').forEach(el => {
            el.style.opacity = '1';
        });
    }, 100);

    // Event Listeners
    // Theme toggle
    themeToggle.addEventListener('click', () => {
        const isLightMode = document.body.classList.contains('light-mode');
        if (isLightMode) {
            // Switch to dark mode
            document.body.classList.remove('light-mode');
            document.body.classList.add('dark-mode');
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
            localStorage.setItem('lightMode', 'false');
        } else {
            // Switch to light mode
            document.body.classList.remove('dark-mode');
            document.body.classList.add('light-mode');
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
            localStorage.setItem('lightMode', 'true');
        }
    });

    // Action button selection
    searchButtons.forEach(button => {
        button.addEventListener('click', () => {
            const action = button.getAttribute('data-action');
            
            // Update active state
            searchButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Handle action change
            currentAction = action;
            
            // Toggle file upload area visibility
            if (action === 'upload') {
                fileUploadArea.style.display = 'block';
                // If a file is already selected, show file info instead
                if (fileSelected) {
                    fileUploadArea.style.display = 'none';
                    fileInfo.style.display = 'flex';
                }
            } else {
                fileUploadArea.style.display = 'none';
                fileInfo.style.display = 'none';
            }
            
            // Update placeholder based on action
            if (action === 'query') {
                searchInput.placeholder = 'Enter your query...';
                // Reset input height for query mode
                searchInput.style.height = '';
                searchInput.style.minHeight = '';
            } else if (action === 'job-desc') {
                searchInput.placeholder = 'Paste job description here...';
                // Apply textarea-like styling for job description
                searchInput.style.minHeight = '150px';
                searchInput.style.height = 'auto';
                searchInput.style.resize = 'vertical';
                searchInput.style.padding = '1rem';
                searchInput.style.whiteSpace = 'pre-wrap';
                searchInput.style.overflowY = 'auto';
                searchInput.style.lineHeight = '1.6';
                searchInput.style.borderRadius = '15px';
                searchInput.focus();
            } else {
                searchInput.placeholder = 'Describe file contents (optional)';
                // Reset input height for upload mode
                searchInput.style.height = '';
                searchInput.style.minHeight = '';
            }
        });
    });

    // Submit button click
    searchSubmitBtn.addEventListener('click', handleSubmit);
    
    // Enter key in search input
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && currentAction !== 'job-desc') {
            handleSubmit();
        }
    });

    // Auto-resize input for job description
    searchInput.addEventListener('input', () => {
        if (currentAction === 'job-desc') {
            // Allow the input to grow with content
            searchInput.style.height = 'auto';
            searchInput.style.height = (searchInput.scrollHeight) + 'px';
        }
    });

    // Handle form submission based on current action
    function handleSubmit() {
        const query = searchInput.value.trim();
        
        // Basic validation
        if (currentAction !== 'upload' && query === '') {
            // Highlight input field for error
            searchInput.style.borderColor = 'var(--danger-color)';
            setTimeout(() => {
                searchInput.style.borderColor = '';
            }, 2000);
            return;
        }
        
        if (currentAction === 'upload' && !fileSelected) {
            // Highlight upload area for error
            fileUploadArea.style.borderColor = 'var(--danger-color)';
            setTimeout(() => {
                fileUploadArea.style.borderColor = '';
            }, 2000);
            return;
        }
        
        // Add button click effect
        addButtonClickEffect(searchSubmitBtn);
        
        // Process based on action type
        if (currentAction === 'upload' && fileSelected) {
            uploadFileForRecommendations(fileInput.files[0]);
        } else {
            getRecommendations(query);
        }
    }

    // File upload handling
    browseLink.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', handleFileSelection);

    // Drag and drop functionality
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, () => {
            fileUploadArea.classList.add('highlight');
            fileUploadArea.style.transform = 'scale(1.02)';
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, () => {
            fileUploadArea.classList.remove('highlight');
            fileUploadArea.style.transform = 'scale(1)';
        }, false);
    });

    fileUploadArea.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        
        if (file) {
            fileInput.files = dt.files;
            handleFileSelection();
            
            // Add a success animation
            fileUploadArea.style.borderColor = 'var(--success-color)';
            setTimeout(() => {
                fileUploadArea.style.borderColor = '';
            }, 1000);
        }
    });

    removeFileBtn.addEventListener('click', () => {
        fileInput.value = '';
        fileInfo.style.display = 'none';
        fileUploadArea.style.display = 'block';
        fileSelected = false;
        
        // Add animation
        fileUploadArea.classList.add('animate-fadeIn');
        setTimeout(() => {
            fileUploadArea.classList.remove('animate-fadeIn');
        }, 500);
    });

    function handleFileSelection() {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            fileName.textContent = file.name;
            fileUploadArea.style.display = 'none';
            fileInfo.style.display = 'flex';
            fileSelected = true;
            
            // Add animation
            fileInfo.classList.add('animate-fadeIn');
            setTimeout(() => {
                fileInfo.classList.remove('animate-fadeIn');
            }, 500);
        }
    }

    // Button click effect
    function addButtonClickEffect(button) {
        if (!button) return;
        
        const ripple = document.createElement('span');
        ripple.classList.add('ripple-effect');
        button.appendChild(ripple);
        
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        
        ripple.style.width = ripple.style.height = `${size}px`;
        ripple.style.left = `${rect.width / 2 - size / 2}px`;
        ripple.style.top = `${rect.height / 2 - size / 2}px`;
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    // API calls
    async function getRecommendations(query) {
        showLoading();
        try {
            // Using fixed max_results instead of slider value
            const maxResults = 10;
            
            const response = await fetch(`${API_ENDPOINT}/recommend`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    max_results: maxResults
                })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            displayResults(data);
        } catch (error) {
            console.error('Error:', error);
            showError("Error fetching recommendations. Please try again.");
        }
    }

    async function uploadFileForRecommendations(file) {
        showLoading();
        try {
            // Using fixed max_results instead of slider value
            const maxResults = 10;
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('max_results', maxResults);

            const response = await fetch(`${API_ENDPOINT}/recommend/file`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            displayResults(data);
        } catch (error) {
            console.error('Error:', error);
            showError("Error processing file. Please try again.");
        }
    }

    // UI update functions
    function showLoading() {
        resultsSection.style.display = 'block';
        loadingSpinner.style.display = 'flex';
        resultsContent.style.display = 'none';
        noResults.style.display = 'none';
        
        // Enhanced animation
        loadingSpinner.classList.add('animate-fadeIn');
        
        // Scroll to results with smooth animation
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function showError(message) {
        loadingSpinner.style.display = 'none';
        resultsContent.style.display = 'none';
        noResults.style.display = 'flex';
        noResults.querySelector('p').textContent = message;
        
        // Add animation
        noResults.classList.add('animate-fadeIn');
        setTimeout(() => {
            noResults.classList.remove('animate-fadeIn');
        }, 500);
    }

    // Make the display results function accessible globally
    window.displayResults = function(data) {
        loadingSpinner.style.display = 'none';
        
        if (!data.recommendations || data.recommendations.length === 0) {
            // No results
            noResults.style.display = 'flex';
            resultsContent.style.display = 'none';
            
            // Display explanation if available
            if (data.gemini_overall_explanation) {
                noResults.querySelector('p').textContent = data.gemini_overall_explanation;
            } else {
                noResults.querySelector('p').textContent = "No relevant assessments found based on your query.";
            }
            
            // Add animation
            noResults.classList.add('animate-fadeIn');
            setTimeout(() => {
                noResults.classList.remove('animate-fadeIn');
            }, 500);
            
            return;
        }

        // Show results
        resultsContent.style.display = 'block';
        noResults.style.display = 'none';
        
        // Add animation
        resultsContent.classList.add('animate-fadeIn');
        setTimeout(() => {
            resultsContent.classList.remove('animate-fadeIn');
        }, 500);

        // Display Gemini's explanation if available
        if (data.gemini_overall_explanation) {
            explanationText.textContent = data.gemini_overall_explanation;
            document.getElementById('gemini-explanation').style.display = 'flex';
            
            // Add typing animation
            const explanation = data.gemini_overall_explanation;
            explanationText.textContent = '';
            let i = 0;
            
            function typeWriter() {
                if (i < explanation.length) {
                    explanationText.textContent += explanation.charAt(i);
                    i++;
                    setTimeout(typeWriter, 15);
                }
            }
            
            typeWriter();
        } else {
            document.getElementById('gemini-explanation').style.display = 'none';
        }

        // Clear previous results
        resultsTbody.innerHTML = '';

        // Add new results
        data.recommendations.forEach((assessment, index) => {
            const row = document.createElement('tr');
            
            // Format remote_testing and adaptive_irt as Yes/No
            // Replace 'None' with 'No' for better readability
            const remoteTestingValue = assessment.remote_testing === 'Yes' ? 
                '<span class="success">Yes</span>' : 
                (assessment.remote_testing === 'None' ? 
                    '<span class="danger">No</span>' : 
                    '<span class="danger">No</span>');
            
            const adaptiveIrtValue = assessment.adaptive_irt === 'Yes' ? 
                '<span class="success">Yes</span>' : 
                (assessment.adaptive_irt === 'None' ? 
                    '<span class="danger">No</span>' : 
                    '<span class="danger">No</span>');

            // Prepare the gemini summary, defaulting if not available or 'None'
            const geminiSummary = 
                !assessment.gemini_summary || assessment.gemini_summary === 'None' ? 
                'This assessment may be relevant to your search criteria.' : 
                assessment.gemini_summary;
                
            // Format duration with proper fallback
            const duration = 
                !assessment.duration || assessment.duration === 'None' || assessment.duration === 'N/A' ? 
                'Varies' : 
                `${assessment.duration} min`;
                
            // Format test type with proper fallback
            const testType = 
                !assessment.test_type || assessment.test_type === 'None' || assessment.test_type === 'N/A' ? 
                'Standard' : 
                assessment.test_type;

            row.innerHTML = `
                <td>${assessment.name}</td>
                <td>${geminiSummary}</td>
                <td>${testType}</td>
                <td>${duration}</td>
                <td>${remoteTestingValue}</td>
                <td>${adaptiveIrtValue}</td>
                <td><a href="${assessment.url}" target="_blank">View Details</a></td>
            `;
            
            // Set initial style for animation
            row.style.opacity = '0';
            row.style.transform = 'translateY(10px)';
            
            resultsTbody.appendChild(row);
            
            // Animate the row to visible after a short delay
            setTimeout(() => {
                row.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                row.style.opacity = '1';
                row.style.transform = 'translateY(0)';
            }, 50 * index); // Stagger the animations
        });
    };
    
    // Initialize hover effect for buttons
    const buttons = document.querySelectorAll('.btn-primary, .btn-secondary');
    buttons.forEach(btn => {
        btn.addEventListener('mouseover', () => {
            btn.style.transform = 'translateY(-2px)';
        });
        
        btn.addEventListener('mouseout', () => {
            btn.style.transform = '';
        });
    });
}); 