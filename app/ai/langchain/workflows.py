"""
LangGraph workflows for employee onboarding processes with hybrid RAG integration.
"""

from typing import Any, Dict, List, Optional, TypedDict
from enum import Enum

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.documents import Document

from app.core.logging import get_logger
from app.ai.langchain.llm_manager import onboarding_llm
from app.ai.langchain.vector_store import vector_store
from app.ai.rag.hybrid_rag_service import hybrid_rag_service
from app.ai.rag.vector_cache_service import vector_cache_service

logger = get_logger("ai.workflows")


class OnboardingStage(Enum):
    """Onboarding stages."""
    WELCOME = "welcome"
    PROFILE_SETUP = "profile_setup"
    DOCUMENT_REVIEW = "document_review"
    QUESTIONS_ANSWERS = "questions_answers"
    COMPLETION = "completion"


class OnboardingState(TypedDict):
    """State for onboarding workflow."""
    user_id: int
    telegram_id: int
    stage: str
    user_info: Dict[str, Any]
    messages: List[BaseMessage]
    documents_reviewed: List[str]
    questions_asked: List[str]
    completion_score: float
    language: str
    context: Optional[str]
    next_action: Optional[str]


class OnboardingWorkflow:
    """LangGraph workflow for employee onboarding."""
    
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the onboarding workflow graph."""
        workflow = StateGraph(OnboardingState)
        
        # Add nodes
        workflow.add_node("welcome", self._welcome_node)
        workflow.add_node("profile_setup", self._profile_setup_node)
        workflow.add_node("document_review", self._document_review_node)
        workflow.add_node("questions_answers", self._questions_answers_node)
        workflow.add_node("completion", self._completion_node)
        
        # Add edges
        workflow.set_entry_point("welcome")
        
        workflow.add_conditional_edges(
            "welcome",
            self._route_from_welcome,
            {
                "profile_setup": "profile_setup",
                "document_review": "document_review",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "profile_setup",
            self._route_from_profile,
            {
                "document_review": "document_review",
                "questions_answers": "questions_answers",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "document_review",
            self._route_from_documents,
            {
                "questions_answers": "questions_answers",
                "completion": "completion",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "questions_answers",
            self._route_from_qa,
            {
                "document_review": "document_review",
                "completion": "completion",
                "end": END
            }
        )
        
        workflow.add_edge("completion", END)
        
        return workflow.compile()
    
    async def _welcome_node(self, state: OnboardingState) -> OnboardingState:
        """Welcome node - greet new employee."""
        logger.info("Processing welcome node", user_id=state["user_id"])
        
        user_info = state["user_info"]
        welcome_message = await onboarding_llm.generate_welcome_message(
            user_name=user_info.get("name", "Новый сотрудник"),
            position=user_info.get("position", ""),
            department=user_info.get("department", ""),
            language=state["language"]
        )
        
        state["messages"].append(SystemMessage(content=welcome_message))
        state["stage"] = OnboardingStage.WELCOME.value
        state["next_action"] = "profile_setup"
        
        return state
    
    async def _profile_setup_node(self, state: OnboardingState) -> OnboardingState:
        """Profile setup node - collect user information."""
        logger.info("Processing profile setup node", user_id=state["user_id"])
        
        # Check if profile is complete
        required_fields = ["name", "position", "department", "start_date"]
        missing_fields = [
            field for field in required_fields
            if not state["user_info"].get(field)
        ]
        
        if missing_fields:
            # Request missing information
            if state["language"] == "ru":
                message = f"Пожалуйста, предоставьте следующую информацию: {', '.join(missing_fields)}"
            elif state["language"] == "en":
                message = f"Please provide the following information: {', '.join(missing_fields)}"
            else:
                message = f"يرجى تقديم المعلومات التالية: {', '.join(missing_fields)}"
            
            state["messages"].append(SystemMessage(content=message))
            state["next_action"] = "profile_setup"
        else:
            # Profile complete, move to documents
            state["stage"] = OnboardingStage.PROFILE_SETUP.value
            state["next_action"] = "document_review"
        
        return state
    
    async def _document_review_node(self, state: OnboardingState) -> OnboardingState:
        """Document review node - provide relevant documents."""
        logger.info("Processing document review node", user_id=state["user_id"])
        
        user_info = state["user_info"]
        
        # Search for relevant documents based on user profile
        search_queries = [
            f"{user_info.get('position', '')} responsibilities",
            f"{user_info.get('department', '')} procedures",
            "company policies",
            "employee handbook"
        ]
        
        relevant_docs = []
        for query in search_queries:
            if query.strip():
                try:
                    results = await vector_store.similarity_search(
                        query=query,
                        k=3,
                        filter_conditions={
                            "document_type": ["policy", "handbook", "procedure"],
                            "department": [user_info.get("department", ""), "general"]
                        }
                    )
                    relevant_docs.extend([doc for doc, score in results])
                except Exception as e:
                    logger.error("Document search failed", error=str(e), query=query)
        
        # Generate document summary
        if relevant_docs:
            doc_summaries = []
            for doc in relevant_docs[:5]:  # Limit to top 5
                doc_summaries.append(f"- {doc.metadata.get('title', 'Документ')}: {doc.page_content[:200]}...")
            
            if state["language"] == "ru":
                message = "Вот документы, которые важно изучить:\n\n" + "\n".join(doc_summaries)
            elif state["language"] == "en":
                message = "Here are important documents to review:\n\n" + "\n".join(doc_summaries)
            else:
                message = "إليك الوثائق المهمة للمراجعة:\n\n" + "\n".join(doc_summaries)
            
            state["context"] = "\n".join([doc.page_content for doc in relevant_docs])
        else:
            if state["language"] == "ru":
                message = "Документы для вашей должности готовятся. Пока можете задать вопросы."
            elif state["language"] == "en":
                message = "Documents for your position are being prepared. You can ask questions in the meantime."
            else:
                message = "يتم إعداد الوثائق لمنصبك. يمكنك طرح الأسئلة في الوقت الحالي."
        
        state["messages"].append(SystemMessage(content=message))
        state["stage"] = OnboardingStage.DOCUMENT_REVIEW.value
        state["documents_reviewed"].extend([doc.metadata.get("title", "") for doc in relevant_docs])
        state["next_action"] = "questions_answers"
        
        return state
    
    async def _questions_answers_node(self, state: OnboardingState) -> OnboardingState:
        """Q&A node - answer user questions using hybrid RAG."""
        logger.info("Processing Q&A node with hybrid RAG", user_id=state["user_id"])
        
        # Get the last user message
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        if not user_messages:
            # No questions yet, prompt for questions
            if state["language"] == "ru":
                message = "Есть ли у вас вопросы о компании, вашей роли или процедурах?"
            elif state["language"] == "en":
                message = "Do you have any questions about the company, your role, or procedures?"
            else:
                message = "هل لديك أي أسئلة حول الشركة أو دورك أو الإجراءات؟"
            
            state["messages"].append(SystemMessage(content=message))
            state["next_action"] = "questions_answers"
            return state
        
        last_question = user_messages[-1].content
        
        # Cache user context for better RAG performance
        await vector_cache_service.cache_user_context(
            user_id=state["user_id"],
            context_data={
                "user_info": state["user_info"],
                "language": state["language"],
                "stage": state["stage"],
                "questions_asked": state["questions_asked"],
                "documents_reviewed": state["documents_reviewed"]
            }
        )
        
        # Use hybrid RAG service for processing
        try:
            rag_result = await hybrid_rag_service.process_query(
                query=last_question,
                user_id=state["user_id"],
                user_info=state["user_info"],
                language=state["language"],
                use_conversation_memory=True
            )
            
            response = rag_result["answer"]
            state["context"] = rag_result.get("context", "")
            
            # Log RAG processing details
            logger.info(
                "Hybrid RAG processing completed",
                user_id=state["user_id"],
                query_complexity=rag_result.get("query_complexity"),
                processing_method=rag_result.get("processing_method"),
                source_docs_count=len(rag_result.get("source_documents", []))
            )
            
        except Exception as e:
            logger.error("Hybrid RAG processing failed, falling back to traditional method", error=str(e))
            
            # Fallback to traditional approach
            try:
                search_results = await vector_store.similarity_search(
                    query=last_question,
                    k=3,
                    score_threshold=0.7
                )
                
                context = "\n".join([doc.page_content for doc, score in search_results])
                if context:
                    state["context"] = context
                
                response = await onboarding_llm.generate_onboarding_response(
                    user_message=last_question,
                    context=state.get("context"),
                    language=state["language"],
                    user_info=state["user_info"]
                )
                
            except Exception as fallback_error:
                logger.error("Fallback processing also failed", error=str(fallback_error))
                
                # Final fallback - simple response
                if state["language"] == "ru":
                    response = "Извините, произошла ошибка при обработке вашего вопроса. Попробуйте переформулировать или обратитесь к HR."
                elif state["language"] == "en":
                    response = "Sorry, there was an error processing your question. Please try rephrasing or contact HR."
                else:
                    response = "عذراً، حدث خطأ في معالجة سؤالك. يرجى إعادة الصياغة أو الاتصال بالموارد البشرية."
        
        state["messages"].append(SystemMessage(content=response))
        state["stage"] = OnboardingStage.QUESTIONS_ANSWERS.value
        state["questions_asked"].append(last_question)
        
        # Check if ready for completion
        if len(state["questions_asked"]) >= 3 and len(state["documents_reviewed"]) >= 2:
            state["next_action"] = "completion"
        else:
            state["next_action"] = "questions_answers"
        
        return state
    
    async def _completion_node(self, state: OnboardingState) -> OnboardingState:
        """Completion node - finalize onboarding."""
        logger.info("Processing completion node", user_id=state["user_id"])
        
        # Calculate completion score
        score = 0.0
        score += min(len(state["documents_reviewed"]) * 20, 40)  # Max 40 for docs
        score += min(len(state["questions_asked"]) * 15, 45)     # Max 45 for questions
        score += 15 if state["user_info"].get("name") else 0     # Profile completeness
        
        state["completion_score"] = score
        
        # Generate completion message
        if state["language"] == "ru":
            message = f"""🎉 Поздравляем! Вы успешно завершили процесс адаптации.
            
Ваш прогресс:
- Изучено документов: {len(state["documents_reviewed"])}
- Задано вопросов: {len(state["questions_asked"])}
- Оценка завершения: {score:.1f}%

Добро пожаловать в команду! Если у вас возникнут вопросы, всегда можете обратиться к HR или вашему руководителю."""
        elif state["language"] == "en":
            message = f"""🎉 Congratulations! You have successfully completed the onboarding process.
            
Your progress:
- Documents reviewed: {len(state["documents_reviewed"])}
- Questions asked: {len(state["questions_asked"])}
- Completion score: {score:.1f}%

Welcome to the team! If you have any questions, you can always contact HR or your manager."""
        else:
            message = f"""🎉 تهانينا! لقد أكملت بنجاح عملية التأهيل.
            
تقدمك:
- الوثائق المراجعة: {len(state["documents_reviewed"])}
- الأسئلة المطروحة: {len(state["questions_asked"])}
- نقاط الإكمال: {score:.1f}%

مرحباً بك في الفريق! إذا كان لديك أي أسئلة، يمكنك دائماً الاتصال بالموارد البشرية أو مديرك."""
        
        state["messages"].append(SystemMessage(content=message))
        state["stage"] = OnboardingStage.COMPLETION.value
        state["next_action"] = None
        
        return state
    
    def _route_from_welcome(self, state: OnboardingState) -> str:
        """Route from welcome node."""
        return state.get("next_action", "end")
    
    def _route_from_profile(self, state: OnboardingState) -> str:
        """Route from profile setup node."""
        return state.get("next_action", "end")
    
    def _route_from_documents(self, state: OnboardingState) -> str:
        """Route from document review node."""
        return state.get("next_action", "end")
    
    def _route_from_qa(self, state: OnboardingState) -> str:
        """Route from Q&A node."""
        return state.get("next_action", "end")
    
    async def run_workflow(self, initial_state: OnboardingState) -> OnboardingState:
        """Run the complete onboarding workflow."""
        try:
            result = await self.graph.ainvoke(initial_state)
            logger.info(
                "Onboarding workflow completed",
                user_id=initial_state["user_id"],
                final_stage=result.get("stage"),
                completion_score=result.get("completion_score", 0)
            )
            return result
        except Exception as e:
            logger.error(
                "Onboarding workflow failed",
                error=str(e),
                user_id=initial_state["user_id"]
            )
            raise


# Global workflow instance
onboarding_workflow = OnboardingWorkflow()