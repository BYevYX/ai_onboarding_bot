"""
Onboarding workflow service.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.database.models import OnboardingSession, User, OnboardingStage
from app.ai.langchain.workflows import onboarding_workflow, OnboardingState
from app.core.logging import get_logger
from app.core.exceptions import UserNotFoundError

logger = get_logger("services.onboarding")


class OnboardingService:
    """Service for managing onboarding workflows."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def start_onboarding(
        self,
        user_id: int,
        telegram_id: int,
        language: str = "ru",
        user_info: Optional[Dict[str, Any]] = None
    ) -> OnboardingSession:
        """Start onboarding process for a user."""
        try:
            # Check if user exists
            user_stmt = select(User).where(User.id == user_id)
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise UserNotFoundError(user_id)
            
            # Check for existing active session
            existing_stmt = (
                select(OnboardingSession)
                .where(OnboardingSession.user_id == user_id)
                .where(OnboardingSession.stage != OnboardingStage.COMPLETED)
            )
            existing_result = await self.db.execute(existing_stmt)
            existing_session = existing_result.scalar_one_or_none()
            
            if existing_session:
                logger.info("Resuming existing onboarding session", user_id=user_id, session_id=existing_session.id)
                return existing_session
            
            # Create new onboarding session
            session = OnboardingSession(
                user_id=user_id,
                stage=OnboardingStage.WELCOME,
                started_at=datetime.utcnow(),
                last_interaction=datetime.utcnow(),
                session_data={
                    "language": language,
                    "user_info": user_info or {},
                    "telegram_id": telegram_id
                }
            )
            
            self.db.add(session)
            await self.db.flush()
            await self.db.refresh(session)
            
            logger.info(
                "Onboarding session started",
                user_id=user_id,
                session_id=session.id,
                language=language
            )
            
            return session
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to start onboarding", error=str(e), user_id=user_id)
            raise
    
    async def get_onboarding_session(self, user_id: int) -> Optional[OnboardingSession]:
        """Get current onboarding session for user."""
        try:
            stmt = (
                select(OnboardingSession)
                .where(OnboardingSession.user_id == user_id)
                .order_by(OnboardingSession.created_at.desc())
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error("Failed to get onboarding session", error=str(e), user_id=user_id)
            return None
    
    async def update_onboarding_progress(
        self,
        session_id: int,
        stage: OnboardingStage,
        completion_score: float,
        session_data: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None
    ) -> Optional[OnboardingSession]:
        """Update onboarding session progress."""
        try:
            updates = {
                "stage": stage,
                "completion_score": completion_score,
                "last_interaction": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            if session_data:
                updates["session_data"] = session_data
            
            if context:
                updates["context"] = context
            
            # Mark as completed if stage is completed
            if stage == OnboardingStage.COMPLETED:
                updates["completed_at"] = datetime.utcnow()
            
            stmt = (
                update(OnboardingSession)
                .where(OnboardingSession.id == session_id)
                .values(**updates)
                .returning(OnboardingSession)
            )
            
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if session:
                logger.info(
                    "Onboarding progress updated",
                    session_id=session_id,
                    stage=stage.value,
                    completion_score=completion_score
                )
            
            return session
            
        except Exception as e:
            logger.error("Failed to update onboarding progress", error=str(e), session_id=session_id)
            return None
    
    async def process_user_message(
        self,
        user_id: int,
        message: str,
        language: str = "ru"
    ) -> Optional[str]:
        """Process user message through onboarding workflow."""
        try:
            # Get current session
            session = await self.get_onboarding_session(user_id)
            if not session:
                logger.warning("No onboarding session found", user_id=user_id)
                return None
            
            # Get session data
            session_data = session.session_data or {}
            user_info = session_data.get("user_info", {})
            
            # Create workflow state
            workflow_state: OnboardingState = {
                "user_id": user_id,
                "telegram_id": session_data.get("telegram_id", user_id),
                "stage": session.stage.value,
                "user_info": user_info,
                "messages": [],
                "documents_reviewed": session_data.get("documents_reviewed", []),
                "questions_asked": session_data.get("questions_asked", []),
                "completion_score": session.completion_score,
                "language": language,
                "context": session.context,
                "next_action": None
            }
            
            # Add user message
            from langchain_core.messages import HumanMessage
            workflow_state["messages"].append(HumanMessage(content=message))
            
            # Process through appropriate workflow node
            if session.stage == OnboardingStage.PROFILE_SETUP:
                result = await onboarding_workflow._profile_setup_node(workflow_state)
            elif session.stage == OnboardingStage.DOCUMENT_REVIEW:
                result = await onboarding_workflow._document_review_node(workflow_state)
            elif session.stage == OnboardingStage.QUESTIONS_ANSWERS:
                result = await onboarding_workflow._questions_answers_node(workflow_state)
            else:
                result = workflow_state
            
            # Update session with new state
            new_stage = OnboardingStage(result["stage"])
            await self.update_onboarding_progress(
                session.id,
                new_stage,
                result["completion_score"],
                {
                    "language": language,
                    "user_info": result["user_info"],
                    "telegram_id": result["telegram_id"],
                    "documents_reviewed": result["documents_reviewed"],
                    "questions_asked": result["questions_asked"],
                    "next_action": result.get("next_action")
                },
                result.get("context")
            )
            
            # Get AI response
            ai_response = ""
            if result["messages"]:
                ai_response = result["messages"][-1].content
            
            logger.info(
                "User message processed",
                user_id=user_id,
                stage=result["stage"],
                completion_score=result["completion_score"]
            )
            
            return ai_response
            
        except Exception as e:
            logger.error("Failed to process user message", error=str(e), user_id=user_id)
            return None
    
    async def complete_onboarding(self, user_id: int) -> Optional[OnboardingSession]:
        """Complete onboarding for user."""
        try:
            session = await self.get_onboarding_session(user_id)
            if not session:
                logger.warning("No onboarding session found for completion", user_id=user_id)
                return None
            
            # Run completion workflow
            session_data = session.session_data or {}
            workflow_state: OnboardingState = {
                "user_id": user_id,
                "telegram_id": session_data.get("telegram_id", user_id),
                "stage": "completion",
                "user_info": session_data.get("user_info", {}),
                "messages": [],
                "documents_reviewed": session_data.get("documents_reviewed", []),
                "questions_asked": session_data.get("questions_asked", []),
                "completion_score": session.completion_score,
                "language": session_data.get("language", "ru"),
                "context": session.context,
                "next_action": None
            }
            
            result = await onboarding_workflow._completion_node(workflow_state)
            
            # Update session
            updated_session = await self.update_onboarding_progress(
                session.id,
                OnboardingStage.COMPLETED,
                result["completion_score"],
                session_data
            )
            
            logger.info(
                "Onboarding completed",
                user_id=user_id,
                session_id=session.id,
                completion_score=result["completion_score"]
            )
            
            return updated_session
            
        except Exception as e:
            logger.error("Failed to complete onboarding", error=str(e), user_id=user_id)
            return None
    
    async def reset_onboarding(self, user_id: int) -> bool:
        """Reset onboarding progress for user."""
        try:
            # Delete existing sessions
            stmt = delete(OnboardingSession).where(OnboardingSession.user_id == user_id)
            await self.db.execute(stmt)
            
            logger.info("Onboarding reset", user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("Failed to reset onboarding", error=str(e), user_id=user_id)
            return False
    
    async def get_onboarding_analytics(self) -> Dict[str, Any]:
        """Get onboarding analytics."""
        try:
            # Total sessions
            total_stmt = select(OnboardingSession.id)
            total_result = await self.db.execute(total_stmt)
            total_sessions = len(total_result.scalars().all())
            
            # Completed sessions
            completed_stmt = select(OnboardingSession.id).where(
                OnboardingSession.stage == OnboardingStage.COMPLETED
            )
            completed_result = await self.db.execute(completed_stmt)
            completed_sessions = len(completed_result.scalars().all())
            
            # In progress sessions
            in_progress_stmt = select(OnboardingSession.id).where(
                OnboardingSession.stage.in_([
                    OnboardingStage.WELCOME,
                    OnboardingStage.PROFILE_SETUP,
                    OnboardingStage.DOCUMENT_REVIEW,
                    OnboardingStage.QUESTIONS_ANSWERS
                ])
            )
            in_progress_result = await self.db.execute(in_progress_stmt)
            in_progress_sessions = len(in_progress_result.scalars().all())
            
            # Stage distribution
            stage_stmt = select(OnboardingSession.stage, OnboardingSession.id)
            stage_result = await self.db.execute(stage_stmt)
            stage_data = stage_result.all()
            
            stage_distribution = {}
            for stage, session_id in stage_data:
                stage_name = stage.value if stage else "unknown"
                stage_distribution[stage_name] = stage_distribution.get(stage_name, 0) + 1
            
            # Average completion score
            score_stmt = select(OnboardingSession.completion_score).where(
                OnboardingSession.stage == OnboardingStage.COMPLETED
            )
            score_result = await self.db.execute(score_stmt)
            scores = score_result.scalars().all()
            avg_score = sum(scores) / len(scores) if scores else 0.0
            
            # Completion rate
            completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0.0
            
            analytics = {
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "in_progress_sessions": in_progress_sessions,
                "not_started": max(0, total_sessions - completed_sessions - in_progress_sessions),
                "completion_rate": round(completion_rate, 2),
                "average_completion_score": round(avg_score, 2),
                "stage_distribution": stage_distribution,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info("Onboarding analytics generated", total_sessions=total_sessions)
            return analytics
            
        except Exception as e:
            logger.error("Failed to get onboarding analytics", error=str(e))
            return {
                "total_sessions": 0,
                "completed_sessions": 0,
                "in_progress_sessions": 0,
                "not_started": 0,
                "completion_rate": 0.0,
                "average_completion_score": 0.0,
                "stage_distribution": {},
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def get_user_onboarding_history(self, user_id: int) -> List[OnboardingSession]:
        """Get onboarding history for user."""
        try:
            stmt = (
                select(OnboardingSession)
                .where(OnboardingSession.user_id == user_id)
                .order_by(OnboardingSession.created_at.desc())
            )
            result = await self.db.execute(stmt)
            sessions = result.scalars().all()
            
            logger.info("Onboarding history retrieved", user_id=user_id, sessions_count=len(sessions))
            return list(sessions)
            
        except Exception as e:
            logger.error("Failed to get onboarding history", error=str(e), user_id=user_id)
            return []