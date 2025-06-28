"""
Main API endpoints for the real estate document collection system
"""
import os
import json
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Import workflow managers
from src.workflows.charleston_workflow import CharlestonWorkflow
from src.workflows.berkeley_workflow import BerkeleyWorkflow

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Real Estate Document Collection API",
    description="API for collecting property documents from Charleston and Berkeley Counties",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000","http://127.0.0.1:5500"],  # Explicitly specify localhost origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Origin", "Accept"],
    expose_headers=["Content-Disposition"]
)

# Data models for requests
class DocumentRequest(BaseModel):
    county: str
    tms: str
    include_property_card: bool = True
    include_tax_info: bool = True
    include_deeds: bool = True

class WorkflowStatus(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    documents: Optional[List[Dict[str, str]]] = None

# Store for active workflows
active_workflows = {}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {"message": "Real Estate Document Collection API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running"""
    return {"status": "healthy", "message": "API is running"}

@app.post("/start-workflow", response_model=dict)
async def start_workflow(request: DocumentRequest, background_tasks: BackgroundTasks):
    """Start a document collection workflow for a specific county and TMS number"""
    try:
        # Generate a unique task ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # Initialize workflow status
        active_workflows[task_id] = {
            "status": "initializing",
            "progress": 0,
            "message": "Initializing workflow",
            "county": request.county,
            "tms": request.tms,
            "documents": []
        }
        
        # Start workflow in background based on county
        if request.county.lower() == "charleston":
            background_tasks.add_task(
                run_charleston_workflow, 
                task_id, 
                request.tms, 
                request.include_property_card,
                request.include_tax_info,
                request.include_deeds
            )
        elif request.county.lower() == "berkeley":
            background_tasks.add_task(
                run_berkeley_workflow, 
                task_id, 
                request.tms, 
                request.include_property_card,
                request.include_tax_info,
                request.include_deeds
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported county")
            
        return {"task_id": task_id, "message": f"Started {request.county} workflow for TMS {request.tms}"}
    
    except Exception as e:
        logger.exception(f"Error starting workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting workflow: {str(e)}")

@app.get("/workflow-status/{task_id}", response_model=WorkflowStatus)
async def get_workflow_status(task_id: str):
    """Get the status of a workflow by task ID"""
    if task_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Task not found")
    
    workflow = active_workflows[task_id]
    return WorkflowStatus(
        task_id=task_id,
        status=workflow["status"],
        progress=workflow["progress"],
        message=workflow["message"],
        documents=workflow.get("documents", [])
    )

@app.get("/documents/{county}/{tms}")
async def get_documents(county: str, tms: str):
    """Get available documents for a specific county and TMS number"""
    try:
        county = county.lower()
        if county not in ["charleston", "berkeley"]:
            raise HTTPException(status_code=400, detail="Unsupported county")
        
        # Define the download directory for this TMS
        download_dir = f"data/downloads/{county}/{tms}"
        if not os.path.exists(download_dir):
            return {"documents": []}
        
        # Get list of available documents
        documents = []
        for filename in os.listdir(download_dir):
            if filename.endswith(('.pdf', '.png', '.jpg')):
                doc_type = "unknown"
                if "property_card" in filename.lower():
                    doc_type = "property_card"
                elif "tax" in filename.lower():
                    doc_type = "tax_info"
                elif "db" in filename.lower() or "deed" in filename.lower():
                    doc_type = "deed"
                
                documents.append({
                    "filename": filename,
                    "type": doc_type,
                    "url": f"/download/{county}/{tms}/{filename}"
                })
        
        return {"documents": documents}
        
    except Exception as e:
        logger.exception(f"Error retrieving documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")

@app.get("/download/{county}/{tms}/{filename}")
async def download_document(county: str, tms: str, filename: str):
    """Download a specific document"""
    try:
        file_path = f"data/downloads/{county}/{tms}/{filename}"
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Document not found")
        
        return FileResponse(
            path=file_path, 
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error downloading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading document: {str(e)}")

# API endpoints for document retrieval
@app.get("/api/documents/{county}/{tms}/{filename}", response_class=FileResponse)
async def get_document(county: str, tms: str, filename: str):
    """Get a specific document file"""
    try:
        # Security check to prevent directory traversal
        if '..' in filename or '/' in filename:
            logger.warning(f"Security issue: possible directory traversal attempt: {filename}")
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Build the document path
        document_path = os.path.join("data", "downloads", county, tms, filename)
        if not os.path.exists(document_path):
            # Check if this is an error screenshot
            if filename.startswith("download_error"):
                # Try to find in screenshots folder
                screenshot_path = os.path.join("data", "screenshots", county, tms, filename)
                if os.path.exists(screenshot_path):
                    return FileResponse(screenshot_path)
                    
            logger.error(f"Document not found: {document_path}")
            raise HTTPException(status_code=404, detail=f"Document not found: {filename}")
        
        return FileResponse(document_path)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Error retrieving document: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")

# API endpoint for screenshots
@app.get("/api/screenshots/{county}/{tms}/{filename}", response_class=FileResponse)
async def get_screenshot(county: str, tms: str, filename: str):
    """Get a specific error screenshot"""
    try:
        # Security check to prevent directory traversal
        if '..' in filename or '/' in filename:
            logger.warning(f"Security issue: possible directory traversal attempt: {filename}")
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Make sure directories exist
        screenshot_dir = os.path.join("data", "screenshots", county, tms)
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # Build the screenshot path
        screenshot_path = os.path.join("data", "screenshots", county, tms, filename)
        
        # If screenshot doesn't exist, return a placeholder
        if not os.path.exists(screenshot_path):
            placeholder_path = os.path.join("data", "screenshots", "placeholder_error.png")
            if not os.path.exists(placeholder_path):
                # Create a very simple placeholder image
                from PIL import Image, ImageDraw, ImageFont
                img = Image.new('RGB', (800, 600), color = (255, 243, 205))
                d = ImageDraw.Draw(img)
                d.text((400, 300), f"Error: {filename}", fill=(216, 76, 76), anchor="mm")
                os.makedirs(os.path.dirname(placeholder_path), exist_ok=True)
                img.save(placeholder_path)
                
            return FileResponse(placeholder_path)
        
        return FileResponse(screenshot_path)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Error retrieving screenshot: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving screenshot: {str(e)}")

# Background task functions
async def run_charleston_workflow(task_id, tms, include_property_card, include_tax_info, include_deeds):
    """Run Charleston County workflow in background"""
    try:
        # Update status
        active_workflows[task_id]["status"] = "running"
        active_workflows[task_id]["message"] = "Starting Charleston workflow"
        
        # Initialize workflow
        workflow = CharlestonWorkflow()
        
        # Execute workflow with progress updates
        await workflow.run(
            tms=tms,
            include_property_card=include_property_card,
            include_tax_info=include_tax_info,
            include_deeds=include_deeds,
            progress_callback=lambda p, msg, docs=None: update_workflow_status(task_id, p, msg, docs)
        )
        
        # Mark as complete
        active_workflows[task_id]["status"] = "completed"
        active_workflows[task_id]["progress"] = 100
        active_workflows[task_id]["message"] = "Workflow completed successfully"
        
    except Exception as e:
        logger.exception(f"Error in Charleston workflow: {str(e)}")
        active_workflows[task_id]["status"] = "failed"
        active_workflows[task_id]["message"] = f"Workflow failed: {str(e)}"

async def run_berkeley_workflow(task_id, tms, include_property_card, include_tax_info, include_deeds):
    """Run Berkeley County workflow in background"""
    try:
        # Update status
        active_workflows[task_id]["status"] = "running"
        active_workflows[task_id]["message"] = "Starting Berkeley workflow"
        
        # Initialize workflow
        workflow = BerkeleyWorkflow()
        
        # Execute workflow with progress updates
        await workflow.run(
            tms=tms,
            include_property_card=include_property_card,
            include_tax_info=include_tax_info,
            include_deeds=include_deeds,
            progress_callback=lambda p, msg, docs=None: update_workflow_status(task_id, p, msg, docs)
        )
        
        # Mark as complete
        active_workflows[task_id]["status"] = "completed"
        active_workflows[task_id]["progress"] = 100
        active_workflows[task_id]["message"] = "Workflow completed successfully"
        
    except Exception as e:
        logger.exception(f"Error in Berkeley workflow: {str(e)}")
        active_workflows[task_id]["status"] = "failed"
        active_workflows[task_id]["message"] = f"Workflow failed: {str(e)}"

def update_workflow_status(task_id, progress, message, documents=None):
    """Update the status of a workflow"""
    if task_id in active_workflows:
        active_workflows[task_id]["progress"] = progress
        active_workflows[task_id]["message"] = message
        if documents:
            active_workflows[task_id]["documents"] = documents
