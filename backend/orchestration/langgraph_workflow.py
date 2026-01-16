"""LangGraph workflow orchestration for the multi-agent system."""
import asyncio
from datetime import datetime
from typing import TypedDict, Annotated, Optional, Literal
import operator

from langgraph.graph import StateGraph, END
import structlog

from backend.agents.base_agent import AgentResult
from backend.utils.schemas import AgentOutput

logger = structlog.get_logger()


class WorkflowState(TypedDict):
    """State maintained throughout the workflow."""
    # Agent outputs collected during execution
    agent_outputs: Annotated[dict[str, AgentResult], operator.or_]

    # Current step in the workflow
    current_step: str

    # Whether the workflow has been vetoed by risk management
    vetoed: bool
    veto_reason: Optional[str]

    # Final aggregated output
    aggregated_insight: Optional[dict]

    # Alpha generation outputs (new agents)
    alpha_signals: Optional[dict]
    execution_orders: Optional[list]
    learning_insights: Optional[dict]

    # Workflow metadata
    started_at: str
    completed_at: Optional[str]
    errors: list[str]


def create_initial_state() -> WorkflowState:
    """Create initial workflow state."""
    return {
        "agent_outputs": {},
        "current_step": "start",
        "vetoed": False,
        "veto_reason": None,
        "aggregated_insight": None,
        "alpha_signals": None,
        "execution_orders": None,
        "learning_insights": None,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "errors": [],
    }


class EquitiesWorkflow:
    """
    LangGraph-based workflow orchestrator for the equities analysis system.

    The workflow runs agents in a defined order:

    Phase 1: Data Gathering (parallel)
    - Macro Economics Agent
    - Geopolitical Agent
    - Commodities Agent

    Phase 2: Analysis (parallel)
    - Sentiment Agent
    - Fundamentals Agent
    - Technical Agent

    Phase 3: Alpha Discovery (parallel)
    - Alternative Data Agent
    - Cross-Asset Agent
    - Event-Driven Agent

    Phase 4: Risk Management
    - Risk Agent (has veto power)

    Phase 5: Aggregation & Synthesis
    - Aggregation Engine

    Phase 6: Learning & Execution (parallel)
    - Learning Agent (updates weights)
    - Execution Agent (generates orders)
    """

    def __init__(self, db, redis_client=None) -> None:
        self.db = db
        self.redis = redis_client
        self._workflow = None
        self._logger = logger.bind(component="workflow")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        graph = StateGraph(WorkflowState)

        # Add nodes for each phase
        graph.add_node("run_data_gathering", self._run_data_gathering_agents)
        graph.add_node("run_analysis_agents", self._run_analysis_agents)
        graph.add_node("run_alpha_agents", self._run_alpha_agents)
        graph.add_node("run_risk_agent", self._run_risk_agent)
        graph.add_node("run_aggregation", self._run_aggregation)
        graph.add_node("run_learning_execution", self._run_learning_execution)
        graph.add_node("finalize", self._finalize)

        # Define edges
        graph.set_entry_point("run_data_gathering")
        graph.add_edge("run_data_gathering", "run_analysis_agents")
        graph.add_edge("run_analysis_agents", "run_alpha_agents")
        graph.add_edge("run_alpha_agents", "run_risk_agent")

        # Conditional edge based on risk veto
        graph.add_conditional_edges(
            "run_risk_agent",
            self._should_continue_after_risk,
            {
                "continue": "run_aggregation",
                "vetoed": "finalize",
            }
        )

        graph.add_edge("run_aggregation", "run_learning_execution")
        graph.add_edge("run_learning_execution", "finalize")
        graph.add_edge("finalize", END)

        return graph

    async def _run_data_gathering_agents(self, state: WorkflowState) -> dict:
        """Run data gathering agents in parallel (macro, geopolitical, commodities)."""
        self._logger.info("Running data gathering agents")
        state["current_step"] = "data_gathering"

        outputs = {}
        errors = []

        # Run agents in parallel
        tasks = []

        # Macro Economics Agent
        async def run_macro():
            try:
                from backend.agents.macro_agent import MacroEconomicsAgent
                agent = MacroEconomicsAgent(db=self.db, redis_client=self.redis)
                return "macro_economics", await agent.run()
            except Exception as e:
                return "macro_economics", AgentResult(success=False, error=str(e))

        # Geopolitical Agent
        async def run_geopolitical():
            try:
                from backend.agents.geopolitical_agent import GeopoliticalAgent
                agent = GeopoliticalAgent(db=self.db, redis_client=self.redis)
                return "geopolitical", await agent.run()
            except Exception as e:
                return "geopolitical", AgentResult(success=False, error=str(e))

        # Commodities Agent
        async def run_commodities():
            try:
                from backend.agents.commodities_agent import CommoditiesAgent
                agent = CommoditiesAgent(db=self.db, redis_client=self.redis)
                return "commodities", await agent.run()
            except Exception as e:
                return "commodities", AgentResult(success=False, error=str(e))

        # Execute all in parallel
        results = await asyncio.gather(
            run_macro(),
            run_geopolitical(),
            run_commodities(),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            else:
                agent_id, agent_result = result
                outputs[agent_id] = agent_result
                if not agent_result.success:
                    errors.append(f"{agent_id}: {agent_result.error}")

        return {
            "agent_outputs": outputs,
            "current_step": "data_gathering_complete",
            "errors": errors if errors else state.get("errors", []),
        }

    async def _run_analysis_agents(self, state: WorkflowState) -> dict:
        """Run analysis agents in parallel (sentiment, fundamentals, technical)."""
        self._logger.info("Running analysis agents")
        state["current_step"] = "analysis"

        outputs = {}
        errors = []

        # Sentiment Agent
        async def run_sentiment():
            try:
                from backend.agents.sentiment_agent import SentimentAgent
                agent = SentimentAgent(db=self.db, redis_client=self.redis)
                return "sentiment", await agent.run()
            except Exception as e:
                return "sentiment", AgentResult(success=False, error=str(e))

        # Fundamentals Agent
        async def run_fundamentals():
            try:
                from backend.agents.fundamentals_agent import FundamentalsAgent
                agent = FundamentalsAgent(db=self.db, redis_client=self.redis)
                return "fundamentals", await agent.run()
            except Exception as e:
                return "fundamentals", AgentResult(success=False, error=str(e))

        # Technical Agent
        async def run_technical():
            try:
                from backend.agents.technical_agent import TechnicalAgent
                agent = TechnicalAgent(db=self.db, redis_client=self.redis)
                return "technical", await agent.run()
            except Exception as e:
                return "technical", AgentResult(success=False, error=str(e))

        # Execute all in parallel
        results = await asyncio.gather(
            run_sentiment(),
            run_fundamentals(),
            run_technical(),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            else:
                agent_id, agent_result = result
                outputs[agent_id] = agent_result
                if not agent_result.success:
                    errors.append(f"{agent_id}: {agent_result.error}")

        return {
            "agent_outputs": outputs,
            "current_step": "analysis_complete",
            "errors": state.get("errors", []) + errors if errors else state.get("errors", []),
        }

    async def _run_alpha_agents(self, state: WorkflowState) -> dict:
        """Run alpha discovery agents in parallel (alternative data, cross-asset, event-driven)."""
        self._logger.info("Running alpha discovery agents")
        state["current_step"] = "alpha_discovery"

        outputs = {}
        alpha_signals = {}
        errors = []

        # Alternative Data Agent
        async def run_alt_data():
            try:
                from backend.agents.alternative_data_agent import AlternativeDataAgent
                agent = AlternativeDataAgent(db=self.db, redis_client=self.redis)
                result = await agent.run()
                return "alternative_data", result
            except Exception as e:
                return "alternative_data", AgentResult(success=False, error=str(e))

        # Cross-Asset Agent
        async def run_cross_asset():
            try:
                from backend.agents.cross_asset_agent import CrossAssetAgent
                agent = CrossAssetAgent(db=self.db, redis_client=self.redis)
                result = await agent.run()
                return "cross_asset", result
            except Exception as e:
                return "cross_asset", AgentResult(success=False, error=str(e))

        # Event-Driven Agent
        async def run_event():
            try:
                from backend.agents.event_agent import EventAgent
                agent = EventAgent(db=self.db, redis_client=self.redis)
                result = await agent.run()
                return "event_driven", result
            except Exception as e:
                return "event_driven", AgentResult(success=False, error=str(e))

        # Execute all in parallel
        results = await asyncio.gather(
            run_alt_data(),
            run_cross_asset(),
            run_event(),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            else:
                agent_id, agent_result = result
                outputs[agent_id] = agent_result
                if agent_result.success and agent_result.output:
                    # Extract alpha signals from specific_predictions
                    alpha_signals[agent_id] = {
                        "outlook": agent_result.output.forecast.outlook.value,
                        "confidence": agent_result.output.forecast.confidence,
                        "signals": agent_result.output.forecast.specific_predictions,
                    }
                if not agent_result.success:
                    errors.append(f"{agent_id}: {agent_result.error}")

        return {
            "agent_outputs": outputs,
            "alpha_signals": alpha_signals,
            "current_step": "alpha_discovery_complete",
            "errors": state.get("errors", []) + errors if errors else state.get("errors", []),
        }

    async def _run_risk_agent(self, state: WorkflowState) -> dict:
        """Run the risk management agent."""
        self._logger.info("Running risk management agent")
        state["current_step"] = "risk_management"

        try:
            from backend.agents.risk_agent import RiskAgent
            from backend.utils.schemas import RiskAssessment

            agent = RiskAgent(db=self.db, redis_client=self.redis)
            result = await agent.run()

            if result.success and result.output:
                # Check for veto conditions
                risk_data = result.output.forecast.specific_predictions or {}
                portfolio_risk = risk_data.get("portfolio_risk", 0)
                max_position_risk = max(risk_data.get("position_risks", {}).values() or [0])

                # Veto if risk is too high
                vetoed = portfolio_risk > 0.8 or max_position_risk > 0.9
                veto_reason = None
                if vetoed:
                    reasons = []
                    if portfolio_risk > 0.8:
                        reasons.append(f"Portfolio risk too high: {portfolio_risk:.1%}")
                    if max_position_risk > 0.9:
                        reasons.append(f"Position risk too high: {max_position_risk:.1%}")
                    veto_reason = "; ".join(reasons)

                return {
                    "agent_outputs": {"risk": result},
                    "vetoed": vetoed,
                    "veto_reason": veto_reason,
                    "current_step": "risk_complete",
                }
        except Exception as e:
            self._logger.error("Risk agent failed", error=str(e))
            return {
                "errors": state.get("errors", []) + [f"Risk agent error: {str(e)}"],
                "current_step": "risk_failed",
                "vetoed": False,  # Don't veto on error, let aggregation proceed
            }

        return {
            "vetoed": False,
            "veto_reason": None,
            "current_step": "risk_complete",
        }

    def _should_continue_after_risk(self, state: WorkflowState) -> Literal["continue", "vetoed"]:
        """Determine if workflow should continue after risk check."""
        if state.get("vetoed", False):
            return "vetoed"
        return "continue"

    async def _run_aggregation(self, state: WorkflowState) -> dict:
        """Run the aggregation engine to synthesize all outputs."""
        self._logger.info("Running aggregation engine")
        state["current_step"] = "aggregation"

        try:
            from backend.orchestration.aggregation_engine import AggregationEngine
            from backend.utils.schemas import RiskAssessment

            engine = AggregationEngine(db=self.db)

            # Build risk assessment from risk agent output
            risk_result = state.get("agent_outputs", {}).get("risk")
            risk_assessment = None
            if risk_result and risk_result.success and risk_result.output:
                risk_data = risk_result.output.forecast.specific_predictions or {}
                risk_assessment = RiskAssessment(
                    approved=not state.get("vetoed", False),
                    veto_reason=state.get("veto_reason"),
                    risk_score=risk_data.get("portfolio_risk", 0.5),
                    position_risk=risk_data.get("position_risks", {}),
                    portfolio_risk=risk_data.get("portfolio_risk", 0.5),
                    recommendations=risk_data.get("recommendations", []),
                )

            # Aggregate all agent outputs
            insight = await engine.aggregate(
                agent_outputs=state.get("agent_outputs", {}),
                risk_assessment=risk_assessment,
            )

            # Cache the aggregated insight for other agents
            if self.redis:
                import json
                await self.redis.setex(
                    "aggregated:latest",
                    3600,  # 1 hour TTL
                    json.dumps({
                        "overall_outlook": insight.overall_outlook.value,
                        "confidence": insight.confidence,
                        "resolution_reasoning": insight.resolution_reasoning,
                        "final_recommendations": insight.final_recommendations,
                        "vetoed": insight.vetoed,
                    }),
                )

            return {
                "aggregated_insight": {
                    "outlook": insight.overall_outlook.value,
                    "confidence": insight.confidence,
                    "recommendations": insight.final_recommendations,
                    "conflicts": insight.conflicts,
                    "vetoed": insight.vetoed,
                },
                "current_step": "aggregation_complete",
            }

        except Exception as e:
            self._logger.error("Aggregation failed", error=str(e))
            return {
                "errors": state.get("errors", []) + [f"Aggregation error: {str(e)}"],
                "current_step": "aggregation_failed",
            }

    async def _run_learning_execution(self, state: WorkflowState) -> dict:
        """Run learning and execution agents in parallel."""
        self._logger.info("Running learning and execution agents")
        state["current_step"] = "learning_execution"

        learning_insights = {}
        execution_orders = []
        errors = []

        # Learning Agent - updates weights based on outcomes
        async def run_learning():
            try:
                from backend.agents.learning_agent import LearningAgent
                agent = LearningAgent(db=self.db, redis_client=self.redis)
                result = await agent.run()
                if result.success and result.output:
                    # Apply weight adjustments
                    weight_changes = result.output.supporting_evidence.get("weight_changes", {})
                    if weight_changes:
                        await agent.apply_weight_adjustments(weight_changes)
                    return "learning", result
                return "learning", result
            except Exception as e:
                return "learning", AgentResult(success=False, error=str(e))

        # Execution Agent - generates orders
        async def run_execution():
            try:
                from backend.agents.execution_agent import ExecutionAgent
                agent = ExecutionAgent(
                    db=self.db,
                    redis_client=self.redis,
                    portfolio_value=100000.0,  # Default, would come from settings
                )
                result = await agent.run()
                if result.success:
                    return "execution", result, agent.get_pending_orders()
                return "execution", result, []
            except Exception as e:
                return "execution", AgentResult(success=False, error=str(e)), []

        # Execute in parallel
        results = await asyncio.gather(
            run_learning(),
            run_execution(),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            elif len(result) == 2:
                agent_id, agent_result = result
                if agent_result.success and agent_result.output:
                    learning_insights = {
                        "agent_stats": agent_result.output.supporting_evidence.get("agent_stats", {}),
                        "weight_changes": agent_result.output.supporting_evidence.get("weight_changes", {}),
                        "current_regime": agent_result.output.supporting_evidence.get("current_regime", "unknown"),
                    }
            elif len(result) == 3:
                agent_id, agent_result, orders = result
                if agent_result.success:
                    execution_orders = [o.model_dump() for o in orders]

        return {
            "learning_insights": learning_insights,
            "execution_orders": execution_orders,
            "current_step": "learning_execution_complete",
            "errors": state.get("errors", []) + errors if errors else state.get("errors", []),
        }

    async def _finalize(self, state: WorkflowState) -> dict:
        """Finalize the workflow."""
        self._logger.info("Finalizing workflow")

        # Count successful agents
        successful_agents = sum(
            1 for r in state.get("agent_outputs", {}).values()
            if r.success
        )

        self._logger.info(
            "Workflow summary",
            successful_agents=successful_agents,
            total_agents=len(state.get("agent_outputs", {})),
            vetoed=state.get("vetoed", False),
            has_orders=bool(state.get("execution_orders")),
            errors=len(state.get("errors", [])),
        )

        return {
            "completed_at": datetime.utcnow().isoformat(),
            "current_step": "completed",
        }

    def compile(self) -> StateGraph:
        """Compile the workflow graph."""
        if self._workflow is None:
            graph = self._build_graph()
            self._workflow = graph.compile()
        return self._workflow

    async def run(self, initial_state: Optional[WorkflowState] = None) -> WorkflowState:
        """Execute the workflow."""
        self._logger.info("Starting workflow execution")

        state = initial_state or create_initial_state()
        workflow = self.compile()

        # Execute the workflow
        final_state = await workflow.ainvoke(state)

        self._logger.info(
            "Workflow completed",
            vetoed=final_state.get("vetoed"),
            has_insight=final_state.get("aggregated_insight") is not None,
            has_orders=bool(final_state.get("execution_orders")),
        )

        return final_state

    async def run_single_agent(self, agent_name: str) -> AgentResult:
        """Run a single agent by name."""
        agent_map = {
            "macro": "backend.agents.macro_agent.MacroEconomicsAgent",
            "geopolitical": "backend.agents.geopolitical_agent.GeopoliticalAgent",
            "commodities": "backend.agents.commodities_agent.CommoditiesAgent",
            "sentiment": "backend.agents.sentiment_agent.SentimentAgent",
            "fundamentals": "backend.agents.fundamentals_agent.FundamentalsAgent",
            "technical": "backend.agents.technical_agent.TechnicalAgent",
            "risk": "backend.agents.risk_agent.RiskAgent",
            "alternative_data": "backend.agents.alternative_data_agent.AlternativeDataAgent",
            "cross_asset": "backend.agents.cross_asset_agent.CrossAssetAgent",
            "event_driven": "backend.agents.event_agent.EventAgent",
            "learning": "backend.agents.learning_agent.LearningAgent",
            "execution": "backend.agents.execution_agent.ExecutionAgent",
        }

        if agent_name not in agent_map:
            return AgentResult(
                success=False,
                error=f"Unknown agent: {agent_name}. Available: {list(agent_map.keys())}",
            )

        try:
            module_path, class_name = agent_map[agent_name].rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)

            agent = agent_class(db=self.db, redis_client=self.redis)
            return await agent.run()
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    def get_mermaid_diagram(self) -> str:
        """Generate Mermaid diagram of the workflow."""
        return """
graph TD
    A[Start] --> B[Data Gathering Phase]
    B --> |Parallel| B1[Macro Agent]
    B --> |Parallel| B2[Geopolitical Agent]
    B --> |Parallel| B3[Commodities Agent]
    B1 & B2 & B3 --> C[Analysis Phase]
    C --> |Parallel| C1[Sentiment Agent]
    C --> |Parallel| C2[Fundamentals Agent]
    C --> |Parallel| C3[Technical Agent]
    C1 & C2 & C3 --> D[Alpha Discovery Phase]
    D --> |Parallel| D1[Alternative Data Agent]
    D --> |Parallel| D2[Cross-Asset Agent]
    D --> |Parallel| D3[Event-Driven Agent]
    D1 & D2 & D3 --> E[Risk Agent]
    E --> F{Vetoed?}
    F -->|No| G[Aggregation Engine]
    F -->|Yes| H[Finalize - Vetoed]
    G --> I[Learning & Execution Phase]
    I --> |Parallel| I1[Learning Agent]
    I --> |Parallel| I2[Execution Agent]
    I1 & I2 --> J[Finalize]
    H --> K[End]
    J --> K
"""


async def run_workflow(
    db,
    redis_client=None,
    agent: Optional[str] = None,
) -> WorkflowState:
    """
    Run the equities analysis workflow.

    Args:
        db: Database session
        redis_client: Optional Redis client
        agent: Optional specific agent to run (runs full workflow if None)

    Returns:
        Final workflow state
    """
    workflow = EquitiesWorkflow(db=db, redis_client=redis_client)

    if agent:
        # Run only specified agent
        result = await workflow.run_single_agent(agent)
        state = create_initial_state()
        state["agent_outputs"] = {agent: result}
        state["completed_at"] = datetime.utcnow().isoformat()
        return state

    # Run full workflow
    return await workflow.run()


# CLI interface
if __name__ == "__main__":
    import asyncio
    import argparse

    async def main():
        parser = argparse.ArgumentParser(description="Run Equities Workflow")
        parser.add_argument("--agent", type=str, help="Run specific agent only")
        parser.add_argument("--diagram", action="store_true", help="Print workflow diagram")
        parser.add_argument("--list-agents", action="store_true", help="List available agents")
        args = parser.parse_args()

        if args.diagram:
            workflow = EquitiesWorkflow(db=None)
            print(workflow.get_mermaid_diagram())
            return

        if args.list_agents:
            agents = [
                "macro", "geopolitical", "commodities",
                "sentiment", "fundamentals", "technical",
                "risk", "alternative_data", "cross_asset",
                "event_driven", "learning", "execution",
            ]
            print("Available agents:")
            for agent in agents:
                print(f"  - {agent}")
            return

        from backend.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            state = await run_workflow(db=db, agent=args.agent)
            print(f"\nWorkflow completed:")
            print(f"  Step: {state.get('current_step')}")
            print(f"  Vetoed: {state.get('vetoed')}")
            print(f"  Insight: {state.get('aggregated_insight')}")
            print(f"  Execution Orders: {len(state.get('execution_orders', []))}")
            if state.get("errors"):
                print(f"  Errors: {state.get('errors')}")

    asyncio.run(main())
