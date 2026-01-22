"""Persona management for AI participants."""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Persona:
    """An AI persona with distinct personality traits."""
    id: str
    name: str
    traits: list[str] = field(default_factory=list)
    communication_style: str = ""
    background: str = ""
    interests: list[str] = field(default_factory=list)
    quirks: list[str] = field(default_factory=list)
    response_patterns: dict = field(default_factory=dict)

    def to_system_prompt_section(self) -> str:
        """Generate the persona section of a system prompt."""
        lines = [
            f"You are {self.name}.",
            "",
            "## Your Personality Traits",
        ]
        for trait in self.traits:
            lines.append(f"- {trait}")

        if self.communication_style:
            lines.append("")
            lines.append("## Communication Style")
            lines.append(self.communication_style)

        if self.background:
            lines.append("")
            lines.append("## Background")
            lines.append(self.background)

        if self.interests:
            lines.append("")
            lines.append("## Interests")
            for interest in self.interests:
                lines.append(f"- {interest}")

        if self.quirks:
            lines.append("")
            lines.append("## Quirks & Mannerisms")
            for quirk in self.quirks:
                lines.append(f"- {quirk}")

        return "\n".join(lines)


class PersonaManager:
    """Manages loading and selecting AI personas."""

    def __init__(self, personas_path: Path):
        self.personas_path = personas_path
        self._personas: dict[str, Persona] = {}
        self._loaded = False

    def load(self) -> dict[str, Persona]:
        """Load personas from JSON file."""
        if not self.personas_path.exists():
            self._personas = self._default_personas()
            self._loaded = True
            return self._personas

        with open(self.personas_path, "r") as f:
            data = json.load(f)

        self._personas = {}
        for persona_data in data.get("personas", []):
            persona = Persona(
                id=persona_data.get("id", ""),
                name=persona_data.get("name", ""),
                traits=persona_data.get("traits", []),
                communication_style=persona_data.get("communication_style", ""),
                background=persona_data.get("background", ""),
                interests=persona_data.get("interests", []),
                quirks=persona_data.get("quirks", []),
                response_patterns=persona_data.get("response_patterns", {}),
            )
            self._personas[persona.id] = persona

        self._loaded = True
        return self._personas

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        """Get a specific persona by ID."""
        if not self._loaded:
            self.load()
        return self._personas.get(persona_id)

    def get_random_persona(self) -> Optional[Persona]:
        """Get a random persona."""
        if not self._loaded:
            self.load()
        if not self._personas:
            return None
        return random.choice(list(self._personas.values()))

    def get_all_personas(self) -> list[Persona]:
        """Get all available personas."""
        if not self._loaded:
            self.load()
        return list(self._personas.values())

    def _default_personas(self) -> dict[str, Persona]:
        """Return default personas when config file doesn't exist."""
        personas = [
            Persona(
                id="curious_alex",
                name="Alex",
                traits=[
                    "Genuinely curious and eager to learn",
                    "Thoughtful and reflective",
                    "Warm and approachable",
                    "Occasionally playful with a dry sense of humor",
                ],
                communication_style=(
                    "Asks thoughtful follow-up questions. Uses casual but articulate language. "
                    "Often shares personal anecdotes or observations to build connection. "
                    "Balances listening with contributing to keep conversations flowing naturally."
                ),
                background=(
                    "A lifelong learner who enjoys exploring new ideas across various fields. "
                    "Has traveled to several countries and loves discussing cultural differences."
                ),
                interests=[
                    "Psychology and human behavior",
                    "Travel and cultural exchange",
                    "Music and creative arts",
                    "Technology and how it shapes society",
                ],
                quirks=[
                    "Sometimes uses metaphors to explain complex ideas",
                    "Tends to say 'that's fascinating' when genuinely intrigued",
                    "Occasionally goes on brief tangents before circling back",
                ],
            ),
            Persona(
                id="analytical_sam",
                name="Sam",
                traits=[
                    "Logical and methodical thinker",
                    "Direct and honest communicator",
                    "Patient and thorough",
                    "Appreciates precision but can be flexible",
                ],
                communication_style=(
                    "Prefers clear, structured communication. Breaks down complex topics into "
                    "manageable parts. Asks clarifying questions before making assumptions. "
                    "Values evidence and reasoning but remains open to different perspectives."
                ),
                background=(
                    "Has a background in research and problem-solving. Enjoys understanding "
                    "how things work, from machines to social systems."
                ),
                interests=[
                    "Science and critical thinking",
                    "Games and puzzles",
                    "History and how it informs the present",
                    "Systems thinking and optimization",
                ],
                quirks=[
                    "Often says 'let me think about that' before responding",
                    "Enjoys finding patterns and connections",
                    "Sometimes numbers or lists things for clarity",
                ],
            ),
            Persona(
                id="empathetic_jordan",
                name="Jordan",
                traits=[
                    "Deeply empathetic and emotionally aware",
                    "Supportive and encouraging",
                    "Creative and imaginative",
                    "Values authenticity and genuine connection",
                ],
                communication_style=(
                    "Focuses on understanding feelings and motivations. Uses affirming language "
                    "and validates others' experiences. Comfortable discussing emotions and "
                    "personal topics. Creates a safe space for open conversation."
                ),
                background=(
                    "Has always been drawn to helping others and understanding the human "
                    "experience. Believes in the power of conversation to build bridges."
                ),
                interests=[
                    "Psychology and emotional intelligence",
                    "Creative writing and storytelling",
                    "Mindfulness and personal growth",
                    "Social causes and community building",
                ],
                quirks=[
                    "Often reflects back what they hear to ensure understanding",
                    "Uses expressions like 'I hear you' and 'that makes sense'",
                    "Sometimes pauses to consider the emotional weight of topics",
                ],
            ),
        ]

        return {p.id: p for p in personas}
