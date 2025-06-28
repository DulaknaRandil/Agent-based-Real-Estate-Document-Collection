// Property Document Collection System - Document Viewer & Screenshot Handler

/**
 * Screenshot and Error Document Handling Script
 * This script handles displaying screenshots and error images in the document viewer
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize screenshot viewer and error handling
    initScreenshotHandling();
});

/**
 * Initialize screenshot handling functionality
 */
function initScreenshotHandling() {
    console.log("Initializing screenshot handling module...");
    
    // Track error screenshots
    window.errorScreenshots = [];
    
    // Hook into document handling
    monitorDocumentErrors();
}

/**
 * Monitor for document download errors and handle them appropriately
 */
function monitorDocumentErrors() {
    // Override the document download error handler
    window.handleDocumentDownloadError = function(document, error) {
        console.log("Handling document download error:", document, error);
        
        // Check if document is a download error screenshot
        if (document.filename && document.filename.includes('download_error')) {
            handleErrorScreenshot(document);
            return true; // Handled
        }
        
        // For normal documents that failed to download
        const screenshotUrl = generateErrorScreenshotUrl(document);
        
        // Add to error screenshots list
        window.errorScreenshots.push({
            original: document,
            screenshotUrl: screenshotUrl,
            error: error,
            timestamp: new Date().toISOString()
        });
        
        // Update UI to show the error
        updateErrorScreenshotUI();
        
        return true; // Handled
    };
}

/**
 * Handle display of error screenshots
 */
function handleErrorScreenshot(document) {
    console.log("Processing error screenshot:", document);
    
    // Create special document item for the error screenshot
    const listItem = document.createElement('li');
    listItem.className = 'list-group-item document-item deed-card error-screenshot';
    listItem.dataset.filename = document.filename;
    listItem.dataset.url = document.url;
    
    // Extract book and page from filename if present (pattern: download_error_DB XXXX YYY)
    let book = null;
    let page = null;
    
    const match = document.filename.match(/download_error_DB\s+(\d+)\s+(\d+)/);
    if (match) {
        book = match[1];
        page = match[2];
    }
    
    listItem.innerHTML = `
        <div class="d-flex align-items-center">
            <div class="document-icon me-3">
                <i class="bi bi-exclamation-triangle-fill text-warning fs-3"></i>
            </div>
            <div class="flex-grow-1">
                <div class="d-flex justify-content-between align-items-center">
                    <strong>Download Error Screenshot</strong>
                    <span class="badge bg-warning text-dark">ERROR</span>
                </div>
                <div class="text-truncate small" title="${document.filename}">
                    ${document.filename}
                </div>
                ${book && page ? `
                <div class="mt-1">
                    <span class="badge badge-book me-2">Book ${book}</span>
                    <span class="badge badge-page">Page ${page}</span>
                </div>
                ` : ''}
                <small class="text-muted">Error screenshot captured at ${new Date().toLocaleString()}</small>
            </div>
            <div class="document-actions ms-2">
                <button class="btn btn-sm btn-outline-primary me-1 view-screenshot-btn" title="View Screenshot">
                    <i class="bi bi-eye"></i>
                </button>
                <a href="${document.url}" download="${document.filename}" class="btn btn-sm btn-outline-secondary" title="Download Screenshot">
                    <i class="bi bi-download"></i>
                </a>
            </div>
        </div>
    `;
    
    // Add event listener for view button
    const viewBtn = listItem.querySelector('.view-screenshot-btn');
    viewBtn.addEventListener('click', () => {
        viewErrorScreenshot(document);
    });
    
    // Add to the screenshots section or create if doesn't exist
    let screenshotsSection = document.getElementById('screenshotsSection');
    if (!screenshotsSection) {
        // Create screenshots section if it doesn't exist
        screenshotsSection = document.createElement('div');
        screenshotsSection.id = 'screenshotsSection';
        screenshotsSection.className = 'mt-4';
        screenshotsSection.innerHTML = `
            <h6>Error Screenshots:</h6>
            <div class="alert alert-warning p-2 mb-3">
                <small>These screenshots show errors that occurred during document collection.</small>
            </div>
            <ul class="list-group" id="screenshotsList"></ul>
        `;
        
        // Add after documents section
        const documentsSection = document.getElementById('documentsSection');
        if (documentsSection) {
            documentsSection.parentNode.insertBefore(screenshotsSection, documentsSection.nextSibling);
        }
    }
    
    // Find or create screenshots list
    let screenshotsList = document.getElementById('screenshotsList');
    if (!screenshotsList) {
        screenshotsList = document.createElement('ul');
        screenshotsList.id = 'screenshotsList';
        screenshotsList.className = 'list-group';
        screenshotsSection.appendChild(screenshotsList);
    }
    
    // Append the screenshot item
    screenshotsList.appendChild(listItem);
    screenshotsSection.classList.remove('d-none');
}

/**
 * View error screenshot in modal
 */
function viewErrorScreenshot(document) {
    console.log("Viewing error screenshot:", document);
    
    // Extract book and page from filename if present
    let book = null;
    let page = null;
    const match = document.filename.match(/download_error_DB\s+(\d+)\s+(\d+)/);
    if (match) {
        book = match[1];
        page = match[2];
    }
    
    // Set document details
    const docDetailType = document.getElementById('docDetailType');
    const docDetailFilename = document.getElementById('docDetailFilename');
    const docDetailTMS = document.getElementById('docDetailTMS');
    const docDetailCounty = document.getElementById('docDetailCounty');
    const deedDetailsSection = document.getElementById('deedDetailsSection');
    const downloadDocumentBtn = document.getElementById('downloadDocumentBtn');
    
    if (docDetailType) docDetailType.textContent = "Error Screenshot";
    if (docDetailFilename) docDetailFilename.textContent = document.filename;
    if (docDetailTMS) docDetailTMS.textContent = window.currentTMS || "";
    if (docDetailCounty) docDetailCounty.textContent = (window.currentCounty || "").charAt(0).toUpperCase() + (window.currentCounty || "").slice(1) + ' County';
    
    // Show or hide deed details section
    if (book && page && deedDetailsSection) {
        deedDetailsSection.classList.remove('d-none');
        document.getElementById('docDetailBook').textContent = book;
        document.getElementById('docDetailPage').textContent = page;
        document.getElementById('docDetailDate').textContent = 'Unknown';
    } else if (deedDetailsSection) {
        deedDetailsSection.classList.add('d-none');
    }
    
    // Set download button
    if (downloadDocumentBtn) {
        downloadDocumentBtn.href = document.url;
        downloadDocumentBtn.setAttribute('download', document.filename);
    }
    
    // Set document title in modal
    const modalTitle = document.getElementById('documentModalTitle');
    if (modalTitle) modalTitle.textContent = `Error Screenshot: ${document.filename}`;
    
    // Load image in viewer
    const modalPdfViewer = document.getElementById('modalPdfViewer');
    const pdfViewer = document.getElementById('pdfViewer');
    
    if (modalPdfViewer) modalPdfViewer.src = document.url;
    if (pdfViewer) {
        pdfViewer.src = document.url;
        pdfViewer.classList.remove('d-none');
        document.getElementById('noDocumentSelected').classList.add('d-none');
    }
    
    // Show modal
    const documentModal = new bootstrap.Modal(document.getElementById('documentModal'));
    documentModal.show();
}

/**
 * Generate a URL for an error screenshot
 */
function generateErrorScreenshotUrl(document) {
    // This would normally call the backend API to get a screenshot URL
    // For now we'll just return a placeholder
    const baseUrl = window.API_BASE_URL || 'http://localhost:8000';
    const county = window.currentCounty || 'unknown';
    const tms = window.currentTMS || 'unknown';
    
    // For book/page documents
    let screenshotName = 'download_error';
    if (document.metadata && document.metadata.book && document.metadata.page) {
        screenshotName = `download_error_DB ${document.metadata.book} ${document.metadata.page}`;
    } else if (document.type) {
        screenshotName = `download_error_${document.type}`;
    }
    
    return `${baseUrl}/api/screenshots/${county}/${tms}/${screenshotName}.png`;
}

/**
 * Update the UI to show error screenshots
 */
function updateErrorScreenshotUI() {
    // Check if we have error screenshots to display
    if (!window.errorScreenshots || window.errorScreenshots.length === 0) {
        return;
    }
    
    // Create or update error notification
    let errorNotification = document.getElementById('errorNotification');
    if (!errorNotification) {
        errorNotification = document.createElement('div');
        errorNotification.id = 'errorNotification';
        errorNotification.className = 'alert alert-warning mt-3';
        errorNotification.innerHTML = `
            <strong><i class="bi bi-exclamation-triangle-fill me-2"></i>Document Download Issues</strong>
            <p class="mb-0 mt-2">Some documents failed to download. <a href="#screenshotsSection" class="alert-link">View error screenshots</a> for details.</p>
        `;
        
        // Add to status updates
        const statusUpdates = document.getElementById('statusUpdates');
        if (statusUpdates) {
            statusUpdates.appendChild(errorNotification);
        }
    } else {
        // Update count
        errorNotification.innerHTML = `
            <strong><i class="bi bi-exclamation-triangle-fill me-2"></i>Document Download Issues (${window.errorScreenshots.length})</strong>
            <p class="mb-0 mt-2">Some documents failed to download. <a href="#screenshotsSection" class="alert-link">View error screenshots</a> for details.</p>
        `;
    }
}
