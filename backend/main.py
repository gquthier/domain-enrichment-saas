import asyncio
import json
import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.config import settings
from backend.enrichment_engine import EnrichmentEngine, find_company_col, detect_context_columns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Domain Enrichment SaaS", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# In-memory storage for jobs and websockets
jobs: Dict[str, dict] = {}
websocket_connections: Dict[str, WebSocket] = {}


# Pydantic models
class ColumnMapping(BaseModel):
    source_column: str
    target_column: str


class EnrichmentRequest(BaseModel):
    job_id: str
    column_mappings: List[ColumnMapping]


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    total: int
    message: str
    result_file: Optional[str] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    return FileResponse(str(frontend_path / "index.html"))


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload CSV or XLSX file and return job_id with detected columns"""
    logger.info(f"📤 Upload request received for file: {file.filename}")
    try:
        # Validate file type
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            logger.error(f"❌ Invalid file type: {file.filename}")
            raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

        # Generate job ID
        job_id = str(uuid.uuid4())
        logger.info(f"🆔 Generated job_id: {job_id}")

        # Save uploaded file
        file_path = settings.UPLOAD_DIR / f"{job_id}_{file.filename}"
        content = await file.read()

        # Check file size
        if len(content) > settings.MAX_UPLOAD_SIZE:
            logger.error(f"❌ File too large: {len(content)} bytes")
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")

        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"💾 File saved to: {file_path}")

        # Read file to detect columns and count rows
        try:
            if file.filename.endswith('.csv'):
                # Read first 5 rows for column detection
                df_sample = pd.read_csv(file_path, nrows=5)
                # Count total rows (more efficient than reading full file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    total_rows = sum(1 for _ in f) - 1  # -1 for header
                logger.info(f"📊 CSV file: {total_rows} rows detected")
            else:
                # For Excel, read full file (Excel files are typically smaller)
                df_sample = pd.read_excel(file_path)
                total_rows = len(df_sample)
                # Keep only 5 rows for detection
                df_sample = df_sample.head(5)
                logger.info(f"📊 Excel file: {total_rows} rows detected")
        except Exception as e:
            logger.error(f"❌ Error reading file: {str(e)}")
            os.remove(file_path)
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

        # Detect company column
        try:
            company_col = find_company_col(df_sample)
            logger.info(f"✅ Company column detected: {company_col}")
        except ValueError:
            company_col = None
            logger.warning(f"⚠️  No company column detected")

        # Detect context columns
        context_cols = detect_context_columns(df_sample)
        logger.info(f"🔍 Context columns detected: {context_cols}")

        # Store job info
        jobs[job_id] = {
            "job_id": job_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "status": "uploaded",
            "progress": 0,
            "total": 0,
            "message": "File uploaded successfully",
            "uploaded_at": datetime.now().isoformat(),
            "columns": list(df_sample.columns),
            "detected_company_col": company_col,
            "detected_context_cols": context_cols,
            "result_file": None,
            "error": None
        }
        logger.info(f"💼 Job stored in memory: {job_id}")
        logger.info(f"📋 Current jobs in memory: {list(jobs.keys())}")

        response_data = {
            "job_id": job_id,
            "filename": file.filename,
            "columns": list(df_sample.columns),
            "detected_company_col": company_col,
            "detected_context_cols": context_cols,
            "row_count": total_rows
        }
        logger.info(f"✅ Upload successful for job {job_id}: {total_rows} rows")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/api/enrich")
async def start_enrichment(request: EnrichmentRequest):
    """Start enrichment process with column mappings"""
    job_id = request.job_id
    logger.info(f"🚀 Enrichment request received for job_id: {job_id}")
    logger.info(f"📋 Current jobs in memory: {list(jobs.keys())}")
    logger.info(f"🗺️  Column mappings: {request.column_mappings}")

    if job_id not in jobs:
        logger.error(f"❌ Job not found: {job_id}")
        logger.error(f"Available jobs: {list(jobs.keys())}")
        raise HTTPException(status_code=404, detail=f"Job not found. Available jobs: {list(jobs.keys())}")

    job = jobs[job_id]
    logger.info(f"📦 Job found - Status: {job['status']}, File: {job['filename']}")

    if job["status"] == "processing":
        logger.warning(f"⚠️  Job already processing: {job_id}")
        raise HTTPException(status_code=400, detail="Job already processing")

    if job["status"] == "completed":
        logger.warning(f"⚠️  Job already completed: {job_id}")
        raise HTTPException(status_code=400, detail="Job already completed")

    # Update job status
    job["status"] = "processing"
    job["message"] = "Starting enrichment..."
    job["column_mappings"] = [m.dict() for m in request.column_mappings]
    logger.info(f"✅ Job status updated to 'processing'")

    # Start enrichment in background
    asyncio.create_task(process_enrichment(job_id))
    logger.info(f"⚡ Background enrichment task started for job {job_id}")

    return {"job_id": job_id, "status": "processing"}


async def process_enrichment(job_id: str):
    """Background task to process enrichment"""
    job = jobs[job_id]

    try:
        # Load file
        file_path = Path(job["file_path"])
        if file_path.suffix == '.csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        # Apply column mappings (rename columns if needed)
        mappings = {m["source_column"]: m["target_column"] for m in job.get("column_mappings", [])}
        df = df.rename(columns=mappings)

        job["total"] = len(df)

        # Progress callback
        async def progress_callback(current: int, total: int, message: str):
            job["progress"] = current
            job["total"] = total
            job["message"] = message

            # Send update via WebSocket if connected
            if job_id in websocket_connections:
                try:
                    await websocket_connections[job_id].send_json({
                        "type": "progress",
                        "job_id": job_id,
                        "progress": current,
                        "total": total,
                        "percentage": int((current / max(1, total)) * 100),
                        "message": message
                    })
                except Exception:
                    pass

        # Create enrichment engine
        engine = EnrichmentEngine(progress_callback=progress_callback)

        # Run enrichment
        result_df = await engine.enrich_dataframe(df)

        # Clean up result (remove debug columns for final export)
        export_df = result_df.copy()
        cols_to_drop = ["URL_ambiguity", "URL_cand_count", "URL_reg_match",
                        "URL_reg_ids_found", "URL_debug", "URL_found_domain"]
        export_df = export_df.drop(columns=[c for c in cols_to_drop if c in export_df.columns], errors="ignore")

        # Save result
        result_filename = f"{job_id}_enriched_{Path(job['filename']).stem}"
        if job['filename'].endswith('.csv'):
            result_path = settings.RESULTS_DIR / f"{result_filename}.csv"
            export_df.to_csv(result_path, index=False)
        else:
            result_path = settings.RESULTS_DIR / f"{result_filename}.xlsx"
            export_df.to_excel(result_path, index=False)

        job["status"] = "completed"
        job["message"] = "Enrichment completed successfully"
        job["result_file"] = str(result_path)
        job["completed_at"] = datetime.now().isoformat()

        # Send completion via WebSocket
        if job_id in websocket_connections:
            try:
                await websocket_connections[job_id].send_json({
                    "type": "completed",
                    "job_id": job_id,
                    "message": "Enrichment completed successfully",
                    "download_url": f"/api/download/{job_id}"
                })
            except Exception:
                pass

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["message"] = f"Enrichment failed: {str(e)}"

        # Send error via WebSocket
        if job_id in websocket_connections:
            try:
                await websocket_connections[job_id].send_json({
                    "type": "error",
                    "job_id": job_id,
                    "error": str(e)
                })
            except Exception:
                pass


@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    """Get job status"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    percentage = int((job["progress"] / max(1, job["total"])) * 100) if job["total"] > 0 else 0

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "total": job["total"],
        "percentage": percentage,
        "message": job["message"],
        "result_file": job.get("result_file"),
        "error": job.get("error")
    }


@app.get("/api/download/{job_id}")
async def download_result(job_id: str):
    """Download enriched file"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.get("result_file") or not Path(job["result_file"]).exists():
        raise HTTPException(status_code=404, detail="Result file not found")

    result_path = Path(job["result_file"])
    return FileResponse(
        path=result_path,
        filename=result_path.name,
        media_type='application/octet-stream'
    )


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await websocket.accept()
    websocket_connections[job_id] = websocket

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back or handle messages if needed
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        if job_id in websocket_connections:
            del websocket_connections[job_id]
    except Exception as e:
        if job_id in websocket_connections:
            del websocket_connections[job_id]


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its associated files"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Delete files
    try:
        if job.get("file_path") and Path(job["file_path"]).exists():
            os.remove(job["file_path"])
        if job.get("result_file") and Path(job["result_file"]).exists():
            os.remove(job["result_file"])
    except Exception:
        pass

    # Remove from jobs
    del jobs[job_id]

    return {"message": "Job deleted successfully"}


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs"""
    return [
        {
            "job_id": job_id,
            "filename": job["filename"],
            "status": job["status"],
            "uploaded_at": job["uploaded_at"],
            "message": job["message"]
        }
        for job_id, job in jobs.items()
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
