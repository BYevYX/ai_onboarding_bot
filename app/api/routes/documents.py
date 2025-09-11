"""
Document management API endpoints.
"""

from typing import List, Optional, Dict, Any
import os
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.exceptions import DocumentProcessingError, FileProcessingError
from app.ai.embeddings.document_processor import document_processor
from app.ai.langchain.vector_store import vector_store

logger = get_logger("api.documents")
router = APIRouter()


class DocumentUploadResponse(BaseModel):
    """Document upload response model."""
    document_id: str
    filename: str
    file_size: int
    status: str
    message: str


class DocumentSearchRequest(BaseModel):
    """Document search request model."""
    query: str
    limit: int = 5
    score_threshold: float = 0.0
    filters: Optional[Dict[str, Any]] = None


class DocumentSearchResult(BaseModel):
    """Document search result model."""
    content: str
    metadata: Dict[str, Any]
    score: float


class DocumentSearchResponse(BaseModel):
    """Document search response model."""
    query: str
    results: List[DocumentSearchResult]
    total_results: int


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Query(None, description="Document type (policy, handbook, etc.)"),
    department: Optional[str] = Query(None, description="Department"),
    language: Optional[str] = Query("ru", description="Document language")
) -> DocumentUploadResponse:
    """Upload and process a document."""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Create upload directory if it doesn't exist
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        # Save uploaded file
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Prepare metadata
        metadata = {
            "title": file.filename,
            "document_type": document_type or "general",
            "department": department or "general",
            "language": language,
            "file_size": len(content)
        }
        
        # Process and index document
        document_id = await document_processor.process_and_index_document(
            str(file_path),
            metadata
        )
        
        # Clean up uploaded file
        os.remove(file_path)
        
        logger.info(
            "Document uploaded and processed",
            document_id=document_id,
            filename=file.filename,
            file_size=len(content)
        )
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            file_size=len(content),
            status="processed",
            message="Document successfully uploaded and indexed"
        )
        
    except (DocumentProcessingError, FileProcessingError) as e:
        logger.error("Document processing failed", error=str(e), filename=file.filename)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Document upload failed", error=str(e), filename=file.filename)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(request: DocumentSearchRequest) -> DocumentSearchResponse:
    """Search documents using vector similarity."""
    try:
        # Perform vector search
        results = await vector_store.similarity_search(
            query=request.query,
            k=request.limit,
            filter_conditions=request.filters,
            score_threshold=request.score_threshold
        )
        
        # Format results
        search_results = []
        for doc, score in results:
            search_results.append(DocumentSearchResult(
                content=doc.page_content,
                metadata=doc.metadata,
                score=score
            ))
        
        logger.info(
            "Document search completed",
            query=request.query[:100],
            results_count=len(search_results)
        )
        
        return DocumentSearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results)
        )
        
    except Exception as e:
        logger.error("Document search failed", error=str(e), query=request.query)
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/metadata/{document_id}")
async def get_document_metadata(document_id: str) -> Dict[str, Any]:
    """Get document metadata by ID."""
    try:
        # Search for documents with this ID
        documents = await vector_store.search_by_metadata(
            metadata_filter={"document_id": document_id},
            limit=1
        )
        
        if not documents:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return documents[0].metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get document metadata", error=str(e), document_id=document_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> Dict[str, str]:
    """Delete a document from the vector store."""
    try:
        success = await document_processor.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found or deletion failed")
        
        logger.info("Document deleted", document_id=document_id)
        
        return {
            "status": "deleted",
            "document_id": document_id,
            "message": "Document successfully deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document deletion failed", error=str(e), document_id=document_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_document_stats() -> Dict[str, Any]:
    """Get document collection statistics."""
    try:
        # Get collection info
        collection_info = await vector_store.get_collection_info()
        
        return {
            "collection_name": vector_store.collection_name,
            "total_documents": collection_info.get("points_count", 0),
            "vector_size": collection_info.get("vector_size", 0),
            "status": collection_info.get("status", "unknown")
        }
        
    except Exception as e:
        logger.error("Failed to get document stats", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/bulk-upload")
async def bulk_upload_directory(
    directory_path: str,
    recursive: bool = Query(True, description="Process subdirectories recursively"),
    document_type: Optional[str] = Query(None, description="Document type"),
    department: Optional[str] = Query(None, description="Department"),
    language: str = Query("ru", description="Document language")
) -> Dict[str, Any]:
    """Bulk upload documents from a directory."""
    try:
        # Validate directory path
        if not os.path.exists(directory_path):
            raise HTTPException(status_code=400, detail="Directory does not exist")
        
        # Prepare metadata
        metadata = {
            "document_type": document_type or "general",
            "department": department or "general",
            "language": language
        }
        
        # Process directory
        document_ids = await document_processor.process_directory(
            directory_path,
            recursive=recursive,
            document_metadata=metadata
        )
        
        logger.info(
            "Bulk upload completed",
            directory_path=directory_path,
            processed_count=len(document_ids)
        )
        
        return {
            "status": "completed",
            "directory_path": directory_path,
            "processed_documents": len(document_ids),
            "document_ids": document_ids,
            "message": f"Successfully processed {len(document_ids)} documents"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Bulk upload failed", error=str(e), directory_path=directory_path)
        raise HTTPException(status_code=500, detail="Bulk upload failed")