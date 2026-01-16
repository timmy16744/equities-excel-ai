"""Main API routes for analysis endpoints."""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database import get_db, AgentPrediction, AggregatedInsight, PerformanceMetric, User
from backend.api.auth_routes import get_current_active_user

router = APIRouter()


@router.post("/analyze")
async def trigger_analysis(
    agents: Optional[list[str]] = None,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger full analysis from all enabled agents."""
    # TODO: Implement orchestration trigger
    return {
        "status": "analysis_triggered",
        "agents": agents or "all",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/agents/{agent_id}/latest")
async def get_latest_agent_output(
    agent_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the latest output from a specific agent."""
    result = await db.execute(
        select(AgentPrediction)
        .where(AgentPrediction.agent_id == agent_id)
        .order_by(desc(AgentPrediction.timestamp))
        .limit(1)
    )
    prediction = result.scalar_one_or_none()

    if not prediction:
        raise HTTPException(status_code=404, detail=f"No predictions found for agent: {agent_id}")

    return {
        "agent_id": prediction.agent_id,
        "timestamp": prediction.timestamp.isoformat(),
        "outlook": prediction.outlook,
        "confidence": prediction.confidence,
        "timeframe": prediction.timeframe,
        "reasoning": prediction.reasoning,
        "key_factors": prediction.key_factors,
        "uncertainties": prediction.uncertainties,
        "data_sources": prediction.data_sources,
    }


@router.get("/agents/{agent_id}/history")
async def get_agent_history(
    agent_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get historical predictions from a specific agent."""
    result = await db.execute(
        select(AgentPrediction)
        .where(AgentPrediction.agent_id == agent_id)
        .order_by(desc(AgentPrediction.timestamp))
        .offset(offset)
        .limit(limit)
    )
    predictions = result.scalars().all()

    return {
        "agent_id": agent_id,
        "predictions": [
            {
                "id": p.id,
                "timestamp": p.timestamp.isoformat(),
                "outlook": p.outlook,
                "confidence": p.confidence,
                "timeframe": p.timeframe,
            }
            for p in predictions
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get("/insights/latest")
async def get_latest_insights(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the latest aggregated insights."""
    result = await db.execute(
        select(AggregatedInsight)
        .order_by(desc(AggregatedInsight.timestamp))
        .limit(1)
    )
    insight = result.scalar_one_or_none()

    if not insight:
        raise HTTPException(status_code=404, detail="No aggregated insights found")

    return {
        "timestamp": insight.timestamp.isoformat(),
        "overall_outlook": insight.overall_outlook,
        "confidence": insight.confidence,
        "agent_outputs": insight.agent_outputs,
        "conflicts": insight.conflicts,
        "resolution_reasoning": insight.resolution_reasoning,
        "final_recommendations": insight.final_recommendations,
        "risk_assessment": insight.risk_assessment,
        "vetoed": insight.vetoed,
        "veto_reason": insight.veto_reason,
    }


@router.get("/performance/{agent_id}")
async def get_agent_performance(
    agent_id: str,
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get performance metrics for a specific agent."""
    result = await db.execute(
        select(PerformanceMetric)
        .where(PerformanceMetric.agent_id == agent_id)
        .order_by(desc(PerformanceMetric.created_at))
        .limit(100)
    )
    metrics = result.scalars().all()

    if not metrics:
        return {
            "agent_id": agent_id,
            "metrics": [],
            "summary": {
                "total_predictions": 0,
                "accuracy": None,
            },
        }

    total = len(metrics)
    accurate = sum(1 for m in metrics if m.accuracy_score and m.accuracy_score >= 0.5)

    return {
        "agent_id": agent_id,
        "metrics": [
            {
                "id": m.id,
                "predicted_outlook": m.predicted_outlook,
                "actual_outcome": m.actual_outcome,
                "accuracy_score": m.accuracy_score,
                "prediction_date": m.prediction_date.isoformat() if m.prediction_date else None,
                "outcome_date": m.outcome_date.isoformat() if m.outcome_date else None,
            }
            for m in metrics[:20]  # Return last 20
        ],
        "summary": {
            "total_predictions": total,
            "accuracy": accurate / total if total > 0 else None,
        },
    }


@router.post("/agents/{agent_id}/run")
async def run_specific_agent(
    agent_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually trigger a specific agent to run."""
    # TODO: Implement single agent trigger
    return {
        "status": "agent_triggered",
        "agent_id": agent_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
