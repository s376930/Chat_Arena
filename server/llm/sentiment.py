"""Simple sentiment analysis for conversation messages."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    sentiment: str  # "positive", "negative", "neutral", "mixed"
    confidence: float  # 0.0 to 1.0
    indicators: list[str]  # What led to this classification


class SentimentAnalyzer:
    """Simple keyword-based sentiment analyzer for conversations."""

    # Positive indicators
    POSITIVE_PATTERNS = [
        (r"\b(great|awesome|amazing|wonderful|fantastic|excellent)\b", "strong_positive"),
        (r"\b(good|nice|cool|interesting|love|like|enjoy)\b", "positive"),
        (r"\b(thanks|thank you|appreciate)\b", "gratitude"),
        (r"\b(haha|lol|hehe|😄|😊|🙂|😀)\b", "humor"),
        (r"\b(agree|yes|exactly|right|true)\b", "agreement"),
        (r"[!]{1,3}(?!\?)", "excitement"),
    ]

    # Negative indicators
    NEGATIVE_PATTERNS = [
        (r"\b(terrible|horrible|awful|worst|hate)\b", "strong_negative"),
        (r"\b(bad|annoying|frustrating|boring|disappointed)\b", "negative"),
        (r"\b(don't like|not good|not great)\b", "mild_negative"),
        (r"\b(sorry|apologize)\b", "apology"),
        (r"\b(confused|don't understand|unclear)\b", "confusion"),
        (r"\b(sad|upset|worried|anxious)\b", "distress"),
        (r"[?]{2,}", "uncertainty"),
    ]

    # Engagement indicators
    ENGAGEMENT_PATTERNS = [
        (r"\?$", "question"),
        (r"\b(what|how|why|when|where|who)\b.*\?", "inquiry"),
        (r"\b(tell me|share|explain|describe)\b", "request"),
        (r"\b(think|believe|feel|wonder)\b", "reflection"),
    ]

    # Disengagement indicators
    DISENGAGEMENT_PATTERNS = [
        (r"^(ok|okay|sure|fine|mhm|hmm)\.?$", "minimal_response"),
        (r"^(yes|no|maybe)\.?$", "short_response"),
        (r"\b(whatever|idk|dunno)\b", "dismissive"),
        (r"^\s*$", "empty"),
    ]

    def analyze(self, text: str) -> SentimentResult:
        """Analyze the sentiment of a message."""
        if not text or not text.strip():
            return SentimentResult(
                sentiment="neutral",
                confidence=0.5,
                indicators=["empty_message"],
            )

        text_lower = text.lower().strip()
        indicators = []
        positive_score = 0.0
        negative_score = 0.0
        engagement_score = 0.0

        # Check positive patterns
        for pattern, indicator in self.POSITIVE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                indicators.append(indicator)
                if "strong" in indicator:
                    positive_score += 2.0
                else:
                    positive_score += 1.0

        # Check negative patterns
        for pattern, indicator in self.NEGATIVE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                indicators.append(indicator)
                if "strong" in indicator:
                    negative_score += 2.0
                else:
                    negative_score += 1.0

        # Check engagement
        for pattern, indicator in self.ENGAGEMENT_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                indicators.append(indicator)
                engagement_score += 1.0

        # Check disengagement
        for pattern, indicator in self.DISENGAGEMENT_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                indicators.append(indicator)
                engagement_score -= 1.0

        # Determine sentiment
        sentiment, confidence = self._calculate_sentiment(
            positive_score, negative_score, engagement_score, len(text)
        )

        return SentimentResult(
            sentiment=sentiment,
            confidence=confidence,
            indicators=indicators,
        )

    def _calculate_sentiment(
        self,
        positive: float,
        negative: float,
        engagement: float,
        text_length: int,
    ) -> tuple[str, float]:
        """Calculate final sentiment and confidence."""
        total = positive + negative

        if total == 0:
            # No clear indicators
            if engagement > 0:
                return "neutral_engaged", 0.6
            elif engagement < 0:
                return "neutral_disengaged", 0.6
            else:
                return "neutral", 0.5

        # Calculate ratio
        if positive > negative * 1.5:
            sentiment = "positive"
            confidence = min(0.9, 0.5 + (positive - negative) * 0.1)
        elif negative > positive * 1.5:
            sentiment = "negative"
            confidence = min(0.9, 0.5 + (negative - positive) * 0.1)
        elif positive > 0 and negative > 0:
            sentiment = "mixed"
            confidence = 0.6
        else:
            sentiment = "neutral"
            confidence = 0.5

        # Adjust for engagement
        if engagement > 2:
            if sentiment == "positive":
                sentiment = "enthusiastic"
            elif sentiment == "neutral":
                sentiment = "engaged"
        elif engagement < -1:
            if sentiment == "neutral":
                sentiment = "disengaged"

        return sentiment, confidence

    def get_trend(self, sentiments: list[str]) -> str:
        """Analyze the trend of recent sentiments."""
        if len(sentiments) < 2:
            return "stable"

        positive_sentiments = {"positive", "enthusiastic", "engaged"}
        negative_sentiments = {"negative", "disengaged", "frustrated"}

        # Count recent vs older sentiments
        recent = sentiments[-2:]
        older = sentiments[:-2] if len(sentiments) > 2 else []

        recent_positive = sum(1 for s in recent if s in positive_sentiments)
        recent_negative = sum(1 for s in recent if s in negative_sentiments)
        older_positive = sum(1 for s in older if s in positive_sentiments)
        older_negative = sum(1 for s in older if s in negative_sentiments)

        # Determine trend
        if recent_positive > recent_negative and recent_positive > older_positive:
            return "improving"
        elif recent_negative > recent_positive and recent_negative > older_negative:
            return "declining"
        else:
            return "stable"
