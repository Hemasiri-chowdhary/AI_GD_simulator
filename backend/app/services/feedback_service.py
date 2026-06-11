"""Feedback Service - Generates post-session feedback reports."""
import logging
import json
import random
from typing import List, Dict, Optional
from datetime import datetime

from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


FEEDBACK_PROMPT = """You are an expert Group Discussion evaluator for placement preparation.

Analyze the following GD transcript and provide detailed feedback for the USER participant only.

TRANSCRIPT:
{transcript}

Evaluate the USER's performance on these metrics (score 0-10):

1. **Confidence Score**
2. **Clarity & Fluency**
3. **Grammar Accuracy**
4. **Vocabulary Strength**
5. **Argument Strength**
6. **Leadership & Initiative**

Also provide **Participation Ratio (%)** for the user.

Provide your evaluation in this exact JSON format:
{
    "confidence_score": <number 0-10>,
    "clarity_fluency": <number 0-10>,
    "grammar_accuracy": <number 0-10>,
    "vocabulary_strength": <number 0-10>,
    "argument_strength": <number 0-10>,
    "participation_ratio": <number 0-100>,
    "leadership_initiative": <number 0-10>,
    "top_strengths": ["strength1", "strength2", "strength3"],
    "top_improvements": ["improvement1", "improvement2", "improvement3"],
    "next_session_goal": "one short goal",
    "filler_words": ["um", "like"],
    "suggested_phrases": ["better phrase 1", "better phrase 2"],
    "detailed_summary": "A concise 2-3 sentence summary"
}

Be constructive, specific, and helpful. Focus on actionable feedback for placement GD preparation."""


class FeedbackService:
    """Service for generating post-session feedback."""
    
    def __init__(self):
        self.ollama = OllamaClient()
    
    async def generate_feedback(
        self,
        session_id: str,
        topic: str,
        messages: List[Dict]
    ) -> Dict:
        """Generate comprehensive feedback for a GD session."""
        
        # Build transcript string
        transcript = self._build_transcript(messages)
        
        # Count user participation
        user_messages = [m for m in messages if m.get("speaker_id") == "user"]
        total_messages = len(messages)
        
        if not user_messages:
            return self._empty_feedback(session_id, "No user participation detected")
        
        # Generate feedback using LLM
        prompt = FEEDBACK_PROMPT.format(transcript=transcript)
        
        try:
            response = await self.ollama.generate(
                prompt=prompt,
                system_prompt="You are an expert GD evaluator. Respond only with valid JSON.",
                temperature=0.3,
                max_tokens=800
            )
            
            # Parse JSON response
            feedback = self._parse_feedback_response(response)
            feedback["session_id"] = session_id
            
            # Add participation metrics
            feedback["participation_details"] = {
                "user_messages": len(user_messages),
                "total_messages": total_messages,
                "participation_rate": round(len(user_messages) / total_messages * 100, 1)
            }

            feedback["participation_ratio"] = feedback.get(
                "participation_ratio",
                feedback["participation_details"]["participation_rate"]
            )

            if "overall_score" not in feedback:
                feedback["overall_score"] = self._compute_overall_score(feedback)
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error generating feedback: {e}")
            return self._fallback_feedback(session_id, user_messages, total_messages)
    
    def _build_transcript(self, messages: List[Dict]) -> str:
        """Build a formatted transcript string."""
        lines = []
        for msg in messages:
            speaker = msg.get("speaker_name", "Unknown")
            content = msg.get("content", "")
            msg_type = msg.get("message_type", "")
            
            # Mark user messages clearly
            if msg.get("speaker_id") == "user":
                lines.append(f"[USER - You]: {content}")
            else:
                lines.append(f"[{speaker}]: {content}")
        
        return "\n".join(lines)
    
    def _parse_feedback_response(self, response: str) -> Dict:
        """Parse the LLM feedback response."""
        try:
            # Try to extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
        
        # Return default structure if parsing fails
        return {
            "confidence_score": 6,
            "clarity_fluency": 6,
            "grammar_accuracy": 6,
            "vocabulary_strength": 6,
            "argument_strength": 6,
            "participation_ratio": 50,
            "leadership_initiative": 6,
            "overall_score": 60,
            "top_strengths": ["Participated in the discussion", "Showed willingness to engage"],
            "top_improvements": ["Be more assertive", "Use specific examples"],
            "next_session_goal": "Speak up earlier with a structured point",
            "filler_words": [],
            "suggested_phrases": [],
            "detailed_summary": "Good effort in participating. Continue practicing for better fluency."
        }
    
    def _empty_feedback(self, session_id: str, reason: str) -> Dict:
        """Return empty feedback when user didn't participate."""
        return {
            "session_id": session_id,
            "confidence_score": 0,
            "clarity_fluency": 0,
            "grammar_accuracy": 0,
            "vocabulary_strength": 0,
            "argument_strength": 0,
            "participation_ratio": 0,
            "leadership_initiative": 0,
            "overall_score": 0,
            "top_strengths": [],
            "top_improvements": ["Participate actively in the discussion to receive feedback"],
            "next_session_goal": "Share at least one structured point",
            "filler_words": [],
            "suggested_phrases": [],
            "detailed_summary": reason
        }
    
    def _fallback_feedback(
        self,
        session_id: str,
        user_messages: List[Dict],
        total_messages: int
    ) -> Dict:
        """Generate comprehensive feedback without LLM using rule-based analysis."""
        
        participation_rate = len(user_messages) / total_messages if total_messages > 0 else 0
        
        # Calculate basic scores based on participation
        base_score = 50 + (participation_rate * 30)
        
        # Analyze message lengths
        avg_length = sum(len(m.get("content", "")) for m in user_messages) / len(user_messages) if user_messages else 0
        length_bonus = min(20, avg_length / 10)
        
        score = min(100, base_score + length_bonus)
        
        strengths = []
        improvements = []
        filler_words = []
        suggested_phrases = []
        
        # Analyze content for filler words
        all_text = " ".join(m.get("content", "").lower() for m in user_messages)
        common_fillers = ["um", "uh", "like", "you know", "basically", "actually", "literally", "i mean", "sort of", "kind of"]
        for filler in common_fillers:
            if filler in all_text:
                filler_words.append(filler)
        
        # Generate strengths based on analysis
        if participation_rate > 0.2:
            strengths.append("Active participation in the discussion")
        if avg_length > 100:
            strengths.append("Provided detailed and thorough responses")
        elif avg_length > 50:
            strengths.append("Good response length with adequate detail")
        if len(user_messages) >= 3:
            strengths.append("Consistent engagement throughout the session")
        if not filler_words:
            strengths.append("Clear speaking with minimal filler words")
        if any(word in all_text for word in ["however", "moreover", "therefore", "furthermore"]):
            strengths.append("Good use of transition words")
        
        # Generate improvements based on analysis
        if participation_rate < 0.15:
            improvements.append("Increase participation frequency - aim to speak more often")
        if avg_length < 30:
            improvements.append("Elaborate more on your points with examples")
        if filler_words:
            improvements.append(f"Reduce filler words like: {', '.join(filler_words[:3])}")
        if len(user_messages) < 2:
            improvements.append("Engage more consistently throughout the discussion")
        if not any(word in all_text for word in ["because", "since", "therefore", "as a result"]):
            improvements.append("Strengthen arguments by explaining your reasoning")
        
        # Suggested professional phrases
        suggested_phrases = [
            "I'd like to build on that point by adding...",
            "From my perspective, we should consider...",
            "While I appreciate that viewpoint, let me offer an alternative...",
            "To summarize my position...",
            "The key takeaway here is..."
        ]
        
        # Ensure at least some content
        if not strengths:
            strengths = ["Participated in the discussion", "Showed willingness to engage"]
        if not improvements:
            improvements = ["Continue practicing with varied topics", "Work on assertive communication"]
        
        # Calculate individual scores with variation
        base = score / 10
        confidence = min(10, max(0, base + random.uniform(-1, 1)))
        clarity = min(10, max(0, base + random.uniform(-0.5, 0.5)))
        grammar = min(10, max(0, base + random.uniform(-0.5, 1) - (0.5 * len(filler_words))))
        vocabulary = min(10, max(0, base + random.uniform(-1, 0.5)))
        argument = min(10, max(0, base + random.uniform(-0.5, 0.5)))
        leadership = min(10, max(0, (base * 0.8) + (2 if len(user_messages) >= 2 else 0)))
        
        return {
            "session_id": session_id,
            "confidence_score": round(confidence, 1),
            "clarity_fluency": round(clarity, 1),
            "grammar_accuracy": round(grammar, 1),
            "vocabulary_strength": round(vocabulary, 1),
            "argument_strength": round(argument, 1),
            "participation_ratio": round(participation_rate * 100, 1),
            "leadership_initiative": round(leadership, 1),
            "overall_score": round(score, 1),
            "top_strengths": strengths[:3],
            "top_improvements": improvements[:3],
            "next_session_goal": "Focus on speaking early and using structured arguments with clear reasoning",
            "filler_words": filler_words[:5],
            "suggested_phrases": suggested_phrases[:3],
            "detailed_summary": f"You contributed {len(user_messages)} messages out of {total_messages} total. {'Good participation! ' if participation_rate > 0.15 else 'Try to participate more next time. '}Keep practicing to improve your GD skills and confidence."
        }

    def _compute_overall_score(self, feedback: Dict) -> float:
        """Compute overall score (0-100) from 0-10 metrics."""
        metrics = [
            feedback.get("confidence_score", 0),
            feedback.get("clarity_fluency", 0),
            feedback.get("grammar_accuracy", 0),
            feedback.get("vocabulary_strength", 0),
            feedback.get("argument_strength", 0),
            feedback.get("leadership_initiative", 0)
        ]
        avg = sum(metrics) / len(metrics) if metrics else 0
        return round(avg * 10, 1)
