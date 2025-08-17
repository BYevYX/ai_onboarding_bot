"""
Onboarding workflow API endpoints.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.logging import get_logger
from app.ai.langchain.workflows import onboarding_workflow, OnboardingState
from app.ai.langchain.llm_manager import onboarding_llm

logger = get_logger("api.onboarding")
router = APIRouter()


class OnboardingStartRequest(BaseModel):
    """Start onboarding request model."""
    user_id: int
    telegram_id: int
    language: str = "ru"
    user_info: Dict[str, Any]


class OnboardingMessageRequest(BaseModel):
    """Onboarding message request model."""
    user_id: int
    message: str
    language: str = "ru"


class OnboardingResponse(BaseModel):
    """Onboarding response model."""
    user_id: int
    stage: str
    message: str
    next_action: Optional[str]
    completion_score: float
    metadata: Dict[str, Any]


class OnboardingStatusResponse(BaseModel):
    """Onboarding status response model."""
    user_id: int
    stage: str
    completion_score: float
    documents_reviewed: int
    questions_asked: int
    is_completed: bool
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


@router.post("/start", response_model=OnboardingResponse)
async def start_onboarding(request: OnboardingStartRequest) -> OnboardingResponse:
    """Start the onboarding process for a user."""
    try:
        # Initialize onboarding state
        initial_state: OnboardingState = {
            "user_id": request.user_id,
            "telegram_id": request.telegram_id,
            "stage": "welcome",
            "user_info": request.user_info,
            "messages": [],
            "documents_reviewed": [],
            "questions_asked": [],
            "completion_score": 0.0,
            "language": request.language,
            "context": None,
            "next_action": None
        }
        
        # Run welcome workflow
        result = await onboarding_workflow._welcome_node(initial_state)
        
        # Get the welcome message
        welcome_message = ""
        if result["messages"]:
            welcome_message = result["messages"][-1].content
        
        logger.info(
            "Onboarding started",
            user_id=request.user_id,
            language=request.language
        )
        
        return OnboardingResponse(
            user_id=request.user_id,
            stage=result["stage"],
            message=welcome_message,
            next_action=result.get("next_action"),
            completion_score=result["completion_score"],
            metadata={
                "documents_reviewed": len(result["documents_reviewed"]),
                "questions_asked": len(result["questions_asked"])
            }
        )
        
    except Exception as e:
        logger.error("Failed to start onboarding", error=str(e), user_id=request.user_id)
        raise HTTPException(status_code=500, detail="Failed to start onboarding")


@router.post("/message", response_model=OnboardingResponse)
async def process_onboarding_message(request: OnboardingMessageRequest) -> OnboardingResponse:
    """Process a message in the onboarding workflow."""
    try:
        # TODO: Retrieve current onboarding state from database
        # For now, create a mock state
        current_state: OnboardingState = {
            "user_id": request.user_id,
            "telegram_id": request.user_id,  # Mock telegram_id
            "stage": "questions_answers",
            "user_info": {"name": "Test User", "position": "Developer", "department": "IT"},
            "messages": [],
            "documents_reviewed": ["handbook", "policies"],
            "questions_asked": [],
            "completion_score": 50.0,
            "language": request.language,
            "context": None,
            "next_action": None
        }
        
        # Add user message to state
        from langchain_core.messages import HumanMessage
        current_state["messages"].append(HumanMessage(content=request.message))
        
        # Process through Q&A workflow
        result = await onboarding_workflow._questions_answers_node(current_state)
        
        # Get AI response
        ai_message = ""
        if result["messages"]:
            ai_message = result["messages"][-1].content
        
        logger.info(
            "Onboarding message processed",
            user_id=request.user_id,
            stage=result["stage"]
        )
        
        return OnboardingResponse(
            user_id=request.user_id,
            stage=result["stage"],
            message=ai_message,
            next_action=result.get("next_action"),
            completion_score=result["completion_score"],
            metadata={
                "documents_reviewed": len(result["documents_reviewed"]),
                "questions_asked": len(result["questions_asked"])
            }
        )
        
    except Exception as e:
        logger.error("Failed to process onboarding message", error=str(e), user_id=request.user_id)
        raise HTTPException(status_code=500, detail="Failed to process message")


@router.get("/{user_id}/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(user_id: int) -> OnboardingStatusResponse:
    """Get current onboarding status for a user."""
    try:
        # TODO: Retrieve onboarding state from database
        
        logger.info("Onboarding status requested", user_id=user_id)
        
        # Mock response - replace with actual database implementation
        return OnboardingStatusResponse(
            user_id=user_id,
            stage="questions_answers",
            completion_score=75.0,
            documents_reviewed=3,
            questions_asked=5,
            is_completed=False,
            started_at=datetime.utcnow(),
            completed_at=None
        )
        
    except Exception as e:
        logger.error("Failed to get onboarding status", error=str(e), user_id=user_id)
        raise HTTPException(status_code=404, detail="Onboarding status not found")


@router.post("/{user_id}/complete", response_model=OnboardingResponse)
async def complete_onboarding(user_id: int) -> OnboardingResponse:
    """Complete the onboarding process for a user."""
    try:
        # TODO: Retrieve current onboarding state from database
        current_state: OnboardingState = {
            "user_id": user_id,
            "telegram_id": user_id,
            "stage": "completion",
            "user_info": {"name": "Test User", "position": "Developer", "department": "IT"},
            "messages": [],
            "documents_reviewed": ["handbook", "policies", "procedures"],
            "questions_asked": ["question1", "question2", "question3"],
            "completion_score": 0.0,
            "language": "ru",
            "context": None,
            "next_action": None
        }
        
        # Run completion workflow
        result = await onboarding_workflow._completion_node(current_state)
        
        # Get completion message
        completion_message = ""
        if result["messages"]:
            completion_message = result["messages"][-1].content
        
        logger.info(
            "Onboarding completed",
            user_id=user_id,
            completion_score=result["completion_score"]
        )
        
        return OnboardingResponse(
            user_id=user_id,
            stage=result["stage"],
            message=completion_message,
            next_action=result.get("next_action"),
            completion_score=result["completion_score"],
            metadata={
                "documents_reviewed": len(result["documents_reviewed"]),
                "questions_asked": len(result["questions_asked"]),
                "completed_at": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Failed to complete onboarding", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to complete onboarding")


@router.post("/{user_id}/reset")
async def reset_onboarding(user_id: int) -> Dict[str, Any]:
    """Reset onboarding progress for a user."""
    try:
        # TODO: Reset onboarding state in database
        
        logger.info("Onboarding reset requested", user_id=user_id)
        
        return {
            "status": "reset",
            "user_id": user_id,
            "message": "Onboarding progress has been reset",
            "reset_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to reset onboarding", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to reset onboarding")


@router.get("/analytics/stats")
async def get_onboarding_analytics() -> Dict[str, Any]:
    """Get onboarding analytics and statistics."""
    try:
        # TODO: Implement analytics from database
        
        logger.info("Onboarding analytics requested")
        
        # Mock analytics - replace with actual database queries
        return {
            "total_users": 150,
            "completed_onboarding": 120,
            "in_progress": 25,
            "not_started": 5,
            "average_completion_time_hours": 4.5,
            "average_completion_score": 87.3,
            "completion_rate": 80.0,
            "stage_distribution": {
                "welcome": 5,
                "profile_setup": 8,
                "document_review": 12,
                "questions_answers": 15,
                "completed": 120
            },
            "department_stats": {
                "IT": {"total": 50, "completed": 45},
                "HR": {"total": 30, "completed": 28},
                "Sales": {"total": 40, "completed": 35},
                "Marketing": {"total": 30, "completed": 12}
            }
        }
        
    except Exception as e:
        logger.error("Failed to get onboarding analytics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get analytics")


@router.post("/generate-welcome")
async def generate_welcome_message(
    user_name: str,
    position: str,
    department: str,
    language: str = "ru"
) -> Dict[str, str]:
    """Generate a personalized welcome message."""
    try:
        welcome_message = await onboarding_llm.generate_welcome_message(
            user_name=user_name,
            position=position,
            department=department,
            language=language
        )
        
        logger.info(
            "Welcome message generated",
            user_name=user_name,
            language=language
        )
        
        return {
            "message": welcome_message,
            "language": language,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to generate welcome message", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate welcome message")