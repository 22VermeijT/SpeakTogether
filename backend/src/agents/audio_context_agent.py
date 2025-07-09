"""
Audio Context Agent using Google ADK
Analyzes audio source type, quality, and determines processing priority
"""

import time
import numpy as np
import librosa
from typing import Dict, Any
import structlog

from google_adk import LlmAgent, AgentManager

logger = structlog.get_logger()


class AudioContextAgent:
    """
    Audio Context Agent - Analyzes incoming audio to determine:
    1. Source type (Zoom, YouTube, Spotify, etc.)
    2. Audio quality and characteristics
    3. Processing priority and recommendations
    """
    
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.agent = None
        self.current_status = {}
        
    async def initialize(self):
        """Initialize the Audio Context Agent"""
        try:
            self.agent = LlmAgent(
                name="AudioContextAgent",
                instructions=self._get_agent_instructions(),
                model="gemini-1.5-pro",
                agent_manager=self.agent_manager
            )
            logger.info("Audio Context Agent initialized")
            
        except Exception as e:
            logger.error("Failed to initialize Audio Context Agent", error=str(e))
            raise
    
    def _get_agent_instructions(self) -> str:
        """Get instructions for the Audio Context Agent"""
        return """
        You are the Audio Context Agent for SpeakTogether. Your role is to analyze incoming 
        audio data and determine the optimal processing approach based on context and quality.

        Your responsibilities:
        1. Identify audio source type (business meeting, entertainment, educational content, etc.)
        2. Assess audio quality (clarity, noise levels, speaker count)
        3. Determine processing priority (high for meetings, medium for education, low for music)
        4. Recommend processing approach (real-time vs batch, enhanced vs standard models)

        Audio source detection criteria:
        - Business meeting: Multiple speakers, formal language, meeting application detected
        - Educational content: Single speaker, structured presentation, educational platforms
        - Entertainment: Music, sound effects, entertainment platforms
        - System notifications: Short duration, system sounds

        Quality assessment factors:
        - Signal-to-noise ratio
        - Speaker clarity and count
        - Audio compression artifacts
        - Background noise levels

        Always provide confidence scores and reasoning for your assessments.
        """
    
    async def analyze_audio(self, audio_data: bytes, session_id: str) -> Dict[str, Any]:
        """
        Analyze audio data to determine context and quality
        Returns analysis results for orchestrator decision-making
        """
        start_time = time.time()
        
        try:
            logger.info("Analyzing audio context", session_id=session_id)
            
            # Perform technical audio analysis
            technical_analysis = await self._perform_technical_analysis(audio_data)
            
            # Use AI agent to interpret context
            context_analysis = await self._analyze_context_with_ai(
                technical_analysis, session_id
            )
            
            # Combine results
            result = {
                **technical_analysis,
                **context_analysis,
                'processing_time_ms': int((time.time() - start_time) * 1000)
            }
            
            # Update current status
            self.current_status[session_id] = {
                'current_decision': f"Source: {result.get('source_type')}, Quality: {result.get('audio_quality'):.2f}",
                'confidence': result.get('confidence', 0.0),
                'reasoning': result.get('reasoning', ''),
                'processing_time_ms': result['processing_time_ms'],
                'metadata': result
            }
            
            logger.info("Audio context analysis complete", 
                       session_id=session_id, result=result)
            
            return result
            
        except Exception as e:
            logger.error("Error in audio context analysis", 
                        session_id=session_id, error=str(e))
            return self._get_fallback_analysis()
    
    async def _perform_technical_analysis(self, audio_data: bytes) -> Dict[str, Any]:
        """Perform technical analysis of audio characteristics"""
        try:
            # Convert bytes to numpy array for analysis
            # This is a simplified version - in production would handle different audio formats
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
            
            # Basic audio characteristics
            analysis = {
                'audio_length': len(audio_array) / 16000,  # Assuming 16kHz sample rate
                'rms_energy': float(np.sqrt(np.mean(audio_array**2))),
                'zero_crossing_rate': self._calculate_zcr(audio_array),
                'spectral_centroid': self._calculate_spectral_centroid(audio_array),
            }
            
            # Derive quality metrics
            analysis.update({
                'audio_quality': self._assess_audio_quality(analysis),
                'noise_level': self._estimate_noise_level(analysis),
                'speaker_count': self._estimate_speaker_count(analysis),
                'signal_type': self._classify_signal_type(analysis)
            })
            
            return analysis
            
        except Exception as e:
            logger.error("Error in technical audio analysis", error=str(e))
            return {
                'audio_quality': 0.5,
                'noise_level': 0.5,
                'speaker_count': 1,
                'signal_type': 'unknown'
            }
    
    def _calculate_zcr(self, audio_array: np.ndarray) -> float:
        """Calculate zero crossing rate"""
        try:
            zcr = librosa.feature.zero_crossing_rate(audio_array)[0]
            return float(np.mean(zcr))
        except:
            return 0.1  # Fallback value
    
    def _calculate_spectral_centroid(self, audio_array: np.ndarray) -> float:
        """Calculate spectral centroid"""
        try:
            spectral_centroid = librosa.feature.spectral_centroid(y=audio_array, sr=16000)[0]
            return float(np.mean(spectral_centroid))
        except:
            return 2000.0  # Fallback value
    
    def _assess_audio_quality(self, analysis: Dict) -> float:
        """Assess overall audio quality (0-1 scale)"""
        # Simplified quality assessment based on technical metrics
        quality_score = 0.8  # Base score
        
        # Adjust based on energy levels
        if analysis['rms_energy'] < 0.01:
            quality_score -= 0.3  # Very low energy
        elif analysis['rms_energy'] > 0.5:
            quality_score -= 0.2  # Potentially clipped
            
        # Adjust based on spectral characteristics
        if analysis['spectral_centroid'] < 500 or analysis['spectral_centroid'] > 8000:
            quality_score -= 0.1  # Poor frequency distribution
            
        return max(0.0, min(1.0, quality_score))
    
    def _estimate_noise_level(self, analysis: Dict) -> float:
        """Estimate background noise level (0-1 scale)"""
        # Simplified noise estimation
        if analysis['rms_energy'] < 0.02:
            return 0.1  # Low noise
        elif analysis['rms_energy'] > 0.1:
            return 0.8  # High noise
        else:
            return 0.3  # Medium noise
    
    def _estimate_speaker_count(self, analysis: Dict) -> int:
        """Estimate number of speakers"""
        # Simplified speaker count estimation
        if analysis['rms_energy'] > 0.05 and analysis['zero_crossing_rate'] > 0.1:
            return 2  # Likely multiple speakers
        else:
            return 1  # Single speaker
    
    def _classify_signal_type(self, analysis: Dict) -> str:
        """Classify type of audio signal"""
        # Simplified signal classification
        if analysis['spectral_centroid'] > 4000:
            return 'speech'
        elif analysis['spectral_centroid'] > 1000:
            return 'mixed'
        else:
            return 'music'
    
    async def _analyze_context_with_ai(self, technical_analysis: Dict, session_id: str) -> Dict[str, Any]:
        """Use AI agent to analyze context based on technical metrics"""
        
        analysis_prompt = f"""
        Analyze the audio context based on these technical characteristics:
        
        Audio Metrics:
        - Audio Quality Score: {technical_analysis.get('audio_quality', 0)}
        - Noise Level: {technical_analysis.get('noise_level', 0)}
        - Speaker Count: {technical_analysis.get('speaker_count', 1)}
        - Signal Type: {technical_analysis.get('signal_type', 'unknown')}
        - Spectral Centroid: {technical_analysis.get('spectral_centroid', 0)}
        - Zero Crossing Rate: {technical_analysis.get('zero_crossing_rate', 0)}
        
        Determine:
        1. Source type: business_meeting, educational_content, entertainment, system_notification
        2. Processing priority: high, medium, low
        3. Recommended processing: enhanced_realtime, standard_realtime, batch_processing
        4. Confidence in your assessment (0-1)
        
        Consider that:
        - High quality speech with multiple speakers suggests business meeting
        - Single speaker with good quality suggests educational content
        - Music or mixed audio suggests entertainment
        - Short duration with system characteristics suggests notifications
        
        Provide your analysis with reasoning.
        """
        
        try:
            response = await self.agent.query(analysis_prompt)
            
            # Parse agent response
            context_result = self._parse_context_response(response, technical_analysis)
            
            return context_result
            
        except Exception as e:
            logger.error("Error in AI context analysis", session_id=session_id, error=str(e))
            return self._get_fallback_context_analysis(technical_analysis)
    
    def _parse_context_response(self, response: str, technical_analysis: Dict) -> Dict[str, Any]:
        """Parse AI agent response into structured context analysis"""
        # Simplified parsing for hackathon - in production would use more sophisticated parsing
        
        # Default values based on technical analysis
        if technical_analysis.get('speaker_count', 1) > 1:
            source_type = 'business_meeting'
            priority = 'high'
        elif technical_analysis.get('signal_type') == 'speech':
            source_type = 'educational_content'
            priority = 'medium'
        else:
            source_type = 'entertainment'
            priority = 'low'
        
        return {
            'source_type': source_type,
            'priority': priority,
            'recommended_processing': 'enhanced_realtime' if priority == 'high' else 'standard_realtime',
            'confidence': 0.85,
            'reasoning': response,
            'context_metadata': {
                'formal_context': priority == 'high',
                'real_time_required': True,
                'quality_threshold': 0.8 if priority == 'high' else 0.6
            }
        }
    
    def _get_fallback_context_analysis(self, technical_analysis: Dict) -> Dict[str, Any]:
        """Fallback context analysis when AI fails"""
        return {
            'source_type': 'unknown',
            'priority': 'medium',
            'recommended_processing': 'standard_realtime',
            'confidence': 0.5,
            'reasoning': 'Fallback analysis due to AI processing error',
            'context_metadata': {
                'formal_context': False,
                'real_time_required': True,
                'quality_threshold': 0.6
            }
        }
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Complete fallback analysis"""
        return {
            'source_type': 'unknown',
            'audio_quality': 0.5,
            'speaker_count': 1,
            'noise_level': 0.5,
            'priority': 'medium',
            'recommended_processing': 'standard_realtime',
            'confidence': 0.3,
            'reasoning': 'Fallback analysis due to processing error'
        }
    
    async def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status for dashboard"""
        return self.current_status.get(session_id, {
            'current_decision': 'idle',
            'confidence': 0.0,
            'reasoning': 'No recent analysis',
            'processing_time_ms': 0,
            'metadata': {}
        })
    
    async def shutdown(self):
        """Shutdown the agent"""
        logger.info("Audio Context Agent shutdown")
        self.current_status.clear() 