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
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import io, csv
from bson import ObjectId

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
        
        raw_predictions = await db.predictions.find(
            {"user_id": str(current_user["_id"])}
        ).sort("timestamp", -1).skip(skip).limit(limit).to_list(length=limit)
        
        total = await db.predictions.count_documents(
            {"user_id": str(current_user["_id"])}
        )
        
        # Flatten and stringify ObjectIds for the frontend
        predictions = []
        for pred in raw_predictions:
            flat_pred = {}
            # Output holds the main prediction details
            if "output" in pred and isinstance(pred["output"], dict):
                flat_pred.update(pred["output"])
            # Input holds original loan data like loan_id
            if "input" in pred and isinstance(pred["input"], dict):
                # Only fallback to input's loan_id if output doesn't have it
                if "loan_id" not in flat_pred and "loan_id" in pred["input"]:
                    flat_pred["loan_id"] = pred["input"]["loan_id"]
            
            # Map top-level DB fields
            flat_pred["_id"] = str(pred["_id"])
            if "latency_ms" in pred:
                flat_pred["processing_time_ms"] = pred["latency_ms"]
            if "timestamp" in pred:
                flat_pred["timestamp"] = pred["timestamp"].isoformat() if isinstance(pred["timestamp"], datetime) else pred["timestamp"]
            
            predictions.append(flat_pred)
        
        return {
            "predictions": predictions,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get prediction history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/history/all')
async def get_all_prediction_history(
    page: int = 1,
    limit: int = 50,
    search: str = '',
    risk_filter: str = '',
    model_version: str = '',
    status: str = '',
    start_date: str = '',
    end_date: str = '',
    current_user: dict = Depends(RoleChecker(['admin']))
):
    """Admin: Get paged prediction history with filters"""
    try:
        query = {}
        if search:
            q_regex = {'$regex': search, '$options': 'i'}
            query['$or'] = [
                {'input.loan_id': q_regex},
                {'output.loan_id': q_regex},
                {'output.risk_tier': q_regex}
            ]
        if risk_filter:
            query['output.risk_tier'] = risk_filter
        if model_version:
            query['output.model_version'] = model_version
        if status:
            query['output.status'] = status
        if start_date or end_date:
            gte = None; lte = None
            from dateutil import parser as dateparser
            if start_date:
                gte = dateparser.parse(start_date)
            if end_date:
                lte = dateparser.parse(end_date)
            rng = {}
            if gte: rng['$gte'] = gte
            if lte: rng['$lte'] = lte
            if rng: query['timestamp'] = rng

        skip = (page - 1) * limit
        cursor = db.predictions.find(query).sort('timestamp', -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        total = await db.predictions.count_documents(query)

        def serialize(pred):
            flat = {}
            if 'output' in pred and isinstance(pred['output'], dict): flat.update(pred['output'])
            if 'input' in pred and isinstance(pred['input'], dict):
                if 'loan_id' not in flat and 'loan_id' in pred['input']: flat['loan_id'] = pred['input']['loan_id']
            flat['_id'] = str(pred['_id'])
            flat['timestamp'] = pred.get('timestamp').isoformat() if hasattr(pred.get('timestamp'), 'isoformat') else pred.get('timestamp')
            return flat

        predictions = [serialize(d) for d in docs]
        return {'predictions': predictions, 'total': total, 'page': page, 'pages': (total + limit - 1)//limit}
    except Exception as e:
        logger.error(f'Failed to fetch all prediction history: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{prediction_id}')
async def get_prediction_detail(prediction_id: str, current_user: dict = Depends(get_current_active_user)):
    """Return detailed prediction record. Admins can access any; users only their own."""
    try:
        obj_id = ObjectId(prediction_id) if ObjectId.is_valid(prediction_id) else prediction_id
        pred = await db.predictions.find_one({'_id': obj_id})
        if not pred:
            raise HTTPException(status_code=404, detail='Prediction not found')
        # Authorization: admin or owner
        if current_user.get('role') != 'admin' and str(pred.get('user_id')) != str(current_user.get('_id')):
            raise HTTPException(status_code=403, detail='Forbidden')
        # Return full record
        pred['_id'] = str(pred['_id'])
        return pred
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Failed to load prediction detail: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/export')
async def export_predictions(
    search: str = '',
    risk_filter: str = '',
    start_date: str = '',
    end_date: str = '',
    format: str = 'csv',
    current_user: dict = Depends(RoleChecker(['admin']))
):
    """Export filtered predictions as CSV (Excel/PDF not implemented)."""
    try:
        query = {}
        if search:
            q_regex = {'$regex': search, '$options': 'i'}
            query['$or'] = [{'input.loan_id': q_regex}, {'output.risk_tier': q_regex}]
        if risk_filter:
            query['output.risk_tier'] = risk_filter
        if start_date or end_date:
            from dateutil import parser as dateparser
            rng = {}
            if start_date: rng['$gte'] = dateparser.parse(start_date)
            if end_date: rng['$lte'] = dateparser.parse(end_date)
            if rng: query['timestamp'] = rng

        cursor = db.predictions.find(query).sort('timestamp', -1)

        if format != 'csv':
            raise HTTPException(status_code=501, detail='Only CSV export is supported')

        # Streaming CSV
        async def gen():
            header = ['_id','loan_id','risk_tier','probability','predicted_migration','processing_time_ms','timestamp']
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(header)
            yield output.getvalue()
            output.seek(0); output.truncate(0)

            async for doc in cursor:
                loan_id = (doc.get('input') or {}).get('loan_id') or (doc.get('output') or {}).get('loan_id')
                prob = (doc.get('output') or {}).get('migration_probability')
                row = [str(doc['_id']), loan_id, (doc.get('output') or {}).get('risk_tier'), prob, (doc.get('output') or {}).get('predicted_migration'), doc.get('latency_ms') or doc.get('processing_time_ms'), doc.get('timestamp')]
                writer.writerow(row)
                yield output.getvalue()
                output.seek(0); output.truncate(0)

        return StreamingResponse(gen(), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=predictions_export.csv'})
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Export failed: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/batch/upload')
async def upload_batch_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None, current_user: dict = Depends(get_current_active_user)):
    """Upload CSV for batch prediction processing. CSV expected with headers matching model input keys."""
    if not file:
        raise HTTPException(status_code=400, detail='No file uploaded')
    filename = file.filename or 'upload.csv'
    if not filename.lower().endswith('.csv'):
        raise HTTPException(status_code=415, detail='Only CSV uploads are supported')

    content = await file.read()
    # Schedule background processing
    background_tasks.add_task(process_batch_file, str(current_user['_id']), content, filename)
    return {'status': 'accepted', 'filename': filename}


async def process_batch_file(user_id: str, content: bytes, filename: str):
    """Background worker to process CSV batch uploads"""
    try:
        text = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text))
        rows = [r for r in reader]
        # Convert rows to model input dicts (best-effort)
        inputs = rows
        # If model_service is not available, just save rows as failed
        if model_service is None:
            # log audit
            await db.audit_logs.insert_one({'user_id': user_id, 'action': 'batch_upload_failed', 'details': 'Model service not available', 'timestamp': datetime.utcnow()})
            return

        # Predict in batches
        batch_size = 100
        for i in range(0, len(inputs), batch_size):
            chunk = inputs[i:i+batch_size]
            try:
                results = model_service.predict(chunk)
            except Exception as e:
                logger.error('Model predict failed during batch: %s', e)
                results = []

            for j, res in enumerate(results):
                latency = res.get('processing_time_ms', 0) / 1000.0 if res.get('processing_time_ms') else 0
                await save_prediction_to_db(user_id, chunk[j], res, latency)
                try:
                    await ws_manager.broadcast_prediction(res)
                except Exception:
                    pass

        await db.audit_logs.insert_one({'user_id': user_id, 'action': 'batch_upload_processed', 'filename': filename, 'count': len(rows), 'timestamp': datetime.utcnow()})
    except Exception as e:
        logger.error('Failed to process batch file: %s', e, exc_info=True)
        try:
            await db.audit_logs.insert_one({'user_id': user_id, 'action': 'batch_upload_failed', 'filename': filename, 'error': str(e), 'timestamp': datetime.utcnow()})
        except Exception:
            pass

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