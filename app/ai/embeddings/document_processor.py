"""
Document processing and embedding generation for onboarding materials.
"""

import os
import uuid
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import asyncio

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
import magic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.exceptions import DocumentProcessingError, FileProcessingError
from app.ai.langchain.vector_store import vector_store
from app.ai.langchain.llm_manager import llm_manager

logger = get_logger("ai.document_processor")


class DocumentProcessor:
    """Process documents and generate embeddings for RAG system."""
    
    def __init__(self):
        self.settings = get_settings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Supported file types and their loaders
        self.loaders = {
            "pdf": PyPDFLoader,
            "docx": Docx2txtLoader,
            "txt": TextLoader,
            "md": UnstructuredMarkdownLoader
        }
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type using python-magic."""
        try:
            mime_type = magic.from_file(file_path, mime=True)
            
            # Map MIME types to extensions
            mime_to_ext = {
                "application/pdf": "pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
                "text/plain": "txt",
                "text/markdown": "md"
            }
            
            return mime_to_ext.get(mime_type, Path(file_path).suffix.lower().lstrip('.'))
            
        except Exception as e:
            logger.warning(
                "Failed to detect file type with magic, using extension",
                file_path=file_path,
                error=str(e)
            )
            return Path(file_path).suffix.lower().lstrip('.')
    
    def _validate_file(self, file_path: str) -> Tuple[bool, str]:
        """Validate file size and type."""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False, "File does not exist"
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.settings.file_upload.max_file_size:
                return False, f"File size ({file_size}) exceeds maximum allowed size"
            
            # Check file type
            file_type = self._detect_file_type(file_path)
            if file_type not in self.settings.file_upload.allowed_file_types:
                return False, f"File type '{file_type}' is not supported"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    async def load_document(self, file_path: str) -> List[Document]:
        """Load document from file."""
        try:
            # Validate file
            is_valid, validation_message = self._validate_file(file_path)
            if not is_valid:
                raise FileProcessingError(
                    message=validation_message,
                    error_code="FILE_VALIDATION_FAILED"
                )
            
            # Detect file type and get appropriate loader
            file_type = self._detect_file_type(file_path)
            loader_class = self.loaders.get(file_type)
            
            if not loader_class:
                raise FileProcessingError(
                    message=f"No loader available for file type: {file_type}",
                    error_code="UNSUPPORTED_FILE_TYPE"
                )
            
            # Load document
            loader = loader_class(file_path)
            documents = loader.load()
            
            # Add metadata
            filename = Path(file_path).name
            for doc in documents:
                doc.metadata.update({
                    "source": file_path,
                    "filename": filename,
                    "file_type": file_type,
                    "file_size": os.path.getsize(file_path)
                })
            
            logger.info(
                "Document loaded successfully",
                file_path=file_path,
                file_type=file_type,
                document_count=len(documents)
            )
            
            return documents
            
        except Exception as e:
            logger.error(
                "Failed to load document",
                file_path=file_path,
                error=str(e)
            )
            raise DocumentProcessingError(
                filename=Path(file_path).name,
                reason=str(e)
            )
    
    async def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks."""
        try:
            chunks = self.text_splitter.split_documents(documents)
            
            # Add chunk metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "chunk_id": str(uuid.uuid4()),
                    "chunk_index": i,
                    "chunk_size": len(chunk.page_content)
                })
            
            logger.info(
                "Documents split into chunks",
                original_count=len(documents),
                chunk_count=len(chunks)
            )
            
            return chunks
            
        except Exception as e:
            logger.error("Failed to split documents", error=str(e))
            raise DocumentProcessingError(
                filename="multiple",
                reason=f"Text splitting failed: {str(e)}"
            )
    
    async def process_and_index_document(
        self,
        file_path: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process document and add to vector store."""
        try:
            document_id = str(uuid.uuid4())
            
            # Load document
            documents = await self.load_document(file_path)
            
            # Split into chunks
            chunks = await self.split_documents(documents)
            
            # Add additional metadata
            metadata = document_metadata or {}
            metadata.update({
                "document_id": document_id,
                "processed_at": asyncio.get_event_loop().time()
            })
            
            # Add to vector store
            await vector_store.add_documents(
                documents=chunks,
                document_id=document_id,
                metadata=metadata
            )
            
            logger.info(
                "Document processed and indexed",
                document_id=document_id,
                file_path=file_path,
                chunk_count=len(chunks)
            )
            
            return document_id
            
        except Exception as e:
            logger.error(
                "Failed to process and index document",
                file_path=file_path,
                error=str(e)
            )
            raise
    
    async def process_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Process all documents in a directory."""
        try:
            directory = Path(directory_path)
            if not directory.exists():
                raise FileProcessingError(
                    message=f"Directory does not exist: {directory_path}",
                    error_code="DIRECTORY_NOT_FOUND"
                )
            
            # Find all supported files
            pattern = "**/*" if recursive else "*"
            all_files = directory.glob(pattern)
            
            supported_files = [
                f for f in all_files
                if f.is_file() and f.suffix.lower().lstrip('.') in self.settings.file_upload.allowed_file_types
            ]
            
            logger.info(
                "Processing directory",
                directory_path=directory_path,
                file_count=len(supported_files),
                recursive=recursive
            )
            
            # Process files concurrently
            document_ids = []
            semaphore = asyncio.Semaphore(5)  # Limit concurrent processing
            
            async def process_file(file_path: Path) -> Optional[str]:
                async with semaphore:
                    try:
                        return await self.process_and_index_document(
                            str(file_path),
                            document_metadata
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to process file in directory",
                            file_path=str(file_path),
                            error=str(e)
                        )
                        return None
            
            tasks = [process_file(file_path) for file_path in supported_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect successful document IDs
            document_ids = [
                result for result in results
                if isinstance(result, str) and result is not None
            ]
            
            logger.info(
                "Directory processing completed",
                directory_path=directory_path,
                processed_count=len(document_ids),
                total_files=len(supported_files)
            )
            
            return document_ids
            
        except Exception as e:
            logger.error(
                "Failed to process directory",
                directory_path=directory_path,
                error=str(e)
            )
            raise
    
    async def update_document_metadata(
        self,
        document_id: str,
        metadata_updates: Dict[str, Any]
    ) -> bool:
        """Update metadata for existing document."""
        try:
            # This would require implementing metadata update in vector store
            # For now, we'll log the operation
            logger.info(
                "Document metadata update requested",
                document_id=document_id,
                updates=metadata_updates
            )
            
            # TODO: Implement metadata update in vector store
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update document metadata",
                document_id=document_id,
                error=str(e)
            )
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete document from vector store."""
        try:
            success = await vector_store.delete_documents(document_id)
            
            if success:
                logger.info("Document deleted", document_id=document_id)
            else:
                logger.warning("Document deletion failed", document_id=document_id)
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to delete document",
                document_id=document_id,
                error=str(e)
            )
            return False


# Global document processor instance
document_processor = DocumentProcessor()