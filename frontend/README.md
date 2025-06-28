# Property Document Collection System - Frontend

This repository contains the frontend application for an AI-powered Property Document Collection System that automates the retrieval of real estate documents from county websites.

## Overview

The frontend provides a user-friendly interface for:
- Selecting a county (Charleston or Berkeley County, SC)
- Entering a TMS/parcel number
- Choosing which documents to collect (property cards, tax info, deeds)
- Monitoring collection progress in real-time
- Viewing and downloading collected documents

## Project Structure

```
frontend/
├── index.html      # Main application interface
├── styles.css      # Custom styling
├── main.js         # Frontend logic and API communication
├── README.md       # Documentation (this file)
```

## Technologies Used

- **HTML5/CSS3**: Modern, responsive layout
- **JavaScript**: Frontend logic and API communication
- **Bootstrap 5**: UI framework for responsive design
- **Axios**: HTTP client for API requests
- **Bootstrap Icons**: Icon library

## Features

### User Interface
- Clean, modern, responsive Bootstrap-based interface
- Real-time progress tracking with progress bar
- Document listing with download links
- PDF document viewer integration
- Organized deed book/page number display

### Backend Communication
- RESTful API integration
- Real-time status updates
- Error handling and retry mechanisms
- WebSocket support for live updates during document collection

### Document Collection
- Property cards, tax information, and deed records
- Organized by county and TMS number
- Direct download links
- Automatic PDF rendering in browser
- Deed book and page number metadata display

## Setup & Running

### Prerequisites
1. Node.js and npm (for development only)
2. Running backend server (see backend README.md)

### Local Development
1. Start the backend API server:
   ```
   cd ../backend
   python run_server.py
   ```

2. Start a simple HTTP server to serve the frontend:
   ```
   cd frontend
   python -m http.server 5000
   ```

3. Open the frontend in your browser:
   - Main application: [http://localhost:5000/index.html](http://localhost:5000/index.html)

## Troubleshooting

If you encounter issues with the frontend:

1. **Check browser console** (F12) for error messages
2. **Verify backend is running** by visiting [http://localhost:8000/health](http://localhost:8000/health)
3. **Check CORS headers** in the browser Network tab
4. **Browser cache**: Try clearing your browser cache or opening in incognito/private mode

## Document Display Features

### PDF Viewer Integration
The frontend includes a built-in PDF viewer that allows users to:
- Preview collected documents directly in the browser
- Zoom and navigate through multi-page documents
- Download documents for offline use

### Deed Book & Page Number Display
Deed references are displayed in a structured format:
- Organized table showing all deed references found for a property
- Book and page numbers clearly displayed with filing dates when available
- One-click access to view the corresponding deed document
- Filter options to sort by date, book number, or document type

### Document Organization UI
Documents are categorized and displayed in separate sections:
1. **Property Information**
   - Property card (primary document)
   - Property images (when available)
   - Property characteristics summary

2. **Tax Information**
   - Current tax bills
   - Tax payment receipts
   - Historical tax records

3. **Deed Records**
   - Chronological listing of all deed documents
   - Book and page reference display
   - Quick filters for document types
   - Metadata extraction showing grantor/grantee when available

### Interactive Features
- Document comparison view for examining multiple deeds side by side
- Bookmark feature for marking important documents
- Document notes capability for adding user annotations
- Share functionality for sending document links

## Test TMS Numbers

- Charleston County: 5590200072
- Berkeley County: 2590502005

## Demo Video

A demonstration video showing the system in action is available in the project root directory.

## Future Improvements

- Add user authentication and document history
- Implement a dashboard for saved properties
- Add batch processing capabilities
- Improve error handling and recovery
- Add more counties and document types
