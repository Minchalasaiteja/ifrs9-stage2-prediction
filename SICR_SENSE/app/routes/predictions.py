from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List
import time
from datetime import datetime
import logging

from ..schemas import (
    LoanInput, PredictionOutput, BatchPredictionOutput,
    PredictionRequest, PredictionResponse
)
from ..model_service import IFRS9ModelService
from ..monitoring import metrics_manager, LATENCY_HISTOGRAM
from ..websocket_handler import ws_manager
from ..auth.dependencies import get_current_active_user, RoleChecker
from ..database import db

logger = logging.getLogger(__name__)
router = APIRouter()

# Global model service (initialized in main.py)
model_service = None

def set_model_service(service):
    """Set the global model service instance"""
    global model_service
    model_service = service

@router.post("/predict", response_model=PredictionOutput)
async def predict_single_loan(
    loan: LoanInput,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Predict SICR for a single loan with real-time WebSocket broadcast
    """
    start_time = time.time()
    
    try:
        # Run prediction
        if model_service is None:
            raise HTTPException(status_code=503, detail="Model service not initialized")
        
        results = model_service.predict([loan.model_dump()])
        prediction = results[0]
        
        # Calculate latency
        latency = time.time() - start_time
        prediction["processing_time_ms"] = round(latency * 1000, 2)
        prediction["timestamp"] = datetime.utcnow().isoformat()
        prediction["user_id"] = str(current_user["_id"])
        
        # Save to database
        background_tasks.add_task(
            save_prediction_to_db,
            current_user["_id"],
            loan.model_dump(),
            prediction,
            latency
        )
        
        # Background tasks for monitoring
        background_tasks.add_task(
            metrics_manager.log_prediction,
            loan.model_dump(),
            prediction,
            latency
        )
        background_tasks.add_task(
            metrics_manager.record_metrics,
            prediction["risk_tier"],
            prediction["predicted_migration"],
            prediction.get("model_version", "2.1.0")
        )
        
        # Record latency
        LATENCY_HISTOGRAM.observe(latency)
        
        # Broadcast via WebSocket
        background_tasks.add_task(
            ws_manager.broadcast_prediction,
            prediction
        )
        
        # Log API usage
        background_tasks.add_task(
            log_api_usage,
            current_user["_id"],
            "/api/v1/predict",
            "single"
        )
        
        return prediction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.post("/predict/batch", response_model=BatchPredictionOutput)
async def predict_batch_loans(
    loans: List[LoanInput],
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user)
):
    """Batch prediction endpoint for multiple loans"""
    if not model_service or not model_service.model:
        raise HTTPException(
            status_code=503,
            detail="Batch predictions require trained model"
        )
    
    start_time = time.time()
    
    try:
        input_dicts = [loan.model_dump() for loan in loans]
        results = model_service.predict(input_dicts)
        
        total_latency = time.time() - start_time
        
        # Background tasks for batch
        for i, result in enumerate(results):
            background_tasks.add_task(
                metrics_manager.log_prediction,
                input_dicts[i],
                result,
                total_latency / len(results)
            )
            background_tasks.add_task(
                metrics_manager.record_metrics,
                result["risk_tier"],
                result["predicted_migration"]
            )
            
            # Save to database
            background_tasks.add_task(
                save_prediction_to_db,
                current_user["_id"],
                input_dicts[i],
                result,
                total_latency / len(results)
            )
        
        LATENCY_HISTOGRAM.observe(total_latency)
        
        # Log API usage
        background_tasks.add_task(
            log_api_usage,
            current_user["_id"],
            "/api/v1/predict/batch",
            "batch",
            len(loans)
        )
        
        return BatchPredictionOutput(
            predictions=results,
            batch_size=len(loans),
            total_processing_time_ms=round(total_latency * 1000, 2)
        )
        
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_prediction_history(
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_active_user)
):
    """Get user's prediction history"""
    try:
        skip = (page - 1) * limit
        
        predictions = await db.predictions.find(
            {"user_id": str(current_user["_id"])}
        ).sort("timestamp", -1).skip(skip).limit(limit).to_list(length=limit)
        
        total = await db.predictions.count_documents(
            {"user_id": str(current_user["_id"])}
        )
        
        return {
            "predictions": predictions,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get prediction history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_prediction_stats(
    current_user: dict = Depends(get_current_active_user)
):
    """Get real-time prediction statistics"""
    return {
        "daily_predictions": metrics_manager.daily_counter,
        "model_version": model_service.model_version if model_service else "simulation",
        "active_websockets": ws_manager.connection_stats["active_connections"],
        "total_messages_sent": ws_manager.connection_stats["messages_sent"],
        "uptime_hours": round(
            (datetime.utcnow() - metrics_manager.start_time).total_seconds() / 3600, 2
        ) if hasattr(metrics_manager, 'start_time') else 0
    }

async def save_prediction_to_db(user_id: str, input_data: dict, prediction: dict, latency: float):
    """Save prediction to database"""
    try:
        await db.predictions.insert_one({
            "user_id": user_id,
            "input": input_data,
            "output": prediction,
            "latency_ms": round(latency * 1000, 2),
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Failed to save prediction: {e}")

async def log_api_usage(user_id: str, endpoint: str, request_type: str, count: int = 1):
    """Log API usage for monitoring"""
    try:
        await db.api_usage.insert_one({
            "user_id": user_id,
            "endpoint": endpoint,
            "request_type": request_type,
            "count": count,
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Failed to log API usage: {e}")