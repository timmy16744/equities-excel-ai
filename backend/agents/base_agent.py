"""Base agent abstract class for all specialized agents."""
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Any

import redis.asyncio as redis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AgentPrediction
from backend.settings import SettingsManager
from backend.utils.anthropic_client import AnthropicClient, get_anthropic_client
from backend.utils.schemas import AgentOutput, Outlook, Timeframe, AgentForecast

logger = structlog.get_logger()


class AgentResult:
    """Result wrapper for agent execution."""

    def __init__(
        self,
        success: bool,
        output: Optional[AgentOutput] = None,
        error: Optional[str] = None,
        cached: bool = False,
    ) -> None:
        self.success = success
        self.output = output
        self.error = error
        self.cached = cached
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output.model_dump() if self.output else None,
            "error": self.error,
            "cached": self.cached,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseAgent(ABC):
    """
    Abstract base class for all analysis agents.

    Provides common functionality:
    - Settings integration
    - Claude API access
    - Redis caching
    - Database persistence
    - Structured logging
    - Error handling

    Subclasses must implement:
    - agent_id: Unique identifier for the agent
    - fetch_data(): Fetch required data from APIs
    - build_prompt(): Build the Claude prompt
    - parse_response(): Parse Claude's response
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: Optional[redis.Redis] = None,
    ) -> None:
        """
        Initialize the base agent.

        Args:
            db: Async database session
            redis_client: Optional Redis client for caching
        """
        self.db = db
        self.redis = redis_client
        self._settings: Optional[SettingsManager] = None
        self._claude: Optional[AnthropicClient] = None
        self._logger = logger.bind(agent_id=self.agent_id)

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Unique identifier for this agent."""
        pass

    @property
    def settings(self) -> SettingsManager:
        """Get settings manager."""
        if self._settings is None:
            self._settings = SettingsManager(self.db)
        return self._settings

    @property
    def claude(self) -> AnthropicClient:
        """Get Claude client."""
        if self._claude is None:
            self._claude = get_anthropic_client()
        return self._claude

    async def is_enabled(self) -> bool:
        """Check if this agent is enabled in settings."""
        return await self.settings.get(
            f"{self.agent_id}_enabled",
            category="agent_config",
            default=True,
        )

    async def get_model(self) -> str:
        """Get the Claude model to use for this agent."""
        return await self.settings.get(
            f"{self.agent_id}_model",
            category="agent_config",
            default="claude-sonnet-4-5-20250929",
        )

    async def get_max_tokens(self) -> int:
        """Get max tokens setting for this agent."""
        return await self.settings.get(
            f"{self.agent_id}_max_tokens",
            category="agent_config",
            default=4000,
        )

    async def get_cache_ttl(self) -> int:
        """Get cache TTL in seconds for this agent."""
        return await self.settings.get(
            f"{self.agent_id}_cache_ttl",
            category="agent_config",
            default=3600,
        )

    @abstractmethod
    async def fetch_data(self) -> dict[str, Any]:
        """
        Fetch required data from external APIs.

        Returns:
            Dict containing all data needed for analysis
        """
        pass

    @abstractmethod
    def build_prompt(self, data: dict[str, Any]) -> str:
        """
        Build the prompt for Claude based on fetched data.

        Args:
            data: Data fetched by fetch_data()

        Returns:
            Complete prompt string
        """
        pass

    @abstractmethod
    def parse_response(self, response: str, data: dict[str, Any]) -> AgentOutput:
        """
        Parse Claude's response into structured output.

        Args:
            response: Raw response from Claude
            data: Original data for context

        Returns:
            Structured AgentOutput
        """
        pass

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.

        Override in subclasses for specialized behavior.
        """
        return f"""You are an expert {self.agent_id.replace('_', ' ')} analyst.
Your task is to analyze the provided data and generate a market outlook.

You must respond with a valid JSON object containing:
- outlook: "bearish", "neutral", or "bullish"
- confidence: a number between 0 and 1
- timeframe: "1week", "1month", "3month", or "1year"
- reasoning: detailed explanation of your analysis
- key_factors: list of key factors influencing your outlook
- uncertainties: list of uncertainties or risks
- specific_predictions: optional dict with specific predictions

Be objective and data-driven. Acknowledge uncertainties.
Base your analysis only on the provided data."""

    async def run(self, force_refresh: bool = False) -> AgentResult:
        """
        Execute the agent's analysis pipeline.

        Args:
            force_refresh: If True, bypass cache

        Returns:
            AgentResult with output or error
        """
        self._logger.info("Starting agent run", force_refresh=force_refresh)

        # Check if enabled
        if not await self.is_enabled():
            self._logger.info("Agent is disabled")
            return AgentResult(
                success=False,
                error=f"Agent {self.agent_id} is disabled in settings",
            )

        # Check cache
        if not force_refresh:
            cached = await self._get_cached_output()
            if cached:
                self._logger.info("Returning cached output")
                return AgentResult(success=True, output=cached, cached=True)

        try:
            # Fetch data
            self._logger.info("Fetching data")
            data = await self.fetch_data()

            if not data:
                return AgentResult(
                    success=False,
                    error="Failed to fetch required data",
                )

            # Build prompt and call Claude
            prompt = self.build_prompt(data)
            model = await self.get_model()
            max_tokens = await self.get_max_tokens()

            self._logger.info("Calling Claude", model=model)
            response = await self.claude.complete(
                model=model,
                system=self.get_system_prompt(),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )

            # Handle mock response
            if response.get("is_mock"):
                self._logger.warning("Using mock response (no API key)")
                output = self._create_mock_output()
            else:
                # Parse response
                output = self.parse_response(response["content"], data)

            # Cache the output
            await self._cache_output(output)

            # Save to database
            await self._save_prediction(output)

            self._logger.info(
                "Agent run completed",
                outlook=output.forecast.outlook,
                confidence=output.forecast.confidence,
            )

            return AgentResult(success=True, output=output)

        except Exception as e:
            self._logger.error("Agent run failed", error=str(e))
            return AgentResult(success=False, error=str(e))

    async def _get_cached_output(self) -> Optional[AgentOutput]:
        """Get cached output if available and not expired."""
        if not self.redis:
            return None

        try:
            cache_key = f"agent:{self.agent_id}:output"
            cached = await self.redis.get(cache_key)

            if cached:
                data = json.loads(cached)
                return AgentOutput(**data)
        except Exception as e:
            self._logger.warning("Cache read failed", error=str(e))

        return None

    async def _cache_output(self, output: AgentOutput) -> None:
        """Cache the agent output."""
        if not self.redis:
            return

        try:
            cache_key = f"agent:{self.agent_id}:output"
            ttl = await self.get_cache_ttl()
            await self.redis.setex(
                cache_key,
                ttl,
                output.model_dump_json(),
            )
        except Exception as e:
            self._logger.warning("Cache write failed", error=str(e))

    async def _save_prediction(self, output: AgentOutput) -> None:
        """Save prediction to database."""
        try:
            prediction = AgentPrediction(
                agent_id=output.agent_id,
                timestamp=output.timestamp,
                outlook=output.forecast.outlook.value,
                confidence=output.forecast.confidence,
                timeframe=output.forecast.timeframe.value,
                specific_predictions=output.forecast.specific_predictions,
                reasoning=output.reasoning,
                key_factors=output.key_factors,
                uncertainties=output.uncertainties,
                data_sources=output.data_sources,
                supporting_evidence=output.supporting_evidence,
            )
            self.db.add(prediction)
            await self.db.commit()
            self._logger.info("Prediction saved", prediction_id=prediction.id)
        except Exception as e:
            self._logger.error("Failed to save prediction", error=str(e))
            await self.db.rollback()

    def _create_mock_output(self) -> AgentOutput:
        """Create a mock output when API is not available."""
        return AgentOutput(
            agent_id=self.agent_id,
            timestamp=datetime.utcnow(),
            forecast=AgentForecast(
                outlook=Outlook.NEUTRAL,
                confidence=0.5,
                timeframe=Timeframe.ONE_MONTH,
                specific_predictions={"mock": True},
            ),
            reasoning="This is a mock response. Configure API key for real analysis.",
            key_factors=["Mock response - no API key configured"],
            uncertainties=["All predictions are placeholder values"],
            data_sources=["None - mock mode"],
        )

    def _parse_json_response(self, response: str) -> dict:
        """
        Extract JSON from Claude's response.

        Handles cases where response is wrapped in markdown code blocks.
        """
        # Try to find JSON in code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()

        return json.loads(response)
