from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from pathlib import Path
import os

from services.pdf_parser import PdfParser

paf_parsing_router = APIRouter()

# Path for the uploaded files
UPLOAD_FOLDER = Path("uploaded_file")
if not UPLOAD_FOLDER.exists():
    UPLOAD_FOLDER.mkdir(parents=True)

@paf_parsing_router.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    translate_to_english: bool = Query(False)  
):
    try:
        # Validate file extension
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        
        file_path = UPLOAD_FOLDER / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()  
            f.write(content)  
        
        parser = PdfParser(file_path)
        
        # Parse and optionally translate
        parser.to_markdown(
            save_as=f'outputs/{Path(file.filename).stem}.md',
            translate_to_english=translate_to_english
        )
        
        return JSONResponse(content={
            "message": "File parsed successfully", 
            "filename": file.filename,
        })
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")