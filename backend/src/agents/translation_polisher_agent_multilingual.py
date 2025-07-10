"""
Multilingual Hybrid Translation Polisher Agent
Ultra-fast with AI enhancement for multiple languages
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


class TranslationPolisherAgentMultilingual:
    """
    Multilingual Hybrid Translation Polisher Agent
    Supports instant rules for multiple languages + AI enhancement
    """
    
    def __init__(self, api_key: str = None):
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
            'fastest_ai_ms': float('inf'),
            'languages_processed': set()
        }
        
        # Background processing queue
        self.ai_queue = deque()
        self.processing_lock = threading.Lock()
        self.background_task = None
        
        # Multilingual instant rules
        self.instant_rules = {
            'english': [
                # Basic verb corrections
                ("I go to", "I go to the"),
                ("She go", "She goes"),
                ("He go", "He goes"),
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
                
                # Common contractions
                (" dont ", " don't "),
                (" cant ", " can't "),
                (" wont ", " won't "),
                (" isnt ", " isn't "),
                (" arent ", " aren't "),
                (" wasnt ", " wasn't "),
                (" werent ", " weren't "),
                
                # Dutch -> English common errors
                ("my name is", "my name is"),
                ("My name is", "My name is"),
                ("Hallo", "Hello"),
                ("hallo", "hello"),
                ("mijn naam is", "my name is"),
                ("Mijn naam is", "My name is"),
                ("naam", "name"),
                ("ik ben", "I am"),
                ("Ik ben", "I am"),
                
                # More aggressive Dutch patterns
                ("Hallo, mijn naam is", "Hello, my name is"),
                ("hallo, mijn naam is", "hello, my name is"),
                ("Hallo, my name", "Hello, my name"),
                ("hallo, my name", "hello, my name"),
                
                # Mixed language patterns
                ("Hallo, my", "Hello, my"),
                ("hallo, my", "hello, my"),
                
                # Grammar improvements
                ("I am go", "I am going"),
                ("I was go", "I was going"),
                ("have go", "have gone"),
                ("has go", "has gone"),
                ("am call", "am called"),
                ("is call", "is called"),
                ("are call", "are called"),
                
                # Article corrections
                ("a apple", "an apple"),
                ("a orange", "an orange"),
                ("a elephant", "an elephant"),
                ("a hour", "an hour"),
                
                # Pronunciation/translation fixes
                ("me name", "my name"),
                ("me is", "I am"),
                ("me am", "I am"),
                
                # Capitalization (simple)
                ("hello, my", "Hello, my"),
                ("hi, my", "Hi, my"),
                
                # Missing articles
                (" name is ", " name is "),
                ("name is ", "my name is "),
            ],
            'spanish': [
                ("yo va", "yo voy"),
                ("tu va", "tú vas"),
                ("el va", "él va"),
                ("ella va", "ella va"),
                ("nosotros va", "nosotros vamos"),
                ("vosotros va", "vosotros vais"),
                ("ellos va", "ellos van"),
                ("yo tiene", "yo tengo"),
                ("tu tiene", "tú tienes"),
                ("nosotros tiene", "nosotros tenemos"),
                ("estar siendo", "estar"),
                ("muy mucho", "mucho"),
                ("mas mejor", "mejor"),
                ("menos peor", "peor"),
            ],
            'french': [
                ("je va", "je vais"),
                ("tu va", "tu vas"),
                ("il va", "il va"),
                ("elle va", "elle va"),
                ("nous va", "nous allons"),
                ("vous va", "vous allez"),
                ("ils va", "ils vont"),
                ("je avoir", "j'ai"),
                ("tu avoir", "tu as"),
                ("il avoir", "il a"),
                ("elle avoir", "elle a"),
                ("nous avoir", "nous avons"),
                ("très beaucoup", "beaucoup"),
                ("plus mieux", "mieux"),
            ],
            'german': [
                ("ich gehen", "ich gehe"),
                ("du gehen", "du gehst"),
                ("er gehen", "er geht"),
                ("sie gehen", "sie geht"),
                ("wir gehen", "wir gehen"),
                ("ihr gehen", "ihr geht"),
                ("sie gehen", "sie gehen"),
                ("ich haben", "ich habe"),
                ("du haben", "du hast"),
                ("er haben", "er hat"),
                ("sie haben", "sie hat"),
                ("sehr viel", "viel"),
            ],
            'portuguese': [
                ("eu vai", "eu vou"),
                ("tu vai", "tu vais"),
                ("ele vai", "ele vai"),
                ("ela vai", "ela vai"),
                ("nós vai", "nós vamos"),
                ("vós vai", "vós ides"),
                ("eles vai", "eles vão"),
                ("eu tem", "eu tenho"),
                ("tu tem", "tu tens"),
                ("ele tem", "ele tem"),
                ("nós tem", "nós temos"),
                ("muito muito", "muito"),
            ],
            'italian': [
                ("io va", "io vado"),
                ("tu va", "tu vai"),
                ("lui va", "lui va"),
                ("lei va", "lei va"),
                ("noi va", "noi andiamo"),
                ("voi va", "voi andate"),
                ("loro va", "loro vanno"),
                ("io avere", "io ho"),
                ("tu avere", "tu hai"),
                ("lui avere", "lui ha"),
                ("molto molto", "molto"),
            ],
            'dutch': [
                ("ik ga", "ik ga"),
                ("jij ga", "jij gaat"),
                ("hij ga", "hij gaat"),
                ("zij ga", "zij gaat"),
                ("wij ga", "wij gaan"),
                ("jullie ga", "jullie gaan"),
                ("zij ga", "zij gaan"),
                ("ik heb", "ik heb"),
                ("jij heb", "jij hebt"),
                ("hij heb", "hij heeft"),
                ("zij heb", "zij heeft"),
                ("wij heb", "wij hebben"),
                ("jullie heb", "jullie hebben"),
                ("zij heb", "zij hebben"),
                ("ik ben", "ik ben"),
                ("jij ben", "jij bent"),
                ("hij ben", "hij is"),
                ("zij ben", "zij is"),
                ("wij ben", "wij zijn"),
                ("jullie ben", "jullie zijn"),
                ("zij ben", "zij zijn"),
                ("niet geen", "geen"),
                ("veel veel", "veel"),
                ("meer beter", "beter"),
                ("minder slechter", "slechter"),
                ("ik doe", "ik doe"),
                ("jij doe", "jij doet"),
                ("hij doe", "hij doet"),
                ("zij doe", "zij doet"),
                ("wij doe", "wij doen"),
                ("jullie doe", "jullie doen"),
                ("zij doe", "zij doen"),
            ]
        }
        
        # Language detection keywords
        self.language_keywords = {
            'english': ['the', 'and', 'is', 'are', 'was', 'were', 'have', 'has', 'had', 'will', 'would'],
            'spanish': ['el', 'la', 'los', 'las', 'es', 'son', 'era', 'fueron', 'tiene', 'tienen', 'será'],
            'french': ['le', 'la', 'les', 'est', 'sont', 'était', 'étaient', 'avoir', 'sera', 'seront'],
            'german': ['der', 'die', 'das', 'ist', 'sind', 'war', 'waren', 'haben', 'hat', 'wird'],
            'portuguese': ['o', 'a', 'os', 'as', 'é', 'são', 'era', 'eram', 'tem', 'têm', 'será'],
            'italian': ['il', 'la', 'lo', 'gli', 'è', 'sono', 'era', 'erano', 'ha', 'hanno', 'sarà'],
            'dutch': ['de', 'het', 'een', 'is', 'zijn', 'was', 'waren', 'heeft', 'hebben', 'zal', 'zullen']
        }
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on keywords"""
        text_lower = text.lower()
        scores = {}
        
        for lang, keywords in self.language_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[lang] = score
        
        # Return language with highest score, default to english
        if scores:
            detected = max(scores, key=scores.get)
            return detected if scores[detected] > 0 else 'english'
        return 'english'
    
    async def initialize(self):
        """Initialize the multilingual hybrid agent"""
        try:
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
                        self.background_task = asyncio.create_task(self._background_processor())
                        logger.info("Multilingual hybrid agent initialized with AI enhancement")
                    else:
                        logger.warning("AI test failed, using instant-only mode")
                except Exception as e:
                    logger.warning(f"AI initialization failed: {e}, using instant-only mode")
            else:
                logger.info("AI not available, using instant-only mode")
                
        except Exception as e:
            logger.error(f"Multilingual hybrid agent initialization error: {e}")
            self.is_initialized = True
    
    async def polish_translation(
        self, 
        raw_translation: str, 
        target_language: str = "auto",
        ai_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Ultra-fast multilingual translation polishing
        
        Args:
            raw_translation: Text to polish
            target_language: Target language ('auto' for detection, or specific language)
            ai_callback: Optional callback for AI-enhanced result
            
        Returns:
            str: Instantly polished text
        """
        if not self.is_initialized:
            return raw_translation
        
        start_time = time.time()
        
        # Detect language if auto
        if target_language == "auto":
            detected_lang = self._detect_language(raw_translation)
        else:
            detected_lang = target_language.lower()
        
        # Track language usage
        self.stats['languages_processed'].add(detected_lang)
        
        # INSTANT RESPONSE: Apply language-specific rules
        instant_result = self._apply_instant_rules(raw_translation, detected_lang)
        
        instant_time = (time.time() - start_time) * 1000
        
        # Update stats
        self.stats['total_requests'] += 1
        self.stats['instant_responses'] += 1
        self.stats['average_instant_time_ms'] = (
            (self.stats['average_instant_time_ms'] * (self.stats['instant_responses'] - 1) + instant_time) 
            / self.stats['instant_responses']
        )
        self.stats['fastest_instant_ms'] = min(self.stats['fastest_instant_ms'], instant_time)
        
        # BACKGROUND AI ENHANCEMENT
        if self.use_gemini and ai_callback:
            with self.processing_lock:
                self.ai_queue.append({
                    'text': raw_translation,
                    'language': detected_lang,
                    'instant_result': instant_result,
                    'callback': ai_callback,
                    'timestamp': time.time()
                })
        
        return instant_result
    
    def _apply_instant_rules(self, text: str, language: str) -> str:
        """Apply instant grammar rules for specific language"""
        original_text = text
        result = text
        
        # DEBUG: Log input
        logger.info("🔧 POLISHER: Starting rule application", 
                   input_text=original_text,
                   language=language,
                   text_length=len(text))
        
        # Get rules for detected language, fallback to english
        rules = self.instant_rules.get(language, self.instant_rules['english'])
        logger.info("🔧 POLISHER: Using rules", 
                   language=language,
                   rules_count=len(rules),
                   available_languages=list(self.instant_rules.keys()))
        
        # Apply ALL matching rules (not just first)
        applied_rules = []
        for old, new in rules:
            # Case-insensitive search but preserve original case
            if old.lower() in result.lower():
                # Find the actual case in the text
                old_index = result.lower().find(old.lower())
                if old_index != -1:
                    # Replace while preserving case context
                    before = result[:old_index]
                    after = result[old_index + len(old):]
                    result = before + new + after
                    applied_rules.append((old, new))
                    logger.info("🎯 POLISHER: Applied rule", 
                               rule_from=old,
                               rule_to=new,
                               before_text=original_text,
                               after_text=result)
        
        # DEBUG: Log final result
        if applied_rules:
            logger.info("✨ POLISHER: Grammar corrections applied", 
                       original=original_text,
                       corrected=result,
                       rules_applied=len(applied_rules),
                       rules_list=applied_rules)
        else:
            logger.info("ℹ️ POLISHER: No grammar corrections needed", 
                       text=original_text,
                       language=language,
                       rules_checked=len(rules))
        
        return result
    
    async def _background_processor(self):
        """Background task to process AI enhancements"""
        while True:
            try:
                item = None
                with self.processing_lock:
                    if self.ai_queue:
                        item = self.ai_queue.popleft()
                
                if item:
                    # Create language-specific prompt
                    language_name = item['language'].title()
                    prompt = f"Fix grammar in {language_name}: {item['text']}"
                    
                    ai_start = time.time()
                    ai_result = await self._call_gemini_fast(prompt)
                    ai_time = (time.time() - ai_start) * 1000
                    
                    # Update AI stats
                    self.stats['ai_enhancements'] += 1
                    self.stats['average_ai_time_ms'] = (
                        (self.stats['average_ai_time_ms'] * (self.stats['ai_enhancements'] - 1) + ai_time) 
                        / self.stats['ai_enhancements']
                    )
                    self.stats['fastest_ai_ms'] = min(self.stats['fastest_ai_ms'], ai_time)
                    
                    # Call callback if result is different/better
                    if ai_result and ai_result != item['instant_result'] and len(ai_result.strip()) > 0:
                        try:
                            item['callback'](ai_result)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                else:
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
            'languages_processed': list(self.stats['languages_processed']),
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