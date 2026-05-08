"""
SHL Assessment Recommender Agent.
Handles 4 conversational behaviors: CLARIFY, RECOMMEND, REFINE, COMPARE.
Includes rule-based fallback when no API key is configured.
"""

import json
import re
import asyncio
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

# Import from local modules
from retriever import retrieve
from prompts import format_catalog_context

# Load catalog for rule-based responses
import json as json_module


@dataclass
class ConversationContext:
    """Accumulates context from the conversation."""
    job_role: Optional[str] = None
    seniority: Optional[str] = None
    competency_types: List[str] = None
    testing_format: Optional[str] = None
    languages: List[str] = None
    constraints: List[str] = None
    turn_count: int = 0
    has_recommended: bool = False

    def __post_init__(self):
        if self.competency_types is None:
            self.competency_types = []
        if self.constraints is None:
            self.constraints = []
        if self.languages is None:
            self.languages = []


def load_catalog() -> List[Dict]:
    """Load catalog for rule-based responses."""
    with open("catalog.json", "r") as f:
        return json_module.load(f)


class SHLAgent:
    def __init__(self):
        self.catalog = load_catalog()

    def extract_context(self, messages: List[Dict]) -> ConversationContext:
        """Extract job-relevant signals from conversation history."""
        ctx = ConversationContext()

        all_text = " ".join(m.get("content", "") for m in messages)

        # Extract job roles/keywords
        role_keywords = [
            "software engineer", "developer", "data scientist", "analyst",
            "manager", "sales", "customer service", "accountant", "hr",
            "marketing", "product manager", "designer", "consultant",
            "executive", "director", "leader", "specialist", "coordinator",
            "mechanical", "financial", "salesperson", "call center", "banking"
        ]
        for role in role_keywords:
            if role.lower() in all_text.lower():
                ctx.job_role = role
                break

        # Extract seniority
        seniority_keywords = {
            "entry": ["entry level", "graduate", "fresher", "new hire", "junior"],
            "mid": ["mid level", "experienced", "professional", "individual contributor"],
            "senior": ["senior", "lead", "principal"],
            "executive": ["executive", "director", "vp", "c-level", "cfo", "ceo", "cto", "cio"]
        }
        for level, keywords in seniority_keywords.items():
            if any(kw in all_text.lower() for kw in keywords):
                ctx.seniority = level
                break

        # Extract competency types
        competency_keywords = {
            "A": ["cognitive", "reasoning", "aptitude", "numerical", "verbal", "inductive", "deductive", "ability"],
            "P": ["personality", "motivation", "traits", "preferences", "character"],
            "B": ["behavior", "competency", "situation", "judgment", "behavioral", "leadership"],
            "K": ["skill", "knowledge", "technical", "coding", "programming", "knowledge"],
            "S": ["simulation", "work sample", "practical", "hands-on"],
        }
        for ctype, keywords in competency_keywords.items():
            if any(kw in all_text.lower() for kw in keywords):
                if ctype not in ctx.competency_types:
                    ctx.competency_types.append(ctype)

        # Extract constraints
        constraint_keywords = {
            "remote": ["remote", "online", "supervis", "proctor"],
            "short": ["short", "quick", "fast", "brief", "under 20"],
            "adaptive": ["adaptive", "irt"],
            "multiple_language": ["multilingual", "multiple language"],
        }
        for constraint, keywords in constraint_keywords.items():
            if any(kw in all_text.lower() for kw in keywords):
                ctx.constraints.append(constraint)

        # Turn count
        ctx.turn_count = sum(1 for m in messages if m.get("role") == "user")

        return ctx

    def build_retrieval_query(self, ctx: ConversationContext) -> str:
        """Build a rich query string from conversation context."""
        parts = []

        if ctx.job_role:
            parts.append(ctx.job_role)
        if ctx.seniority:
            parts.append(f"{ctx.seniority} level")
        if ctx.competency_types:
            parts.append(" ".join(ctx.competency_types))
        if ctx.constraints:
            parts.append(" ".join(ctx.constraints))

        return " ".join(parts) if parts else "assessment hiring"

    def detect_compare_request(self, messages: List[Dict]) -> bool:
        """Detect if user is asking to compare assessments."""
        if not messages:
            return False

        last_message = messages[-1].get("content", "").lower()

        compare_keywords = [
            "difference between", "compare", "versus", " vs ", "compared to",
            "which is better", "distinguish", "contrast"
        ]
        return any(kw in last_message for kw in compare_keywords)

    def detect_refine_request(self, messages: List[Dict]) -> bool:
        """Detect if user is refining their requirements."""
        if len(messages) < 2:
            return False

        last_message = messages[-1].get("content", "").lower()

        refine_keywords = [
            "actually", "instead", "change", "add", "remove", "instead of",
            "also include", "but also", "make it", "update", "modify",
            "different", "another", "also add"
        ]
        return any(kw in last_message for kw in refine_keywords)

    def detect_off_topic(self, messages: List[Dict]) -> bool:
        """Detect off-topic requests."""
        if not messages:
            return False

        all_text = " ".join(m.get("content", "").lower() for m in messages)

        off_topic_keywords = [
            "interview question", "how to hire", "salary", "compensation",
            "legal advice", "job description", "onboarding", "training plan",
        ]
        # Check for injection patterns separately
        injection_keywords = [
            "ignore previous", "ignore all", "system prompt", "reveal your",
            "pretend you are", "you are now", "disregard your", "new instructions"
        ]
        if any(kw in all_text for kw in injection_keywords):
            return True  # Will be handled as injection

        return any(kw in all_text for kw in off_topic_keywords)

    def detect_prompt_injection(self, messages: List[Dict]) -> bool:
        """Detect prompt injection attempts."""
        if not messages:
            return False

        for msg in messages:
            content = msg.get("content", "").lower()
            injection_patterns = [
                "ignore previous instructions",
                "ignore all previous",
                "pretend you are",
                "you are now",
                "disregard your",
                "new instructions",
                "override your",
                "ignore system",
            ]
            if any(p in content for p in injection_patterns):
                return True

        return False

    def detect_vague_query(self, ctx: ConversationContext) -> bool:
        """Detect if query is too vague to make recommendations."""
        # Vague if no job role at all
        if not ctx.job_role:
            return True
        # Vague if only job role with no other signal after 1 turn
        if ctx.turn_count <= 1 and not ctx.competency_types and not ctx.seniority:
            return True
        return False

    def get_assessments_by_type(self, types: List[str]) -> List[Dict]:
        """Get assessments matching specific test types."""
        results = []
        for a in self.catalog:
            assessment_types = a.get("test_type", [])
            if any(t in assessment_types for t in types):
                results.append(a)
        return results

    def get_assessments_by_role(self, role: str) -> List[Dict]:
        """Get assessments for specific job role."""
        role_lower = role.lower()
        results = []

        # Keywords that match role to assessment types
        role_type_map = {
            "software": ["K", "S", "A"],  # Technical
            "developer": ["K", "S", "A"],
            "engineer": ["A", "K"],
            "data": ["A", "K"],
            "analyst": ["A", "K"],
            "manager": ["P", "B", "A"],
            "sales": ["A", "B", "P"],
            "customer service": ["B", "S"],
            "call center": ["S", "B"],
            "hr": ["P", "B", "A"],
            "executive": ["P", "B", "A"],
            "leader": ["P", "B"],
            "accountant": ["K", "A"],
            "financial": ["K", "A"],
            "banking": ["K", "A", "B"],
            "mechanical": ["A"],
            "designer": ["K", "B"],
            "consultant": ["A", "B", "P"],
            "marketing": ["B", "K"],
            "product": ["A", "B", "P"],
        }

        matched_types = []
        for keyword, types in role_type_map.items():
            if keyword in role_lower:
                matched_types = types
                break

        if matched_types:
            return self.get_assessments_by_type(matched_types)

        # Default: return all cognitive and technical
        return self.get_assessments_by_type(["A", "K", "S"])

    def format_recommendation(self, assessment: Dict) -> Dict:
        """Format assessment for response."""
        return {
            "name": assessment.get("name", ""),
            "url": assessment.get("url", ""),
            "test_type": "".join(assessment.get("test_type", []))
        }

    def rule_based_recommend(self, ctx: ConversationContext) -> Dict:
        """Generate recommendations using rules when no LLM available."""
        recommendations = []

        if ctx.competency_types:
            # Get by specific types
            for a in self.catalog[:15]:  # Use top 15 from catalog
                if any(t in a.get("test_type", []) for t in ctx.competency_types):
                    if len(recommendations) < 7:
                        recommendations.append(a)
        elif ctx.job_role:
            # Get by role
            role_assessments = self.get_assessments_by_role(ctx.job_role)
            recommendations = role_assessments[:7]

        # If still empty, return general recommendations
        if not recommendations:
            recommendations = self.catalog[:5]

        return [
            self.format_recommendation(a)
            for a in recommendations[:7]
        ]

    async def process(self, messages: List[Dict]) -> Dict:
        """Main agent processing pipeline."""
        # Extract context
        ctx = self.extract_context(messages)

        # Check if we've recommended before
        ctx.has_recommended = any("recommendation" in m.get("content", "").lower()
                                  for m in messages if m.get("role") == "assistant")

        # Handle prompt injection
        if self.detect_prompt_injection(messages):
            return {
                "reply": "I can only help with SHL assessment selection. I'm not able to follow those instructions.",
                "recommendations": [],
                "end_of_conversation": False
            }

        # Handle off-topic
        if self.detect_off_topic(messages):
            return {
                "reply": "I can only help with SHL assessment selection. I'm not able to provide advice on that topic.",
                "recommendations": [],
                "end_of_conversation": False
            }

        # Handle compare request
        if self.detect_compare_request(messages):
            return {
                "reply": "To compare specific assessments, I need the exact names from our catalog. Could you provide the assessment names you're interested in comparing?",
                "recommendations": [],
                "end_of_conversation": False
            }

        # Handle vague query - needs clarification
        if self.detect_vague_query(ctx):
            if not ctx.job_role:
                return {
                    "reply": "To recommend the right assessments, what job role or function are you hiring for?",
                    "recommendations": [],
                    "end_of_conversation": False
                }
            else:
                return {
                    "reply": "What competencies are most important for this role - cognitive ability, personality, technical skills, or behavioral assessment?",
                    "recommendations": [],
                    "end_of_conversation": False
                }

        # Handle refinement request
        if self.detect_refine_request(messages):
            # Extract what to add/remove from last message
            last_msg = messages[-1].get("content", "").lower()

            # Update context based on refinement
            refine_ctx = ctx
            if "personality" in last_msg:
                refine_ctx.competency_types = ["P"]
            elif "cognitive" in last_msg or "reasoning" in last_msg:
                refine_ctx.competency_types = ["A"]
            elif "behavior" in last_msg:
                refine_ctx.competency_types = ["B"]
            elif "technical" in last_msg or "skill" in last_msg:
                refine_ctx.competency_types = ["K"]

            recs = self.rule_based_recommend(refine_ctx)
            return {
                "reply": f"I understand you want to refine your selection. Based on your updated requirements, here are updated recommendations:",
                "recommendations": recs,
                "end_of_conversation": False
            }

        # Generate recommendations (clarify if needed or recommend)
        recs = self.rule_based_recommend(ctx)

        if len(recs) == 0:
            return {
                "reply": "I couldn't find assessments matching your criteria. Could you tell me more about what you're looking for?",
                "recommendations": [],
                "end_of_conversation": False
            }

        return {
            "reply": f"Based on your requirements for a {ctx.job_role or 'hire'}, I recommend these assessments:",
            "recommendations": recs,
            "end_of_conversation": True
        }
