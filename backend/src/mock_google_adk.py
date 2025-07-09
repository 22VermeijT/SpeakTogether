"""
Mock Google ADK for development and testing
This replaces the actual google_adk package which may not be publicly available
"""

import asyncio
import time
from typing import Dict, Any, Optional


class LlmAgent:
    """Mock LLM Agent for development"""
    
    def __init__(self, name: str, instructions: str, model: str = "gemini-1.5-pro", agent_manager=None):
        self.name = name
        self.instructions = instructions
        self.model = model
        self.agent_manager = agent_manager
        self.is_initialized = False
        
    async def initialize(self):
        """Mock initialization"""
        await asyncio.sleep(0.1)  # Simulate async initialization
        self.is_initialized = True
        
    async def query(self, prompt: str) -> str:
        """Mock query response"""
        await asyncio.sleep(0.2)  # Simulate processing time
        
        # Simple mock responses based on agent type
        if "AudioContext" in self.name:
            return "Audio source: business_meeting, Quality: 0.85, Priority: high"
        elif "TranslationStrategy" in self.name:
            return "Style: formal_business, Adaptation: conservative, Confidence: 0.92"
        elif "QualityControl" in self.name:
            return "Quality score: 0.88, Passed: true, Issues: none"
        elif "VoiceSynthesis" in self.name:
            return "Voice: professional_male, Style: formal, Duration: 2.3s"
        elif "Orchestrator" in self.name:
            return "Processing: enhanced_model, Translation: formal, Quality_threshold: 0.8"
        else:
            return f"Mock response from {self.name}: {prompt[:50]}..."


class AgentManager:
    """Mock Agent Manager for development"""
    
    def __init__(self, project_id: str, api_key: str):
        self.project_id = project_id
        self.api_key = api_key
        self.agents = {}
        
    async def initialize(self):
        """Mock initialization"""
        await asyncio.sleep(0.1)
        
    def get_agent(self, name: str) -> Optional[LlmAgent]:
        """Get agent by name"""
        return self.agents.get(name)
        
    def register_agent(self, agent: LlmAgent):
        """Register an agent"""
        self.agents[agent.name] = agent


# Export the classes to match the expected google_adk interface
__all__ = ['LlmAgent', 'AgentManager'] 