// Property Document Collection System - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Main elements
    const searchForm = document.getElementById('searchForm');
    const resultCard = document.getElementById('resultCard');
    const progressBar = document.getElementById('progressBar');
    const statusMessage = document.getElementById('statusMessage');
    const displayTMS = document.getElementById('displayTMS');
    const displayCounty = document.getElementById('displayCounty');
    const documentsSection = document.getElementById('documentsSection');
    const documentsList = document.getElementById('documentsList');
    
    // Document viewer elements
    const pdfViewer = document.getElementById('pdfViewer');
    const modalPdfViewer = document.getElementById('modalPdfViewer');
    const deedReferencesList = document.getElementById('deedReferencesList');
    
    // Document details
    const docDetailType = document.getElementById('docDetailType');
    const docDetailFilename = document.getElementById('docDetailFilename');
    const docDetailTMS = document.getElementById('docDetailTMS');
    const docDetailCounty = document.getElementById('docDetailCounty');
    const docDetailBook = document.getElementById('docDetailBook');
    const docDetailPage = document.getElementById('docDetailPage');
    const docDetailDate = document.getElementById('docDetailDate');
    const deedDetailsSection = document.getElementById('deedDetailsSection');
    const downloadDocumentBtn = document.getElementById('downloadDocumentBtn');
    
    // API base URL - replace with your actual backend URL when deploying
    const API_BASE_URL = 'http://localhost:8000';
    
    // Add debugging info to the console
    console.log('Frontend initialized with API endpoint:', API_BASE_URL);
    
    // API Status element in navbar
    const apiStatusEl = document.getElementById('apiStatus');
    
    // Check if the backend is available
    fetch(`${API_BASE_URL}/health`, {
        headers: { 'Accept': 'application/json' },
        method: 'GET', 
        mode: 'cors'
    })
        .then(response => {
            if (response.ok) return response.json();
            throw new Error(`Server returned ${response.status}`);
        })
        .then(data => {
            console.log('Backend health check successful:', data);
            
            // Update API status in navbar
            apiStatusEl.textContent = 'Connected';
            apiStatusEl.parentElement.classList.remove('bg-light', 'text-dark');
            apiStatusEl.parentElement.classList.add('bg-success', 'text-white');
            
            // Show success message
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-success mt-3 fade show';
            alertDiv.role = 'alert';
            alertDiv.innerHTML = '✅ Backend connection successful! The system is ready to use.';
            document.querySelector('.container').prepend(alertDiv);
            
            // Auto-hide the alert after 5 seconds
            setTimeout(() => {
                alertDiv.classList.remove('show');
                setTimeout(() => alertDiv.remove(), 500);
            }, 5000);
        })
        .catch(error => {
            console.error('Error connecting to backend:', error);
            
            // Update API status in navbar
            apiStatusEl.textContent = 'Disconnected';
            apiStatusEl.parentElement.classList.remove('bg-light', 'text-dark');
            apiStatusEl.parentElement.classList.add('bg-danger', 'text-white');
            
            // Show persistent error message that doesn't auto-hide
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger mt-3';
            alertDiv.role = 'alert';
            alertDiv.innerHTML = `
                <h4 class="alert-heading">⚠️ Connection Problem</h4>
                <p>Cannot connect to the backend server. Please check:</p>
                <ul>
                    <li>Make sure the server is running: <code>python run_server.py</code></li>
                    <li>Verify the server is accessible at: <code>http://localhost:8000</code></li>
                    <li>Check that CORS is properly configured on the backend</li>
                </ul>
                <hr>
                <p>Error details: ${error.message}</p>
            `;
            document.querySelector('.container').prepend(alertDiv);
        });
    
    // Mock workflow steps for each county
    const countyWorkflows = {
        charleston: [
            { step: 1, description: "Navigating to Charleston County online services", completed: false },
            { step: 2, description: "Accessing real property record search", completed: false },
            { step: 3, description: "Entering TMS number and searching", completed: false },
            { step: 4, description: "Accessing property details page", completed: false },
            { step: 5, description: "Saving property card as PDF", completed: false },
            { step: 6, description: "Collecting book and page references", completed: false },
            { step: 7, description: "Accessing tax information", completed: false },
            { step: 8, description: "Saving tax information as PDF", completed: false },
            { step: 9, description: "Navigating to Register of Deeds page", completed: false },
            { step: 10, description: "Searching for deed records by book/page", completed: false },
            { step: 11, description: "Downloading deed documents", completed: false }
        ],
        berkeley: [
            { step: 1, description: "Navigating to Berkeley County Property Search", completed: false },
            { step: 2, description: "Entering TMS number and searching", completed: false },
            { step: 3, description: "Accessing property card page", completed: false },
            { step: 4, description: "Saving property card as PDF", completed: false },
            { step: 5, description: "Collecting book and page references", completed: false },
            { step: 6, description: "Accessing Berkeley County Assessor website", completed: false },
            { step: 7, description: "Searching for tax information", completed: false },
            { step: 8, description: "Saving tax bill as PDF", completed: false },
            { step: 9, description: "Saving tax receipt as PDF (if available)", completed: false },
            { step: 10, description: "Navigating to Berkeley County register of deeds website", completed: false },
            { step: 11, description: "Searching for deed records by book/page", completed: false },
            { step: 12, description: "Downloading deed documents", completed: false }
        ]
    };

    // Handle form submission
    searchForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const county = document.getElementById('countySelect').value;
        const tmsNumber = document.getElementById('tmsNumber').value.trim();
        const collectAll = document.getElementById('collectAll').checked;
        
        console.log('Form values:', { county, tmsNumber, collectAll });
        
        // Better validation
        if (!county) {
            alert('Please select a county from the dropdown.');
            return;
        }
        
        if (!tmsNumber) {
            alert('Please enter a valid TMS number.');
            return;
        }
        
        // Basic TMS format validation (numeric only for Charleston and Berkeley)
        if (!/^\d+$/.test(tmsNumber)) {
            if (!confirm('TMS number appears to contain non-numeric characters. Continue anyway?')) {
                return;
            }
        }
        
        console.log('Form validation passed, starting workflow...');
        
        // Reset state
        collectedDocuments = [];
        deedReferences = [];
        currentCounty = county;
        currentTMS = tmsNumber;
        
        // Display results card and start workflow
        displayTMS.textContent = tmsNumber;
        displayCounty.textContent = county === 'charleston' ? 'Charleston County, SC' : 'Berkeley County, SC';
        resultCard.classList.remove('d-none');
        
        // Reset UI elements
        documentsList.innerHTML = '';
        deedReferencesList.innerHTML = '';
        pdfViewer.classList.add('d-none');
        document.getElementById('noDocumentSelected').classList.remove('d-none');
        documentsSection.classList.add('d-none');
        
        // Reset progress and status
        updateProgress(0, 'Initializing document collection process...');
        
        // Show task modal with workflow steps
        showWorkflowTasks(county);
        
        // Start the workflow
        startWorkflow(county, tmsNumber, collectAll);
    });

    // Function to show workflow tasks in modal
    function showWorkflowTasks(county) {
        const tasksContainer = document.getElementById('tasksContainer');
        tasksContainer.innerHTML = '';
        
        const workflow = countyWorkflows[county];
        
        workflow.forEach(task => {
            const taskElement = document.createElement('div');
            taskElement.classList.add('task-item');
            taskElement.id = `task-${task.step}`;
            
            taskElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>Step ${task.step}:</strong> ${task.description}
                    </div>
                    <span class="badge bg-secondary">Pending</span>
                </div>
            `;
            
            tasksContainer.appendChild(taskElement);
        });
        
        // Show the modal
        const taskModal = new bootstrap.Modal(document.getElementById('taskModal'));
        taskModal.show();
    }

    // Function to update a specific task's status
    function updateTaskStatus(step, status, county) {
        const taskElement = document.getElementById(`task-${step}`);
        if (!taskElement) return;
        
        const badge = taskElement.querySelector('.badge');
        
        taskElement.classList.remove('completed', 'in-progress', 'error');
        badge.classList.remove('bg-secondary', 'bg-success', 'bg-warning', 'bg-danger');
        
        switch(status) {
            case 'in-progress':
                taskElement.classList.add('in-progress');
                badge.classList.add('bg-warning');
                badge.textContent = 'In Progress';
                break;
            case 'completed':
                taskElement.classList.add('completed');
                badge.classList.add('bg-success');
                badge.textContent = 'Completed';
                break;
            case 'error':
                taskElement.classList.add('error');
                badge.classList.add('bg-danger');
                badge.textContent = 'Error';
                break;
            default:
                badge.classList.add('bg-secondary');
                badge.textContent = 'Pending';
                break;
        }
    }

    // Global variables for statistics
    let workflowStartTime = null;
    let completedSteps = 0;
    let totalSteps = 0;
    let collectedFiles = 0;
    
    // Function to update progress bar and status
    function updateProgress(percent, message) {
        // Handle negative percent (error state)
        const displayPercent = percent < 0 ? 0 : percent;
        
        // Smoothly animate the progress bar
        progressBar.style.transition = 'width 0.5s ease-in-out';
        progressBar.style.width = `${displayPercent}%`;
        progressBar.textContent = `${Math.round(displayPercent)}%`;
        statusMessage.textContent = message;
        
        // Change progress bar color based on completion
        progressBar.classList.remove('bg-primary', 'bg-success', 'bg-danger', 'bg-warning');
        
        if (percent === 100) {
            progressBar.classList.add('bg-success');
            // Change result card header to success
            document.querySelector('#resultCard .card-header').className = 'card-header bg-success text-white';
        } else if (percent < 0) {
            progressBar.classList.add('bg-danger');
            progressBar.style.width = '100%'; // Show full red bar for error
            // Change result card header to danger
            document.querySelector('#resultCard .card-header').className = 'card-header bg-danger text-white';
        } else if (percent >= 80) {
            progressBar.classList.add('bg-success'); // Use success color when getting close
            // Change result card header to primary (orange)
            document.querySelector('#resultCard .card-header').className = 'card-header bg-primary text-white';
        } else {
            progressBar.classList.add('bg-primary');
            // Change result card header to primary (orange)
            document.querySelector('#resultCard .card-header').className = 'card-header bg-primary text-white';
        }
        
        // Log status update for debugging
        console.log(`Progress update: ${percent}% - ${message}`);
        
        // Update statistics display if we have a workflow running
        if (workflowStartTime) {
            updateStats();
        }
    }

    // Function to start the workflow
    async function startWorkflow(county, tmsNumber, collectAll) {
        try {
            // Initialize statistics tracking
            workflowStartTime = Date.now();
            collectedFiles = 0;
            completedSteps = 0;
            totalSteps = countyWorkflows[county] ? countyWorkflows[county].length : 0;
            
            // Reset the document list
            documentsList.innerHTML = '';
            documentsSection.classList.add('d-none');
            
            // Update stats display initially
            document.getElementById('statsFiles').textContent = '0';
            document.getElementById('statsTime').textContent = '0s';
            document.getElementById('statsSteps').textContent = `0/${totalSteps}`;
            document.getElementById('statsSection').classList.remove('d-none');
            
            // Update UI to show we're connecting
            updateProgress(5, "Connecting to server...");
            
            const requestBody = {
                county: county,
                tms: tmsNumber,
                include_property_card: true,
                include_tax_info: true,
                include_deeds: collectAll
            };
            
            // Debug output
            console.log('Sending workflow request to:', `${API_BASE_URL}/start-workflow`);
            console.log('Request payload:', requestBody);
            
            // Make API request to start workflow
            const response = await fetch(`${API_BASE_URL}/start-workflow`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(requestBody),
                mode: 'cors' // Explicitly set CORS mode
            });
            
            console.log('Response status:', response.status);
            console.log('Response headers:', [...response.headers.entries()]);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Error response body:', errorText);
                throw new Error(`Server error: ${response.status} - ${errorText || 'Unknown error'}`);
            }
            
            const data = await response.json();
            console.log('API response data:', data);
            
            if (!data || !data.task_id) {
                throw new Error('Invalid response: Missing task_id in server response');
            }
            
            // Start polling for status
            updateProgress(10, `Workflow started. Task ID: ${data.task_id}`);
            const taskId = data.task_id;
            pollWorkflowStatus(taskId, county);
            
        } catch (error) {
            console.error('Error starting workflow:', error);
            updateProgress(-1, `Error starting workflow: ${error.message || 'Unknown error'}`);
            statusMessage.classList.remove('alert-info');
            statusMessage.classList.add('alert-danger');
            
            // Show detailed error alert
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger mt-3';
            alertDiv.innerHTML = `
                <h4 class="alert-heading">Workflow Start Failed</h4>
                <p>Failed to start document collection workflow:</p>
                <pre class="bg-light p-2">${error.message}</pre>
                <hr>
                <p>Please try again or contact support if the issue persists.</p>
            `;
            document.getElementById('resultCard').querySelector('.card-body').appendChild(alertDiv);
        }
    }

    // Function to poll for workflow status
    function pollWorkflowStatus(taskId, county) {
        // Make sure taskId is valid
        if (!taskId) {
            console.error('Cannot poll workflow status: Invalid task ID');
            updateProgress(-1, "Error: Invalid task ID");
            return;
        }
        
        // Poll the API for status updates
        console.log(`Starting to poll workflow status for task ${taskId} in ${county} county`);
        const workflow = countyWorkflows[county];
        const maxAttempts = 300; // 5 minutes (300 * 1 second)
        let attempts = 0;
        let consecutiveErrors = 0;
        
        // Add a status update for better user feedback
        updateProgress(10, `Connected to workflow. Task ID: ${taskId}. Beginning document collection...`);
        
        // Use workflow steps to map progress
        const statusInterval = setInterval(async () => {
            try {
                attempts++;
                
                // Check if we've reached max attempts
                if (attempts > maxAttempts) {
                    clearInterval(statusInterval);
                    updateProgress(-1, "Workflow timed out after 5 minutes");
                    return;
                }
                
                const statusUrl = `${API_BASE_URL}/workflow-status/${taskId}`;
                
                // Fetch status from API
                console.log(`Polling attempt ${attempts}: ${statusUrl}`);
                const response = await fetch(statusUrl, {
                    headers: { 'Accept': 'application/json' },
                    method: 'GET',
                    mode: 'cors',
                    cache: 'no-cache' // Prevent caching of status responses
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error(`API error status: ${response.status}`, errorText);
                    consecutiveErrors++;
                    
                    if (consecutiveErrors > 5) {
                        throw new Error(`API responded with status ${response.status} after multiple retries: ${errorText}`);
                    }
                    
                    // Add warning but continue polling
                    console.warn(`API error (attempt ${consecutiveErrors}/5) - will retry in 3 seconds`);
                    return; // Skip this iteration but continue polling
                }
                
                // Reset consecutive errors counter on success
                consecutiveErrors = 0;
                
                // Try to parse the JSON response
                let statusData;
                try {
                    statusData = await response.json();
                    console.log("Received status data:", statusData);
                } catch (jsonError) {
                    console.error("Failed to parse JSON response:", jsonError);
                    throw new Error("Invalid JSON response from server");
                }
                
                // Update progress bar and status message
                updateProgress(statusData.progress, statusData.message);
                
                // Map progress to workflow steps
                const currentStep = Math.ceil((statusData.progress / 100) * workflow.length);
                
                // Update task statuses and count completed steps
                completedSteps = 0;
                for (let i = 1; i <= workflow.length; i++) {
                    if (i < currentStep) {
                        updateTaskStatus(i, 'completed', county);
                        completedSteps++;
                    } else if (i === currentStep) {
                        updateTaskStatus(i, 'in-progress', county);
                    }
                }
                
                // Update stats with current progress
                updateStats();
                
                // Add documents to list if they're available
                if (statusData.documents && statusData.documents.length > 0) {
                    statusData.documents.forEach(doc => {
                        // Extract metadata for deed documents if available
                        let metadata = null;
                        if (doc.type === 'deed' && doc.metadata) {
                            metadata = {
                                book: doc.metadata.book,
                                page: doc.metadata.page,
                                date: doc.metadata.date
                            };
                        }
                        addDocumentToList(doc.type, county, doc.filename, doc.url, metadata);
                    });
                }
                
                // Handle error screenshots if present
                if (statusData.error_screenshots && statusData.error_screenshots.length > 0) {
                    statusData.error_screenshots.forEach(screenshot => {
                        addDocumentToList('screenshot', county, screenshot.filename, screenshot.url, screenshot.metadata);
                    });
                }
                
                // Process deed references if they're included
                if (statusData.deed_references && statusData.deed_references.length > 0) {
                    statusData.deed_references.forEach(ref => {
                        // Add to deed references if not already present
                        if (!deedReferences.some(existing => existing.book === ref.book && existing.page === ref.page)) {
                            deedReferences.push(ref);
                        }
                    });
                    
                    // Update the deed references display
                    displayDeedReferences(deedReferences);
                }
                
                // Check if workflow is complete
                if (statusData.status === 'completed') {
                    clearInterval(statusInterval);
                    updateProgress(100, 'Document collection completed successfully!');
                    statusMessage.classList.remove('alert-info');
                    statusMessage.classList.add('alert-success');
                } else if (statusData.status === 'failed') {
                    clearInterval(statusInterval);
                    updateProgress(-1, statusData.message || 'Workflow failed');
                    statusMessage.classList.remove('alert-info');
                    statusMessage.classList.add('alert-danger');
                }
                
            } catch (error) {
                console.error('Error polling workflow status:', error);
                clearInterval(statusInterval);
                updateProgress(-1, `Error checking status: ${error.message || 'Unknown error'}`);
            }
        }, 3000);
    }

    // Function to update statistics display
    function updateStats() {
        // Make sure the stats section is visible
        const statsSection = document.getElementById('statsSection');
        statsSection.classList.remove('d-none');
        
        // Update files count
        document.getElementById('statsFiles').textContent = collectedFiles;
        
        // Update time elapsed
        const elapsedMs = Date.now() - workflowStartTime;
        const elapsedSec = Math.floor(elapsedMs / 1000);
        let timeDisplay = '';
        
        if (elapsedSec < 60) {
            timeDisplay = `${elapsedSec}s`;
        } else if (elapsedSec < 3600) {
            const min = Math.floor(elapsedSec / 60);
            const sec = elapsedSec % 60;
            timeDisplay = `${min}m ${sec}s`;
        } else {
            const hr = Math.floor(elapsedSec / 3600);
            const min = Math.floor((elapsedSec % 3600) / 60);
            timeDisplay = `${hr}h ${min}m`;
        }
        
        document.getElementById('statsTime').textContent = timeDisplay;
        
        // Update steps completed
        document.getElementById('statsSteps').textContent = `${completedSteps}/${totalSteps}`;
    }
    
    // Function to add document to the list
    function addDocumentToList(docType, county, filename, url, metadata = null) {
        // Check if this document already exists in the list
        const existingItems = Array.from(documentsList.children);
        if (existingItems.some(item => item.dataset.filename === filename)) {
            return; // Skip if document already in list
        }
        
        // Handle error screenshots differently
        if (filename.includes('download_error')) {
            // If we have the screenshot handler, use it
            if (window.handleDocumentDownloadError) {
                window.handleDocumentDownloadError({
                    type: 'screenshot',
                    filename: filename,
                    url: `${API_BASE_URL}${url}`
                });
                return;
            }
        }
        
        // Increment collected files count
        collectedFiles++;
        
        // Make sure document section is visible
        documentsSection.classList.remove('d-none');
        
        // Format the document type for display
        let displayDocType = docType;
        let iconClass = 'bi-file-earmark';
        
        switch(docType) {
            case 'property_card':
                displayDocType = 'Property Card';
                iconClass = 'bi-house-fill';
                break;
            case 'tax_info':
                displayDocType = 'Tax Info';
                iconClass = 'bi-cash';
                break;
            case 'deed':
                displayDocType = 'Deed';
                iconClass = 'bi-file-earmark-text';
                break;
        }
        
        // Check file extension to determine icon & type
        const fileExt = filename.split('.').pop().toLowerCase();
        let badgeClass = 'bg-secondary';
        
        if (fileExt === 'pdf') {
            iconClass = 'bi-file-earmark-pdf';
            badgeClass = 'bg-danger';
        } else if (['jpg', 'jpeg', 'png', 'gif'].includes(fileExt)) {
            iconClass = 'bi-file-earmark-image';
            badgeClass = 'bg-info';
        }
        
        // Add to our collected documents array for the viewer
        const documentObject = {
            type: docType,
            filename: filename,
            url: `${API_BASE_URL}${url}`,
            metadata: metadata
        };
        collectedDocuments.push(documentObject);
        
        // If this is a deed document with book/page info, add it to deed references
        if (docType === 'deed' && metadata && metadata.book && metadata.page) {
            const deedRef = {
                book: metadata.book,
                page: metadata.page,
                date: metadata.date || 'Unknown',
                filename: filename,
                url: `${API_BASE_URL}${url}`
            };
            
            // Add to deed references if not already present
            if (!deedReferences.some(ref => ref.book === deedRef.book && ref.page === deedRef.page)) {
                deedReferences.push(deedRef);
                displayDeedReferences(deedReferences);
            }
        }
        
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item document-item deed-card';
        listItem.dataset.filename = filename;
        listItem.dataset.url = url;
        listItem.dataset.docIndex = collectedDocuments.length - 1; // Store the index for easy reference
        
        let metadataDisplay = '';
        if (docType === 'deed' && metadata && metadata.book && metadata.page) {
            metadataDisplay = `
                <div class="mt-1">
                    <span class="badge badge-book me-2">Book ${metadata.book}</span>
                    <span class="badge badge-page">Page ${metadata.page}</span>
                    ${metadata.date ? `<small class="text-muted ms-2">Filed: ${metadata.date}</small>` : ''}
                </div>
            `;
        }
        
        listItem.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="document-icon me-3">
                    <i class="bi ${iconClass} fs-3"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-center">
                        <strong>${displayDocType}</strong>
                        <span class="badge ${badgeClass}">${fileExt.toUpperCase()}</span>
                    </div>
                    <div class="text-truncate small" title="${filename}">
                        ${filename}
                    </div>
                    ${metadataDisplay}
                    <small class="text-muted">Collected on ${new Date().toLocaleString()}</small>
                </div>
                <div class="document-actions ms-2">
                    <button class="btn btn-sm btn-outline-primary me-1 view-doc-btn" title="View Document">
                        <i class="bi bi-eye"></i>
                    </button>
                    <a href="${API_BASE_URL}${url}" download="${filename}" class="btn btn-sm btn-outline-secondary" title="Download Document">
                        <i class="bi bi-download"></i>
                    </a>
                </div>
            </div>
        `;
        
        console.log('Added document to list:', { type: displayDocType, filename: filename, url: `${API_BASE_URL}${url}`, metadata: metadata });
        
        // Add event listener for view button
        const viewBtn = listItem.querySelector('.view-doc-btn');
        viewBtn.addEventListener('click', () => {
            viewDocument(documentObject);
        });
        
        // Append to the list with a subtle animation
        listItem.style.opacity = '0';
        documentsList.appendChild(listItem);
        
        // Fade it in 
        setTimeout(() => {
            listItem.style.transition = 'opacity 0.5s ease-in';
            listItem.style.opacity = '1';
        }, 10);
        
        // Update statistics
        updateStats();
    }
    
    // Current task ID and collected documents
    let currentTaskId = null;
    let collectedDocuments = [];
    let deedReferences = [];
    let currentCounty = '';
    let currentTMS = '';
    
    // Function to display deed references in table
    function displayDeedReferences(references) {
        deedReferencesList.innerHTML = '';
        
        if (references.length === 0) {
            deedReferencesList.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center text-muted">
                        <i class="bi bi-info-circle me-2"></i>No deed references found yet.
                    </td>
                </tr>
            `;
            return;
        }
        
        references.forEach(ref => {
            const tr = document.createElement('tr');
            
            // Format book with padding for consistent display
            const bookDisplay = ref.book.includes('-') ? ref.book : ref.book.padStart(4, '0');
            
            // Format page with padding
            const pageDisplay = ref.page.padStart(3, '0');
            
            tr.innerHTML = `
                <td><span class="badge badge-book">${bookDisplay}</span></td>
                <td><span class="badge badge-page">${pageDisplay}</span></td>
                <td>${ref.date || 'Unknown'}</td>
                <td>
                    <button class="view-deed-btn" data-book="${ref.book}" data-page="${ref.page}">
                        <i class="bi bi-eye-fill me-1"></i> View
                    </button>
                </td>
            `;
            
            deedReferencesList.appendChild(tr);
        });
        
        // Add event listeners to view buttons
        document.querySelectorAll('.view-deed-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const book = this.getAttribute('data-book');
                const page = this.getAttribute('data-page');
                viewDeedDocument(book, page);
            });
        });
    }
    
    // Function to view deed document
    function viewDeedDocument(book, page) {
        // Find the deed document in collected documents
        const deedDoc = collectedDocuments.find(doc => 
            doc.type === 'deed' && 
            doc.metadata && 
            doc.metadata.book === book && 
            doc.metadata.page === page
        );
        
        if (deedDoc) {
            viewDocument(deedDoc);
        } else {
            // If deed not found in collected documents, try to fetch it
            fetchDeedDocument(book, page);
        }
    }
    
    // Function to fetch deed document
    function fetchDeedDocument(book, page) {
        showStatusMessage('info', `Fetching deed document (Book ${book}, Page ${page})...`);
        
        // API endpoint for fetching deed document
        fetch(`${API_BASE_URL}/api/documents/${currentCounty}/${currentTMS}/deed/${book}/${page}`)
            .then(response => {
                if (response.ok) return response.json();
                throw new Error(`Server returned ${response.status}`);
            })
            .then(data => {
                const deedDoc = {
                    type: 'deed',
                    filename: data.filename,
                    url: data.url,
                    metadata: {
                        book: book,
                        page: page,
                        date: data.date || 'Unknown'
                    }
                };
                
                // Add to collected documents
                collectedDocuments.push(deedDoc);
                
                // Update documents list
                updateDocumentsList();
                
                // View the document
                viewDocument(deedDoc);
                
                showStatusMessage('success', `Deed document (Book ${book}, Page ${page}) fetched successfully.`);
            })
            .catch(error => {
                console.error('Error fetching deed document:', error);
                showStatusMessage('danger', `Failed to fetch deed document (Book ${book}, Page ${page}): ${error.message}`);
            });
    }
    
    // Function to view document in modal
    function viewDocument(document) {
        // Set document details
        docDetailType.textContent = document.type.charAt(0).toUpperCase() + document.type.slice(1);
        docDetailFilename.textContent = document.filename;
        docDetailTMS.textContent = currentTMS;
        docDetailCounty.textContent = currentCounty.charAt(0).toUpperCase() + currentCounty.slice(1) + ' County';
        
        // Set download button
        downloadDocumentBtn.href = document.url;
        downloadDocumentBtn.setAttribute('download', document.filename);
        
        // Show or hide deed details section
        if (document.type === 'deed' && document.metadata) {
            deedDetailsSection.classList.remove('d-none');
            docDetailBook.textContent = document.metadata.book;
            docDetailPage.textContent = document.metadata.page;
            docDetailDate.textContent = document.metadata.date || 'Unknown';
        } else {
            deedDetailsSection.classList.add('d-none');
        }
        
        // Set document title in modal
        const modalTitle = document.getElementById('documentModalTitle');
        modalTitle.textContent = `${document.type.charAt(0).toUpperCase() + document.type.slice(1)}: ${document.filename}`;
        
        // Load document in viewer
        modalPdfViewer.src = document.url;
        pdfViewer.src = document.url;
        pdfViewer.classList.remove('d-none');
        document.getElementById('noDocumentSelected').classList.add('d-none');
        
        // Show modal
        const documentModal = new bootstrap.Modal(document.getElementById('documentModal'));
        documentModal.show();
    }
    
    // Function to update the documents list
    function updateDocumentsList() {
        documentsList.innerHTML = '';
        
        if (collectedDocuments.length === 0) {
            documentsList.innerHTML = `
                <li class="list-group-item text-center text-muted">
                    <i class="bi bi-info-circle me-2"></i>No documents collected yet.
                </li>
            `;
            return;
        }
        
        // Group documents by type
        const docTypes = {
            'property_card': [],
            'tax_info': [],
            'deed': []
        };
        
        collectedDocuments.forEach(doc => {
            if (docTypes.hasOwnProperty(doc.type)) {
                docTypes[doc.type].push(doc);
            }
        });
        
        // Create document groups
        for (const [type, docs] of Object.entries(docTypes)) {
            if (docs.length > 0) {
                const typeDisplay = type.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
                
                const groupHeader = document.createElement('li');
                groupHeader.className = 'list-group-item list-group-item-secondary';
                groupHeader.innerHTML = `<strong>${typeDisplay} (${docs.length})</strong>`;
                documentsList.appendChild(groupHeader);
                
                docs.forEach(doc => {
                    const li = document.createElement('li');
                    li.className = 'list-group-item list-group-item-action deed-card';
                    
                    // Create document display
                    let docDesc = doc.filename;
                    if (type === 'deed' && doc.metadata) {
                        docDesc = `Book ${doc.metadata.book}, Page ${doc.metadata.page}`;
                        if (doc.metadata.date) {
                            docDesc += ` (${doc.metadata.date})`;
                        }
                    }
                    
                    li.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <i class="bi bi-file-earmark-pdf text-danger me-2"></i>
                                ${docDesc}
                            </div>
                            <div>
                                <button class="btn btn-sm btn-primary view-doc-btn">
                                    <i class="bi bi-eye-fill"></i> View
                                </button>
                                <a href="${doc.url}" download="${doc.filename}" class="btn btn-sm btn-outline-secondary">
                                    <i class="bi bi-download"></i> Download
                                </a>
                            </div>
                        </div>
                    `;
                    
                    // Add event listener for view button
                    li.querySelector('.view-doc-btn').addEventListener('click', () => {
                        viewDocument(doc);
                    });
                    
                    documentsList.appendChild(li);
                });
            }
        }
    }
    
    // Function to display deed references tab
    function showDeedReferencesTab() {
        document.getElementById('deeds-tab').click();
    }
    
    // Function to display document viewer tab
    function showDocumentViewerTab() {
        document.getElementById('preview-tab').click();
    }
});
