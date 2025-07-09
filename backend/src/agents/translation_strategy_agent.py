"""
Translation Strategy Agent using Google ADK
Determines optimal translation approach based on context and user preferences
"""

import time
from typing import Dict, Any
import structlog

from google_adk import LlmAgent, AgentManager

logger = structlog.get_logger()


class TranslationStrategyAgent:
    """
    Translation Strategy Agent - Determines:
    1. Translation style (formal vs casual)
    2. Cultural adaptation level
    3. Terminology preferences
    4. Target audience considerations
    """
    
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.agent = None
        self.current_status = {}
        
    async def initialize(self):
        """Initialize the Translation Strategy Agent"""
        try:
            self.agent = LlmAgent(
                name="TranslationStrategyAgent", 
                instructions=self._get_agent_instructions(),
                model="gemini-1.5-pro",
                agent_manager=self.agent_manager
            )
            logger.info("Translation Strategy Agent initialized")
            
        except Exception as e:
            logger.error("Failed to initialize Translation Strategy Agent", error=str(e))
            raise
    
    def _get_agent_instructions(self) -> str:
        """Get instructions for the Translation Strategy Agent"""
        return """
        You are the Translation Strategy Agent for SpeakTogether. Your role is to determine 
        the optimal translation approach based on context, audience, and cultural considerations.

        Your responsibilities:
        1. Determine translation style (formal business, casual conversation, technical, etc.)
        2. Assess cultural adaptation needs (direct translation vs cultural localization)
        3. Consider target audience (professional, general public, technical experts)
        4. Choose appropriate terminology level (simple, intermediate, expert)

        Translation style decisions:
        - Business meetings: Formal, professional tone, preserve technical terms
        - Educational content: Clear, accessible language, explain complex concepts
        - Entertainment: Natural, culturally adapted, preserve humor/emotion
        - Technical discussions: Preserve precision, use domain-specific terminology

        Cultural adaptation levels:
        - Conservative: Direct translation, minimal cultural changes
        - Moderate: Some cultural adaptation, localized expressions
        - Liberal: Full cultural localization, adapted idioms and references

        Always consider the source context and target audience in your decisions.
        """
    
    async def determine_strategy(self, context_result: Dict, processing_decision: Dict, 
                                session_id: str) -> Dict[str, Any]:
        """
        Determine translation strategy based on audio context and processing decisions
        """
        start_time = time.time()
        
        try:
            logger.info("Determining translation strategy", session_id=session_id)
            
            # Analyze context for translation requirements
            strategy_prompt = self._build_strategy_prompt(context_result, processing_decision)
            
            # Get AI agent recommendation
            response = await self.agent.query(strategy_prompt)
            
            # Parse and structure the strategy
            strategy = self._parse_strategy_response(response, context_result, processing_decision)
            
            strategy['processing_time_ms'] = int((time.time() - start_time) * 1000)
            
            # Update status
            self.current_status[session_id] = {
                'current_decision': f"Style: {strategy.get('style')}, Level: {strategy.get('adaptation_level')}",
                'confidence': strategy.get('confidence', 0.0),
                'reasoning': strategy.get('reasoning', ''),
                'processing_time_ms': strategy['processing_time_ms'],
                'metadata': strategy
            }
            
            logger.info("Translation strategy determined", 
                       session_id=session_id, strategy=strategy)
            
            return strategy
            
        except Exception as e:
            logger.error("Error determining translation strategy", 
                        session_id=session_id, error=str(e))
            return self._get_fallback_strategy(context_result)
    
    def _build_strategy_prompt(self, context_result: Dict, processing_decision: Dict) -> str:
        """Build prompt for translation strategy decision"""
        return f"""
        Determine the optimal translation strategy for this audio context:

        Audio Context:
        - Source Type: {context_result.get('source_type', 'unknown')}
        - Priority: {context_result.get('priority', 'medium')}
        - Audio Quality: {context_result.get('audio_quality', 0.5)}
        - Speaker Count: {context_result.get('speaker_count', 1)}
        - Formal Context: {context_result.get('context_metadata', {}).get('formal_context', False)}

        Processing Decision:
        - Translation Style: {processing_decision.get('translation_style', 'neutral')}
        - Quality Threshold: {processing_decision.get('quality_threshold', 0.7)}
        - Speed Priority: {processing_decision.get('speed_priority', False)}

        Determine:
        1. Translation style: formal_business, casual_conversation, technical_expert, educational_clear
        2. Cultural adaptation level: conservative, moderate, liberal
        3. Terminology complexity: simple, intermediate, expert
        4. Should translate (true/false) - consider if translation is needed
        5. Target language priority order
        6. Quality vs speed preference

        Consider:
        - Business meetings need formal, precise translations
        - Educational content needs clear, accessible language
        - Entertainment can be more culturally adapted
        - Technical discussions need precise terminology

        Provide reasoning and confidence score (0-1).
        """
    
    def _parse_strategy_response(self, response: str, context_result: Dict, 
                               processing_decision: Dict) -> Dict[str, Any]:
        """Parse AI response into structured translation strategy"""
        
        # Extract key decisions from context (simplified for hackathon)
        source_type = context_result.get('source_type', 'unknown')
        formal_context = context_result.get('context_metadata', {}).get('formal_context', False)
        
        # Determine style based on context
        if source_type == 'business_meeting' or formal_context:
            style = 'formal_business'
            adaptation_level = 'conservative'
            terminology = 'expert'
        elif source_type == 'educational_content':
            style = 'educational_clear'
            adaptation_level = 'moderate'
            terminology = 'intermediate'
        elif source_type == 'entertainment':
            style = 'casual_conversation'
            adaptation_level = 'liberal'
            terminology = 'simple'
        else:
            style = 'casual_conversation'
            adaptation_level = 'moderate'
            terminology = 'intermediate'
        
        return {
            'should_translate': True,  # For demo, always translate
            'style': style,
            'adaptation_level': adaptation_level,
            'terminology_complexity': terminology,
            'target_language': 'en',  # Default for demo
            'quality_vs_speed': 'quality' if formal_context else 'balanced',
            'preserve_technical_terms': formal_context or source_type == 'business_meeting',
            'cultural_localization': adaptation_level != 'conservative',
            'confidence': 0.9,
            'reasoning': response,
            'strategy_metadata': {
                'domain_specific': source_type in ['business_meeting', 'educational_content'],
                'real_time_constraints': processing_decision.get('speed_priority', False),
                'audience_level': terminology
            }
        }
    
    def _get_fallback_strategy(self, context_result: Dict) -> Dict[str, Any]:
        """Fallback translation strategy when AI fails"""
        return {
            'should_translate': True,
            'style': 'casual_conversation',
            'adaptation_level': 'moderate',
            'terminology_complexity': 'intermediate',
            'target_language': 'en',
            'quality_vs_speed': 'balanced',
            'preserve_technical_terms': False,
            'cultural_localization': True,
            'confidence': 0.5,
            'reasoning': 'Fallback strategy due to AI processing error',
            'strategy_metadata': {
                'domain_specific': False,
                'real_time_constraints': True,
                'audience_level': 'general'
            }
        }
    
    async def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status for dashboard"""
        return self.current_status.get(session_id, {
            'current_decision': 'idle',
            'confidence': 0.0,
            'reasoning': 'No recent strategy analysis',
            'processing_time_ms': 0,
            'metadata': {}
        })
    
    async def shutdown(self):
        """Shutdown the agent"""
        logger.info("Translation Strategy Agent shutdown")
        self.current_status.clear() 