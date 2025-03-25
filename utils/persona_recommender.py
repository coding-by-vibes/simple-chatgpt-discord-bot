import json
import os
from typing import List, Dict, Optional
from datetime import datetime

class PersonaRecommender:
    def __init__(self, settings_dir: str):
        self.settings_dir = settings_dir
        self.recommendations_dir = os.path.join(settings_dir, "persona_recommendations")
        os.makedirs(self.recommendations_dir, exist_ok=True)

    async def generate_recommendations(self, 
                                     user_id: str,
                                     interaction_history: List[Dict],
                                     current_personas: List[Dict]) -> List[Dict]:
        """Generate persona recommendations based on user interactions.
        
        Args:
            user_id: The Discord user ID
            interaction_history: List of recent interactions
            current_personas: List of currently available personas
            
        Returns:
            List[Dict]: List of recommended personas
        """
        # Create a prompt for ChatGPT to analyze interactions and suggest personas
        prompt = f"""
        Based on this user's interaction history and current personas, recommend 3-5 new personas that would be helpful.
        
        Current Personas:
        {json.dumps(current_personas, indent=2)}
        
        Recent Interactions:
        {json.dumps(interaction_history[-5:], indent=2)}
        
        For each recommended persona, provide:
        1. name: A unique, descriptive name
        2. role: The primary role/purpose
        3. traits: List of 3-5 key personality traits
        4. style: Communication style (formal, casual, technical, etc.)
        5. example: A sample response showing the personality
        
        Format as a JSON array of persona objects.
        """
        
        # TODO: Call ChatGPT API with this prompt
        # For now, return example recommendations
        recommendations = [
            {
                "name": "Code Mentor",
                "role": "Programming and technical guidance",
                "traits": ["patient", "technical", "methodical", "encouraging"],
                "style": "Clear and structured, with code examples",
                "example": "Let's break down this problem step by step. First, we need to consider the data structure..."
            },
            {
                "name": "Creative Writer",
                "role": "Storytelling and creative expression",
                "traits": ["imaginative", "expressive", "inspirational", "detailed"],
                "style": "Flowing and descriptive, with rich imagery",
                "example": "The story unfolds like a tapestry, each thread carefully woven into the narrative..."
            }
        ]
        
        # Save recommendations
        await self.save_recommendations(user_id, recommendations)
        
        return recommendations

    async def save_recommendations(self, user_id: str, recommendations: List[Dict]):
        """Save persona recommendations for a user.
        
        Args:
            user_id: The Discord user ID
            recommendations: List of recommended personas
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recommendations_{user_id}_{timestamp}.json"
        filepath = os.path.join(self.recommendations_dir, filename)
        
        data = {
            "user_id": user_id,
            "timestamp": timestamp,
            "recommendations": recommendations
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    async def get_recommendations(self, user_id: str) -> List[Dict]:
        """Get the most recent recommendations for a user.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            List[Dict]: List of recommended personas
        """
        # Get all recommendation files for the user
        user_files = [f for f in os.listdir(self.recommendations_dir) 
                     if f.startswith(f"recommendations_{user_id}_")]
        
        if not user_files:
            return []
        
        # Get the most recent file
        latest_file = max(user_files, key=lambda x: os.path.getctime(
            os.path.join(self.recommendations_dir, x)))
        
        with open(os.path.join(self.recommendations_dir, latest_file), 'r', 
                 encoding='utf-8') as f:
            data = json.load(f)
            return data.get("recommendations", [])

    async def apply_recommendation(self, user_id: str, 
                                 persona_name: str) -> Optional[Dict]:
        """Apply a recommended persona to the user's available personas.
        
        Args:
            user_id: The Discord user ID
            persona_name: Name of the recommended persona to apply
            
        Returns:
            Optional[Dict]: The applied persona if successful, None otherwise
        """
        recommendations = await self.get_recommendations(user_id)
        
        # Find the recommended persona
        persona = next((p for p in recommendations 
                       if p["name"].lower() == persona_name.lower()), None)
        
        if not persona:
            return None
            
        # Format the persona for the persona system
        formatted_persona = {
            "name": persona["name"],
            "role": persona["role"],
            "traits": persona["traits"],
            "style": persona["style"],
            "example": persona["example"],
            "created_by": "recommendation",
            "created_at": datetime.now().isoformat()
        }
        
        return formatted_persona 