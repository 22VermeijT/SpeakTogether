"""
Hybrid Translation Polisher Agent - Ultra-fast with AI enhancement
Provides instant mock results + background AI polishing for maximum speed
"""

import asyncio
import time
import os
from typing import Dict, Any, Optional, Callable
import structlog
from collections import deque
import threading

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import google.generativeai as genai
    GEMINI_IMPORT_OK = True
except ImportError:
    genai = None
    GEMINI_IMPORT_OK = False

logger = structlog.get_logger()


class TranslationPolisherAgentHybrid:
    """
    Hybrid Translation Polisher Agent - Ultra-fast instant results with AI enhancement
    
    Strategy:
    1. Instant mock response (0-5ms)
    2. Background AI enhancement (3-5 seconds)
    3. Optional callback when AI result is ready
    """
    
    def __init__(self, api_key: str = None):
        # Use ADK_API_KEY from environment if no api_key provided
        if api_key is None:
            api_key = os.getenv('ADK_API_KEY')
        self.api_key = api_key
        self.model = None
        self.is_initialized = False
        self.use_gemini = False
        
        # Stats tracking
        self.stats = {
            'total_requests': 0,
            'instant_responses': 0,
            'ai_enhancements': 0,
            'average_instant_time_ms': 0.0,
            'average_ai_time_ms': 0.0,
            'fastest_instant_ms': float('inf'),
            'fastest_ai_ms': float('inf')
        }
        
        # Background processing queue
        self.ai_queue = deque()
        self.processing_lock = threading.Lock()
        self.background_task = None
        
        # Mock rules for instant processing
        self.instant_rules = [
            ("I go to", "I go to the"),
            ("She go", "She goes"),
            ("He go", "He goes"),
            ("They go", "They go"),
            ("We go", "We go"),
            ("You go", "You go"),
            ("It go", "It goes"),
            ("He do", "He does"),
            ("She do", "She does"),
            ("It do", "It does"),
            ("They is", "They are"),
            ("We is", "We are"),
            ("You is", "You are"),
            ("I are", "I am"),
            ("He are", "He is"),
            ("She are", "She is"),
            ("It are", "It is"),
            ("I was go", "I was going"),
            ("I am go", "I am going"),
            ("was went", "went"),
            ("have went", "have gone"),
            ("had went", "had gone"),
            (" dont ", " don't "),
            (" cant ", " can't "),
            (" wont ", " won't "),
            (" isnt ", " isn't "),
            (" arent ", " aren't "),
            (" wasnt ", " wasn't "),
            (" werent ", " weren't "),
            (" hasnt ", " hasn't "),
            (" havent ", " haven't "),
            (" hadnt ", " hadn't "),
            (" shouldnt ", " shouldn't "),
            (" couldnt ", " couldn't "),
            (" wouldnt ", " wouldn't "),
        ]
    
    async def initialize(self):
        """Initialize the hybrid agent"""
        try:
            # Always enable instant responses
            self.is_initialized = True
            
            # Try to initialize AI enhancement
            if GEMINI_IMPORT_OK and self.api_key:
                try:
                    genai.configure(api_key=self.api_key)
                    self.model = genai.GenerativeModel(
                        'gemini-1.5-flash',
                        generation_config=genai.GenerationConfig(
                            max_output_tokens=50,
                            temperature=0.1,
                            top_p=0.8,
                            top_k=20
                        )
                    )
                    
                    # Quick test
                    test_response = await asyncio.wait_for(
                        self.model.generate_content_async("Fix: test"),
                        timeout=2.0
                    )
                    
                    if test_response and test_response.text:
                        self.use_gemini = True
                        # Start background processing
                        self.background_task = asyncio.create_task(self._background_processor())
                        logger.info("Hybrid agent initialized with AI enhancement")
                    else:
                        logger.warning("AI test failed, using instant-only mode")
                except Exception as e:
                    logger.warning(f"AI initialization failed: {e}, using instant-only mode")
            else:
                logger.info("AI not available, using instant-only mode")
                
        except Exception as e:
            logger.error(f"Hybrid agent initialization error: {e}")
            # Always ensure instant mode works
            self.is_initialized = True
    
    async def polish_translation(
        self, 
        raw_translation: str, 
        target_language: str = "English",
        ai_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Ultra-fast translation polishing with optional AI enhancement
        
        Args:
            raw_translation: Text to polish
            target_language: Target language
            ai_callback: Optional callback for AI-enhanced result
            
        Returns:
            str: Instantly polished text (mock), AI result via callback if available
        """
        if not self.is_initialized:
            return raw_translation
        
        start_time = time.time()
        
        # INSTANT RESPONSE: Apply mock rules (0-5ms)
        instant_result = self._apply_instant_rules(raw_translation)
        
        instant_time = (time.time() - start_time) * 1000
        
        # Update instant stats
        self.stats['total_requests'] += 1
        self.stats['instant_responses'] += 1
        self.stats['average_instant_time_ms'] = (
            (self.stats['average_instant_time_ms'] * (self.stats['instant_responses'] - 1) + instant_time) 
            / self.stats['instant_responses']
        )
        self.stats['fastest_instant_ms'] = min(self.stats['fastest_instant_ms'], instant_time)
        
        # BACKGROUND AI ENHANCEMENT: Queue for AI processing if available
        if self.use_gemini and ai_callback:
            with self.processing_lock:
                self.ai_queue.append({
                    'text': raw_translation,
                    'instant_result': instant_result,
                    'callback': ai_callback,
                    'timestamp': time.time()
                })
        
        return instant_result
    
    def _apply_instant_rules(self, text: str) -> str:
        """Apply instant grammar rules (0-5ms)"""
        result = text
        
        # Apply first matching rule for maximum speed
        for old, new in self.instant_rules:
            if old in result:
                result = result.replace(old, new, 1)  # Replace only first occurrence
                break
        
        return result
    
    async def _background_processor(self):
        """Background task to process AI enhancements"""
        while True:
            try:
                # Check queue
                item = None
                with self.processing_lock:
                    if self.ai_queue:
                        item = self.ai_queue.popleft()
                
                if item:
                    # Process with AI
                    ai_start = time.time()
                    ai_result = await self._call_gemini_fast(f"Fix grammar: {item['text']}")
                    ai_time = (time.time() - ai_start) * 1000
                    
                    # Update AI stats
                    self.stats['ai_enhancements'] += 1
                    self.stats['average_ai_time_ms'] = (
                        (self.stats['average_ai_time_ms'] * (self.stats['ai_enhancements'] - 1) + ai_time) 
                        / self.stats['ai_enhancements']
                    )
                    self.stats['fastest_ai_ms'] = min(self.stats['fastest_ai_ms'], ai_time)
                    
                    # Call callback with AI result if it's different/better
                    if ai_result and ai_result != item['instant_result'] and len(ai_result.strip()) > 0:
                        try:
                            item['callback'](ai_result)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                else:
                    # No items in queue, sleep briefly
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Background processor error: {e}")
                await asyncio.sleep(1)
    
    async def _call_gemini_fast(self, prompt: str) -> str:
        """Fast Gemini API call"""
        try:
            response = await asyncio.wait_for(
                self.model.generate_content_async(prompt),
                timeout=5.0
            )
            
            if response and response.text:
                cleaned = response.text.strip()
                if cleaned.startswith('"') and cleaned.endswith('"'):
                    cleaned = cleaned[1:-1]
                return cleaned
            return ""
        except Exception:
            return ""
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            **self.stats,
            'is_initialized': self.is_initialized,
            'ai_available': self.use_gemini,
            'queue_size': len(self.ai_queue)
        }
    
    async def shutdown(self):
        """Shutdown the agent"""
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass 