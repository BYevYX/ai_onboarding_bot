"""
Custom application exceptions.
"""

from typing import Any, Dict, Optional


class BaseAppException(Exception):
    """Base application exception."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(BaseAppException):
    """Configuration related errors."""
    pass


class DatabaseError(BaseAppException):
    """Database related errors."""
    pass


class AuthenticationError(BaseAppException):
    """Authentication related errors."""
    pass


class AuthorizationError(BaseAppException):
    """Authorization related errors."""
    pass


class ValidationError(BaseAppException):
    """Data validation errors."""
    pass


class FileProcessingError(BaseAppException):
    """File processing related errors."""
    pass


class AIServiceError(BaseAppException):
    """AI service related errors."""
    pass


class LangChainError(BaseAppException):
    """LangChain related errors."""
    pass


class VectorStoreError(BaseAppException):
    """Vector store related errors."""
    pass


class TelegramBotError(BaseAppException):
    """Telegram bot related errors."""
    pass


class RateLimitError(BaseAppException):
    """Rate limiting errors."""
    pass


class ExternalServiceError(BaseAppException):
    """External service integration errors."""
    pass


# User-related exceptions
class UserNotFoundError(BaseAppException):
    """User not found error."""
    
    def __init__(self, user_id: Any):
        super().__init__(
            message=f"User with ID {user_id} not found",
            error_code="USER_NOT_FOUND",
            details={"user_id": user_id}
        )


class UserAlreadyExistsError(BaseAppException):
    """User already exists error."""
    
    def __init__(self, identifier: str):
        super().__init__(
            message=f"User with identifier {identifier} already exists",
            error_code="USER_ALREADY_EXISTS",
            details={"identifier": identifier}
        )


# Document-related exceptions
class DocumentNotFoundError(BaseAppException):
    """Document not found error."""
    
    def __init__(self, document_id: Any):
        super().__init__(
            message=f"Document with ID {document_id} not found",
            error_code="DOCUMENT_NOT_FOUND",
            details={"document_id": document_id}
        )


class DocumentProcessingError(FileProcessingError):
    """Document processing specific error."""
    
    def __init__(self, filename: str, reason: str):
        super().__init__(
            message=f"Failed to process document {filename}: {reason}",
            error_code="DOCUMENT_PROCESSING_FAILED",
            details={"filename": filename, "reason": reason}
        )


# AI-related exceptions
class EmbeddingGenerationError(AIServiceError):
    """Embedding generation error."""
    
    def __init__(self, text_length: int, reason: str):
        super().__init__(
            message=f"Failed to generate embeddings for text of length {text_length}: {reason}",
            error_code="EMBEDDING_GENERATION_FAILED",
            details={"text_length": text_length, "reason": reason}
        )


class LLMResponseError(AIServiceError):
    """LLM response error."""
    
    def __init__(self, model: str, reason: str):
        super().__init__(
            message=f"Failed to get response from model {model}: {reason}",
            error_code="LLM_RESPONSE_FAILED",
            details={"model": model, "reason": reason}
        )


# Vector store exceptions
class VectorSearchError(VectorStoreError):
    """Vector search error."""
    
    def __init__(self, query: str, reason: str):
        super().__init__(
            message=f"Vector search failed for query '{query}': {reason}",
            error_code="VECTOR_SEARCH_FAILED",
            details={"query": query, "reason": reason}
        )


class VectorIndexError(VectorStoreError):
    """Vector indexing error."""
    
    def __init__(self, document_id: Any, reason: str):
        super().__init__(
            message=f"Failed to index document {document_id}: {reason}",
            error_code="VECTOR_INDEX_FAILED",
            details={"document_id": document_id, "reason": reason}
        )