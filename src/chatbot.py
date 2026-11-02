"""
Sentinel Chatbot - Unified Production Chatbot Engine.

Integrates all 6 enterprise subsystems:
1. Multilingual Sentiment Analysis & Dynamic Escalation
2. Structured Support Ticket Generation & SLA Lifecycle
3. Knowledge Base Production Pipeline & Quality Gates
4. RAG-Based Knowledge Assistant & Temporal Policy Resolution
5. Multimodal File Processing & Safety Validation
6. Multilingual Conversational Memory & Session Management
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .core.config.settings import get_settings, Settings
from .core.models.data_models import (
    AccessLevel,
    ConversationContext,
    EscalationRecord,
    FileProcessingResult,
    KnowledgeDocument,
    Message,
    Priority,
    RAGResult,
    SentimentResult,
    SentimentType,
    SessionState,
    SupportTicket,
)
from .core.utils.helpers import TimeProvider, get_logger, mask_sensitive_data

# Subsystems
from .knowledge_pipeline import (
    AccessController,
    DocumentProcessor,
    HealthChecker,
    PipelineMonitor,
    QualityTester,
    RetryManager,
    UpdateScheduler,
    VersionManager,
)
from .multilingual import (
    ContextManager,
    InputProcessor,
    LanguageDetector,
    SessionManager,
    SimpleTranslator,
)
from .multimodal import (
    BackgroundQueue,
    DataExtractor,
    FileValidator,
    MultimodalProcessor,
    OCREngine,
    RetentionManager,
)
from .rag import (
    AnswerGenerator,
    DocumentRetriever,
    DocumentStore,
    PolicyResolver,
    SafetyChecker,
)
from .sentiment import (
    EscalationManager,
    SentimentAnalyzer,
    ToneAdjuster,
)
from .tickets import (
    DuplicateDetector,
    HandoffManager,
    PriorityCalculator,
    SLAManager,
    TicketCreator,
    TicketRouter,
)

logger = get_logger("sentinel.engine")


class SentinelChatbot:
    """
    Unified enterprise customer support engine that wires together
    all 6 subsystems for real-time customer interaction and operational safety.
    """

    def __init__(self, settings: Optional[Settings] = None, seed_default_docs: bool = True) -> None:
        self.settings = settings or get_settings()

        # Component 1: Sentiment Analysis & Escalation
        self.sentiment_analyzer = SentimentAnalyzer(settings=self.settings)
        self.escalation_manager = EscalationManager(settings=self.settings)
        self.tone_adjuster = ToneAdjuster()

        # Component 2: Ticket Management & SLA
        self.ticket_creator = TicketCreator(settings=self.settings)
        self.priority_calculator = PriorityCalculator(settings=self.settings)
        self.ticket_router = TicketRouter(settings=self.settings)
        self.sla_manager = SLAManager(settings=self.settings)
        self.duplicate_detector = DuplicateDetector()
        self.handoff_manager = HandoffManager()
        self.tickets: List[SupportTicket] = []

        # Component 3: Knowledge Base Pipeline
        self.doc_processor = DocumentProcessor(settings=self.settings)
        self.version_manager = VersionManager(settings=self.settings)
        self.quality_tester = QualityTester(settings=self.settings)
        self.update_scheduler = UpdateScheduler(settings=self.settings)
        self.retry_manager = RetryManager(settings=self.settings)
        self.health_checker = HealthChecker(settings=self.settings)
        self.access_controller = AccessController()
        self.monitor = PipelineMonitor(settings=self.settings)

        # Component 4: RAG Knowledge Assistant
        self.doc_store = DocumentStore()
        self.policy_resolver = PolicyResolver()
        self.safety_checker = SafetyChecker()
        self.retriever = DocumentRetriever(
            document_store=self.doc_store,
            policy_resolver=self.policy_resolver,
            safety_checker=self.safety_checker,
        )
        self.answer_generator = AnswerGenerator(safety_checker=self.safety_checker)

        # Component 5: Multimodal Processing
        self.file_validator = FileValidator()
        self.ocr_engine = OCREngine()
        self.data_extractor = DataExtractor()
        self.bg_queue = BackgroundQueue()
        self.retention_manager = RetentionManager()
        self.multimodal_processor = MultimodalProcessor(
            config=self.settings.multimodal,
            validator=self.file_validator,
            ocr_engine=self.ocr_engine,
            extractor=self.data_extractor,
            queue=self.bg_queue,
            retention_manager=self.retention_manager,
        )

        # Component 6: Multilingual & Session Management
        self.lang_detector = LanguageDetector(config=self.settings.language)
        self.translator = SimpleTranslator()
        self.context_manager = ContextManager()
        self.session_manager = SessionManager(config=self.settings.session)
        self.input_processor = InputProcessor(config=self.settings.language, language_detector=self.lang_detector)

        if seed_default_docs:
            self.seed_default_knowledge()

        logger.info("Sentinel Chatbot Engine initialized successfully.")

    def seed_default_knowledge(self) -> None:
        """Seed foundational knowledge documents into DocumentStore if empty."""
        if len(self.doc_store._documents) > 0:
            return

        docs = [
            KnowledgeDocument(
                id="kb-war-2025",
                title="Hardware Warranty Policy 2025-2026",
                product="UltraLaptop",
                region="global",
                access_level=AccessLevel.PUBLIC,
                version=2,
                effective_date=datetime(2025, 1, 1),
                expiry_date=datetime(2026, 12, 31),
                content=(
                    "UltraLaptop models include a 2-year premium on-site warranty covering hardware defects "
                    "and accidental damage protection with a $0 deductible."
                ),
            ),
            KnowledgeDocument(
                id="kb-war-2024",
                title="Hardware Warranty Policy 2024",
                product="UltraLaptop",
                region="global",
                access_level=AccessLevel.PUBLIC,
                version=1,
                effective_date=datetime(2024, 1, 1),
                expiry_date=datetime(2024, 12, 31),
                content=(
                    "UltraLaptop 2024 models include a 1-year basic replacement warranty covering manufacturer "
                    "defects only. Accidental liquid and drop damage are not covered under standard terms."
                ),
            ),
            KnowledgeDocument(
                id="kb-ret-2026",
                title="Global Return and Refund Policy",
                product="General",
                region="global",
                access_level=AccessLevel.PUBLIC,
                version=1,
                effective_date=datetime(2025, 6, 1),
                expiry_date=None,
                content=(
                    "Customers may return items within 30 days of delivery for a full refund to the original payment method. "
                    "Items must be in original condition with packaging. Refunds are processed within 3 to 5 business days."
                ),
            ),
            KnowledgeDocument(
                id="kb-sec-2026",
                title="Account Security & Compromise Protocol",
                product="General",
                region="global",
                access_level=AccessLevel.INTERNAL,
                version=1,
                effective_date=datetime(2025, 1, 1),
                expiry_date=None,
                content=(
                    "When an account compromise or unauthorized access is reported, the security team must immediately "
                    "suspend active sessions, initiate password resets, and audit the last 48 hours of transactions."
                ),
            ),
            KnowledgeDocument(
                id="kb-settle-playbook",
                title="Executive Settlement Playbook",
                product="All",
                region="global",
                access_level=AccessLevel.CONFIDENTIAL,
                version=1,
                effective_date=datetime(2025, 1, 1),
                expiry_date=None,
                content=(
                    "Authorized directors may settle legal claims up to $100,000 without board approval under strict NDA."
                ),
            ),
        ]
        for doc in docs:
            self.doc_store.add_document(doc)


    def handle_message(
        self,
        customer_id: str,
        raw_text: str,
        reference_date: Optional[datetime] = None,
        user_access_level: str = "public",
        uploaded_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        End-to-end message handling workflow orchestrating all 6 subsystems.
        """
        now = TimeProvider.now()

        # 1. Session Management (Restore if <24h, expire if >30min)
        session = self.session_manager.get_active_session(customer_id)
        if not session:
            session = self.session_manager.restore_session(customer_id)
            if not session:
                session = self.session_manager.create_session(customer_id)
        else:
            self.session_manager.update_activity(session.session_id)

        session_id = session.session_id

        # 2. Input Processing & Typo Correction
        processed_input = self.input_processor.process(raw_text, session_id=session_id)
        cleaned_text = processed_input["cleaned_text"]
        detected_lang = processed_input["detected_language"]

        # Ambiguous / Low confidence input -> immediate clarification
        if processed_input["needs_clarification"]:
            clarification_reply = processed_input["clarification_message"]
            return {
                "session_id": session_id,
                "reply": clarification_reply,
                "needs_clarification": True,
                "sentiment": SentimentType.NEUTRAL.value,
                "confidence": processed_input["confidence"],
                "is_high_risk": False,
                "escalated": False,
                "ticket": None,
                "ticket_id": None,
                "assigned_team": None,
                "sources": [],
                "file_result": None,
            }

        # Create incoming Message object
        user_msg = Message(
            session_id=session_id,
            customer_id=customer_id,
            content=cleaned_text,
            language=detected_lang,
            timestamp=now,
            is_customer=True,
        )
        self.context_manager.add_message(session_id, user_msg)
        session.messages.append(user_msg)

        # 3. Multimodal File Handling (if attachment included)
        file_result: Optional[FileProcessingResult] = None
        if uploaded_file:
            file_result = self.multimodal_processor.process_file(uploaded_file, message=user_msg)
            if file_result.queued_for_background:
                return {
                    "session_id": session_id,
                    "reply": file_result.metadata.get("notification", "Processing in background..."),
                    "file_status": file_result.status.value,
                    "escalated": False,
                    "ticket": None,
                }
            if not file_result.is_safe:
                return {
                    "session_id": session_id,
                    "reply": "The uploaded file could not be verified due to safety policy violations.",
                    "file_status": "rejected",
                    "escalated": False,
                    "ticket": None,
                }

        # 4. Multilingual Sentiment Analysis & Escalation Check
        ctx = ConversationContext(
            session_id=session_id,
            customer_id=customer_id,
            messages=self.context_manager.get_context(session_id),
            started_at=session.started_at,
        )
        sentiment_res = self.sentiment_analyzer.analyze(user_msg, ctx)
        ctx.sentiment_history.append(sentiment_res)

        escalation_record: Optional[EscalationRecord] = self.escalation_manager.check_escalation(ctx, sentiment_res)

        # 5. RAG Knowledge Retrieval & Conversational Handling
        import re
        norm_text = cleaned_text.strip().lower()
        is_greeting = bool(re.match(r"^(hi|hello|hey|howdy|greetings|good\s+(morning|afternoon|evening|day))[\s!.,?]*$", norm_text))
        is_capabilities_query = bool(re.match(r"^(what\s+can\s+you\s+do|who\s+are\s+you|help(\s+me)?|what\s+are\s+your\s+capabilities)[\s!.,?]*$", norm_text))
        is_closing = bool(re.match(r"^(thanks|thank\s+you|thx|many\s+thanks|bye|goodbye|have\s+a\s+good\s+day)[\s!.,?]*$", norm_text))

        if (is_greeting or is_capabilities_query) and not escalation_record and not sentiment_res.is_high_risk:
            base_answer = (
                "Hello! I am Sentinel, your AI Customer Support Assistant.\n\n"
                "I can help you with:\n"
                "• Hardware warranty terms and coverage details\n"
                "• Return, replacement, and refund policies\n"
                "• Billing inquiries and payment issues\n"
                "• Account security, password resets, and access protection\n"
                "• Structured escalation to specialized support teams\n\n"
                "How can I assist you today?"
            )
            rag_res = RAGResult(
                answer=base_answer,
                confidence=1.0,
                sources=[],
                is_ambiguous=False,
                requires_clarification=False,
                clarification_message="",
            )
        elif is_closing and not escalation_record and not sentiment_res.is_high_risk:
            base_answer = (
                "You're very welcome! If you have any further questions or need additional support, "
                "feel free to reach out anytime. Have a wonderful day!"
            )
            rag_res = RAGResult(
                answer=base_answer,
                confidence=1.0,
                sources=[],
                is_ambiguous=False,
                requires_clarification=False,
                clarification_message="",
            )
        else:
            retrieved_docs = self.retriever.retrieve(
                query=cleaned_text,
                user_access_level=user_access_level,
                reference_date=reference_date,
            )
            rag_res = self.answer_generator.generate_answer(cleaned_text, retrieved_docs)
            base_answer = rag_res.answer

        # 6. Dynamic Tone Adjustment (preserving business policies)
        final_response = self.tone_adjuster.adjust_response(base_answer, sentiment_res, ctx)

        # Translate back if non-English and response was generated in English
        if detected_lang != "en":
            # Translate common phrases
            translated_response = self.translator.translate(final_response, "en", detected_lang)
            if translated_response and translated_response != final_response:
                final_response = translated_response

        # 7. Ticket Generation (if escalated or high risk)
        ticket: Optional[SupportTicket] = None
        if escalation_record:
            ticket = self.ticket_creator.create_from_conversation(ctx)
            # Calculate priority
            priority, p_score = self.priority_calculator.calculate(ticket, sentiment_res, ctx)
            ticket.priority = priority
            ticket.priority_score = p_score

            # SLA deadline calculation
            self.sla_manager.calculate_deadline(ticket)

            # Routing to team & agent
            team, agent = self.ticket_router.route(ticket)
            ticket.assigned_team = team
            ticket.assigned_agent = agent

            # Duplicate check
            duplicates = self.duplicate_detector.find_duplicates(ticket, self.tickets)
            if duplicates:
                ticket.duplicate_of = duplicates[0].id
                ticket.related_tickets = [d.id for d in duplicates]

            # Generate masked handoff summary
            self.handoff_manager.generate_summary(ticket, ctx)
            self.tickets.append(ticket)

            final_response += (
                f"\n\n[Notice: Your inquiry has been escalated to {team.upper()} (Ticket #{ticket.id[:8]}). "
                f"Queue: {escalation_record.queue_type.upper()}]"
            )

        bot_msg = Message(
            session_id=session_id,
            customer_id=customer_id,
            content=final_response,
            language=detected_lang,
            timestamp=TimeProvider.now(),
            is_customer=False,
        )
        self.context_manager.add_message(session_id, bot_msg)
        session.messages.append(bot_msg)

        return {
            "session_id": session_id,
            "reply": final_response,
            "sentiment": sentiment_res.sentiment.value,
            "confidence": sentiment_res.confidence,
            "is_high_risk": sentiment_res.is_high_risk,
            "escalated": escalation_record is not None,
            "escalation_reason": escalation_record.reason.value if escalation_record else None,
            "ticket_id": ticket.id if ticket else None,
            "assigned_team": ticket.assigned_team if ticket else None,
            "sources": rag_res.sources,
            "file_result": file_result,
        }
