"""Aggregation Engine for synthesizing all agent outputs."""
import json
from datetime import datetime
from typing import Optional, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base_agent import AgentResult
from backend.settings import SettingsManager
from backend.utils.anthropic_client import get_anthropic_client
from backend.utils.schemas import (
    AgentOutput,
    AggregatedInsightOutput,
    Outlook,
    RiskAssessment,
)
from backend.database import AggregatedInsight, AgentWeight

logger = structlog.get_logger()


class AggregationEngine:
    """
    Aggregation Engine that synthesizes outputs from all agents.

    Responsibilities:
    - Collect and validate agent outputs
    - Weight agents based on historical performance
    - Resolve conflicts between agents
    - Generate final recommendations
    - Apply risk management decisions
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._settings: Optional[SettingsManager] = None
        self._logger = logger.bind(component="aggregation_engine")

    @property
    def settings(self) -> SettingsManager:
        """Get settings manager."""
        if self._settings is None:
            self._settings = SettingsManager(self.db)
        return self._settings

    async def aggregate(
        self,
        agent_outputs: dict[str, AgentResult],
        risk_assessment: Optional[RiskAssessment] = None,
    ) -> AggregatedInsightOutput:
        """
        Aggregate outputs from all agents into a final insight.

        Args:
            agent_outputs: Dict of agent_id -> AgentResult
            risk_assessment: Optional risk assessment with veto power

        Returns:
            AggregatedInsightOutput with final recommendations
        """
        self._logger.info(
            "Starting aggregation",
            agent_count=len(agent_outputs),
            has_risk_assessment=risk_assessment is not None,
        )

        # Filter to successful outputs only
        valid_outputs = {
            agent_id: result.output
            for agent_id, result in agent_outputs.items()
            if result.success and result.output is not None
        }

        if not valid_outputs:
            self._logger.warning("No valid agent outputs to aggregate")
            return self._empty_insight("No valid agent outputs available")

        # Get agent weights
        weights = await self._get_agent_weights(list(valid_outputs.keys()))

        # Calculate weighted outlook
        weighted_outlook, confidence, conflicts = self._calculate_weighted_outlook(
            valid_outputs, weights
        )

        # Build prompt for Claude to synthesize
        synthesis = await self._synthesize_with_claude(
            valid_outputs, weighted_outlook, conflicts
        )

        # Apply risk veto if needed
        vetoed = False
        veto_reason = None
        if risk_assessment and not risk_assessment.approved:
            vetoed = True
            veto_reason = risk_assessment.veto_reason

        # Create the final insight
        insight = AggregatedInsightOutput(
            timestamp=datetime.utcnow(),
            overall_outlook=weighted_outlook,
            confidence=confidence,
            agent_outputs={
                agent_id: output
                for agent_id, output in valid_outputs.items()
            },
            conflicts=conflicts,
            resolution_reasoning=synthesis.get("reasoning", ""),
            final_recommendations=synthesis.get("recommendations", []),
            risk_assessment=risk_assessment,
            vetoed=vetoed,
            veto_reason=veto_reason,
        )

        # Save to database
        await self._save_insight(insight)

        self._logger.info(
            "Aggregation completed",
            outlook=weighted_outlook.value,
            confidence=confidence,
            vetoed=vetoed,
        )

        return insight

    async def _get_agent_weights(self, agent_ids: list[str]) -> dict[str, float]:
        """Get weights for each agent based on historical performance."""
        from sqlalchemy import select

        # Get weighting method from settings
        method = await self.settings.get(
            "aggregation_weighting_method",
            category="agent_config",
            default="equal",
        )

        if method == "equal":
            return {agent_id: 1.0 for agent_id in agent_ids}

        # Get weights from database
        weights = {}
        for agent_id in agent_ids:
            result = await self.db.execute(
                select(AgentWeight).where(AgentWeight.agent_id == agent_id)
            )
            weight_record = result.scalar_one_or_none()
            if weight_record:
                weights[agent_id] = weight_record.weight
            else:
                weights[agent_id] = 1.0

        return weights

    def _calculate_weighted_outlook(
        self,
        outputs: dict[str, AgentOutput],
        weights: dict[str, float],
    ) -> tuple[Outlook, float, list[dict]]:
        """
        Calculate weighted outlook from all agents.

        Returns:
            Tuple of (outlook, confidence, conflicts)
        """
        outlook_scores = {
            Outlook.BEARISH: 0.0,
            Outlook.NEUTRAL: 0.0,
            Outlook.BULLISH: 0.0,
        }
        total_weight = 0.0
        conflicts = []

        for agent_id, output in outputs.items():
            weight = weights.get(agent_id, 1.0)
            confidence = output.forecast.confidence
            weighted_score = weight * confidence

            outlook_scores[output.forecast.outlook] += weighted_score
            total_weight += weighted_score

        # Normalize scores
        if total_weight > 0:
            for outlook in outlook_scores:
                outlook_scores[outlook] /= total_weight

        # Determine winning outlook
        winning_outlook = max(outlook_scores, key=outlook_scores.get)
        confidence = outlook_scores[winning_outlook]

        # Detect conflicts (agents disagree significantly)
        outlooks_present = set(o.forecast.outlook for o in outputs.values())
        if len(outlooks_present) > 1:
            bearish_agents = [
                aid for aid, o in outputs.items()
                if o.forecast.outlook == Outlook.BEARISH
            ]
            bullish_agents = [
                aid for aid, o in outputs.items()
                if o.forecast.outlook == Outlook.BULLISH
            ]
            if bearish_agents and bullish_agents:
                conflicts.append({
                    "type": "outlook_disagreement",
                    "bearish": bearish_agents,
                    "bullish": bullish_agents,
                    "resolution": f"Weighted average favors {winning_outlook.value}",
                })

        return winning_outlook, confidence, conflicts

    async def _synthesize_with_claude(
        self,
        outputs: dict[str, AgentOutput],
        weighted_outlook: Outlook,
        conflicts: list[dict],
    ) -> dict[str, Any]:
        """Use Claude to synthesize all agent outputs into recommendations."""
        model = await self.settings.get(
            "aggregation_model",
            category="agent_config",
            default="claude-sonnet-4-5-20250929",
        )

        # Build synthesis prompt
        prompt = self._build_synthesis_prompt(outputs, weighted_outlook, conflicts)

        client = get_anthropic_client()
        try:
            response = await client.complete(
                model=model,
                system="""You are a senior investment strategist synthesizing multiple analyst reports.
Your job is to:
1. Identify common themes and agreements
2. Resolve conflicts between analysts
3. Generate actionable recommendations
4. Explain your reasoning clearly

Respond with JSON containing:
- reasoning: explanation of how you resolved conflicts and reached conclusions
- recommendations: list of actionable recommendations
- key_themes: common themes across all analyses""",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )

            if response.get("is_mock"):
                return {
                    "reasoning": "Mock synthesis - API key not configured",
                    "recommendations": ["Configure API key for real synthesis"],
                    "key_themes": ["mock data"],
                }

            # Parse response
            try:
                content = response["content"]
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    content = content[start:end].strip()
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "reasoning": response["content"],
                    "recommendations": [],
                    "key_themes": [],
                }

        except Exception as e:
            self._logger.error("Synthesis failed", error=str(e))
            return {
                "reasoning": f"Synthesis failed: {str(e)}",
                "recommendations": [],
                "key_themes": [],
            }

    def _build_synthesis_prompt(
        self,
        outputs: dict[str, AgentOutput],
        weighted_outlook: Outlook,
        conflicts: list[dict],
    ) -> str:
        """Build the synthesis prompt."""
        prompt = "## Agent Analysis Reports\n\n"

        for agent_id, output in outputs.items():
            prompt += f"### {agent_id.replace('_', ' ').title()}\n"
            prompt += f"- Outlook: {output.forecast.outlook.value}\n"
            prompt += f"- Confidence: {output.forecast.confidence:.0%}\n"
            prompt += f"- Timeframe: {output.forecast.timeframe.value}\n"
            prompt += f"- Reasoning: {output.reasoning[:500]}...\n"
            prompt += f"- Key Factors: {', '.join(output.key_factors[:3])}\n\n"

        prompt += f"## Weighted Consensus: {weighted_outlook.value.upper()}\n\n"

        if conflicts:
            prompt += "## Conflicts Detected\n"
            for conflict in conflicts:
                prompt += f"- {conflict.get('type')}: {conflict.get('resolution')}\n"
            prompt += "\n"

        prompt += """
## Task

Synthesize these analyses and provide:
1. Your reasoning for the final outlook
2. 3-5 actionable recommendations
3. Key themes across all analyses

Respond with valid JSON."""

        return prompt

    async def _save_insight(self, insight: AggregatedInsightOutput) -> None:
        """Save aggregated insight to database."""
        try:
            db_insight = AggregatedInsight(
                timestamp=insight.timestamp,
                overall_outlook=insight.overall_outlook.value,
                confidence=insight.confidence,
                agent_outputs={
                    aid: out.model_dump() for aid, out in insight.agent_outputs.items()
                },
                conflicts=insight.conflicts,
                resolution_reasoning=insight.resolution_reasoning,
                final_recommendations=insight.final_recommendations,
                risk_assessment=insight.risk_assessment.model_dump() if insight.risk_assessment else None,
                vetoed=insight.vetoed,
                veto_reason=insight.veto_reason,
            )
            self.db.add(db_insight)
            await self.db.commit()
            self._logger.info("Insight saved", insight_id=db_insight.id)
        except Exception as e:
            self._logger.error("Failed to save insight", error=str(e))
            await self.db.rollback()

    def _empty_insight(self, reason: str) -> AggregatedInsightOutput:
        """Return an empty insight when aggregation fails."""
        return AggregatedInsightOutput(
            timestamp=datetime.utcnow(),
            overall_outlook=Outlook.NEUTRAL,
            confidence=0.0,
            agent_outputs={},
            conflicts=[],
            resolution_reasoning=reason,
            final_recommendations=[],
            vetoed=False,
        )
