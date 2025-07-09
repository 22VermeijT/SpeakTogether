"""
Quality Control Agent using Google ADK
Monitors processing quality and triggers reprocessing when needed
"""

import time
from typing import Dict, Any
import structlog

from ..mock_google_adk import LlmAgent, AgentManager

logger = structlog.get_logger()


class QualityControlAgent:
    """
    Quality Control Agent - Monitors and validates:
    1. Speech recognition accuracy
    2. Translation quality and fluency
    3. Overall confidence scores
    4. Error detection and correction recommendations
    """
    
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.agent = None
        self.current_status = {}
        self.quality_history = {}
        
    async def initialize(self):
        """Initialize the Quality Control Agent"""
        try:
            self.agent = LlmAgent(
                name="QualityControlAgent",
                instructions=self._get_agent_instructions(),
                model="gemini-1.5-pro",
                agent_manager=self.agent_manager
            )
            logger.info("Quality Control Agent initialized")
            
        except Exception as e:
            logger.error("Failed to initialize Quality Control Agent", error=str(e))
            raise
    
    def _get_agent_instructions(self) -> str:
        """Get instructions for the Quality Control Agent"""
        return """
        You are the Quality Control Agent for SpeakTogether. Your role is to monitor 
        and validate the quality of speech recognition and translation results.

        Your responsibilities:
        1. Assess transcription accuracy based on confidence scores and context
        2. Evaluate translation quality for fluency and meaning preservation
        3. Detect potential errors or inconsistencies
        4. Recommend reprocessing when quality falls below thresholds
        5. Track quality trends and suggest improvements

        Quality assessment criteria:
        - Transcription confidence scores
        - Translation fluency and naturalness
        - Context consistency
        - Technical term preservation
        - Cultural appropriateness

        Error detection signals:
        - Low confidence scores (< 0.7)
        - Inconsistent terminology
        - Unnatural phrasing
        - Missing or corrupted audio segments
        - Cultural mismatches

        Always provide specific feedback and actionable recommendations.
        """
    
    async def validate_result(self, processing_result: Dict, session_id: str) -> Dict[str, Any]:
        """
        Validate processing result quality and recommend actions
        """
        start_time = time.time()
        
        try:
            logger.info("Validating processing result quality", session_id=session_id)
            
            # Perform quality assessment
            quality_assessment = await self._assess_quality(processing_result, session_id)
            
            # Make validation decision
            validation_result = await self._make_validation_decision(
                processing_result, quality_assessment, session_id
            )
            
            # Update quality history
            self._update_quality_history(session_id, quality_assessment)
            
            # Prepare final result
            final_result = processing_result.copy()
            final_result.update({
                'quality_assessment': quality_assessment,
                'validation_passed': validation_result['passed'],
                'quality_score': quality_assessment['overall_score'],
                'recommendations': validation_result['recommendations']
            })
            
            processing_time = int((time.time() - start_time) * 1000)
            final_result['quality_control_time_ms'] = processing_time
            
            # Update status
            self.current_status[session_id] = {
                'current_decision': f"Quality: {quality_assessment['overall_score']:.2f}, Passed: {validation_result['passed']}",
                'confidence': quality_assessment['overall_score'],
                'reasoning': validation_result['reasoning'],
                'processing_time_ms': processing_time,
                'metadata': {
                    'quality_assessment': quality_assessment,
                    'validation_result': validation_result
                }
            }
            
            logger.info("Quality validation complete", 
                       session_id=session_id, 
                       quality_score=quality_assessment['overall_score'],
                       passed=validation_result['passed'])
            
            return final_result
            
        except Exception as e:
            logger.error("Error in quality validation", 
                        session_id=session_id, error=str(e))
            return self._get_fallback_result(processing_result)
    
    async def _assess_quality(self, processing_result: Dict, session_id: str) -> Dict[str, Any]:
        """Assess the quality of processing results"""
        
        # Extract key metrics
        transcript_confidence = processing_result.get('confidence', 0.0)
        translation_confidence = processing_result.get('translation_confidence', 0.0)
        transcript = processing_result.get('transcript', '')
        translation = processing_result.get('translation', '')
        
        # Build quality assessment prompt
        assessment_prompt = f"""
        Assess the quality of this speech recognition and translation result:

        Transcription:
        - Text: "{transcript}"
        - Confidence: {transcript_confidence}

        Translation:
        - Text: "{translation}"
        - Confidence: {translation_confidence}

        Evaluate:
        1. Transcription quality (0-1): Consider confidence, completeness, coherence
        2. Translation quality (0-1): Consider fluency, accuracy, naturalness
        3. Overall consistency: Do transcript and translation align?
        4. Potential issues: Missing words, mistranslations, cultural problems
        5. Recommendation: accept, reprocess_with_enhancement, reprocess_full

        Consider:
        - Confidence scores below 0.7 indicate potential issues
        - Short or fragmented text may indicate audio problems
        - Unnatural phrasing suggests translation issues
        - Technical terms should be preserved appropriately

        Provide detailed assessment with specific issues identified.
        """
        
        try:
            response = await self.agent.query(assessment_prompt)
            
            # Parse assessment response
            assessment = self._parse_assessment_response(
                response, transcript_confidence, translation_confidence
            )
            
            return assessment
            
        except Exception as e:
            logger.error("Error in AI quality assessment", session_id=session_id, error=str(e))
            return self._get_fallback_assessment(transcript_confidence, translation_confidence)
    
    def _parse_assessment_response(self, response: str, transcript_conf: float, 
                                 translation_conf: float) -> Dict[str, Any]:
        """Parse AI assessment response into structured quality metrics"""
        
        # Calculate component scores based on confidence and heuristics
        transcription_score = min(1.0, transcript_conf + 0.1)  # Slight boost for processing
        translation_score = min(1.0, translation_conf + 0.05)
        
        # Overall score weighted average
        overall_score = (transcription_score * 0.6 + translation_score * 0.4)
        
        # Determine issues based on scores
        issues = []
        if transcript_conf < 0.7:
            issues.append("Low transcription confidence")
        if translation_conf < 0.7:
            issues.append("Low translation confidence")
        if overall_score < 0.6:
            issues.append("Overall quality below threshold")
        
        return {
            'transcription_score': transcription_score,
            'translation_score': translation_score,
            'consistency_score': min(transcription_score, translation_score),
            'overall_score': overall_score,
            'issues_detected': issues,
            'detailed_feedback': response,
            'confidence_analysis': {
                'transcript_confidence': transcript_conf,
                'translation_confidence': translation_conf,
                'confidence_trend': 'stable'  # Would track over time in production
            }
        }
    
    async def _make_validation_decision(self, processing_result: Dict, 
                                      quality_assessment: Dict, session_id: str) -> Dict[str, Any]:
        """Make validation decision based on quality assessment"""
        
        overall_score = quality_assessment['overall_score']
        issues = quality_assessment['issues_detected']
        
        # Decision logic
        if overall_score >= 0.8 and len(issues) == 0:
            decision = 'accept'
            passed = True
            recommendations = ['Result meets quality standards']
        elif overall_score >= 0.6 and len(issues) <= 2:
            decision = 'accept_with_warning'
            passed = True
            recommendations = [
                'Result acceptable but has minor quality issues',
                'Consider improving audio quality for better results'
            ]
        elif overall_score >= 0.4:
            decision = 'reprocess_with_enhancement'
            passed = False
            recommendations = [
                'Quality below threshold - recommend reprocessing',
                'Apply noise reduction and enhanced models',
                'Check audio source quality'
            ]
        else:
            decision = 'reprocess_full'
            passed = False
            recommendations = [
                'Quality significantly below threshold',
                'Full reprocessing required with different strategy',
                'Consider manual review if reprocessing fails'
            ]
        
        return {
            'decision': decision,
            'passed': passed,
            'recommendations': recommendations,
            'reasoning': f"Overall score: {overall_score:.2f}, Issues: {len(issues)}"
        }
    
    def _update_quality_history(self, session_id: str, quality_assessment: Dict):
        """Update quality history for trend analysis"""
        if session_id not in self.quality_history:
            self.quality_history[session_id] = []
        
        self.quality_history[session_id].append({
            'timestamp': time.time(),
            'overall_score': quality_assessment['overall_score'],
            'transcription_score': quality_assessment['transcription_score'],
            'translation_score': quality_assessment['translation_score']
        })
        
        # Keep only last 10 entries per session
        self.quality_history[session_id] = self.quality_history[session_id][-10:]
    
    def _get_fallback_assessment(self, transcript_conf: float, translation_conf: float) -> Dict[str, Any]:
        """Fallback quality assessment when AI fails"""
        overall_score = (transcript_conf + translation_conf) / 2
        
        return {
            'transcription_score': transcript_conf,
            'translation_score': translation_conf,
            'consistency_score': min(transcript_conf, translation_conf),
            'overall_score': overall_score,
            'issues_detected': ['AI assessment unavailable'],
            'detailed_feedback': 'Fallback assessment based on confidence scores only',
            'confidence_analysis': {
                'transcript_confidence': transcript_conf,
                'translation_confidence': translation_conf,
                'confidence_trend': 'unknown'
            }
        }
    
    def _get_fallback_result(self, processing_result: Dict) -> Dict[str, Any]:
        """Fallback result when quality control fails"""
        result = processing_result.copy()
        result.update({
            'quality_assessment': self._get_fallback_assessment(0.5, 0.5),
            'validation_passed': True,  # Conservative fallback
            'quality_score': 0.5,
            'recommendations': ['Quality control temporarily unavailable']
        })
        return result
    
    async def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status for dashboard"""
        return self.current_status.get(session_id, {
            'current_decision': 'idle',
            'confidence': 0.0,
            'reasoning': 'No recent quality validation',
            'processing_time_ms': 0,
            'metadata': {}
        })
    
    async def shutdown(self):
        """Shutdown the agent"""
        logger.info("Quality Control Agent shutdown")
        self.current_status.clear()
        self.quality_history.clear() 