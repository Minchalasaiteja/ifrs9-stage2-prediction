from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from ..database import db
from ..auth.dependencies import RoleChecker, get_current_active_user
from datetime import datetime
import csv, io, os
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/generate')
async def generate_report(report_type: str, filters: dict = None, background_tasks: BackgroundTasks = None, current_user: dict = Depends(RoleChecker(['admin']))):
    """Request report generation; runs in background and stores report metadata in DB."""
    try:
        report_id = str(uuid.uuid4())
        entry = {
            '_id': report_id,
            'report_type': report_type,
            'filters': filters or {},
            'status': 'pending',
            'generated_by': str(current_user['_id']),
            'created_at': datetime.utcnow()
        }
        await db.reports.insert_one(entry)
        background_tasks.add_task(run_generate_report, report_id)
        return {'report_id': report_id, 'status': 'pending'}
    except Exception as e:
        logger.error('Failed to enqueue report generation: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


async def run_generate_report(report_id: str):
    try:
        rep = await db.reports.find_one({'_id': report_id})
        if not rep:
            return
        # For now support a few report types by querying predictions
        filters = rep.get('filters', {}) or {}
        query = {}
        # Apply basic filters mapping
        if filters.get('start_date') or filters.get('end_date'):
            from dateutil import parser as dateparser
            rng = {}
            if filters.get('start_date'): rng['$gte'] = dateparser.parse(filters.get('start_date'))
            if filters.get('end_date'): rng['$lte'] = dateparser.parse(filters.get('end_date'))
            if rng: query['timestamp'] = rng

        cursor = db.predictions.find(query).sort('timestamp', -1)
        # Prepare CSV
        reports_dir = os.path.join(os.getcwd(), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        filename = f"report_{report_id}.csv"
        filepath = os.path.join(reports_dir, filename)
        with open(filepath, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.writer(fh)
            writer.writerow(['_id','loan_id','risk_tier','probability','predicted_migration','processing_time_ms','timestamp'])
            async for doc in cursor:
                loan_id = (doc.get('input') or {}).get('loan_id') or (doc.get('output') or {}).get('loan_id')
                prob = (doc.get('output') or {}).get('migration_probability')
                row = [str(doc['_id']), loan_id, (doc.get('output') or {}).get('risk_tier'), prob, (doc.get('output') or {}).get('predicted_migration'), doc.get('latency_ms') or doc.get('processing_time_ms'), doc.get('timestamp')]
                writer.writerow(row)

        await db.reports.update_one({'_id': report_id}, {'$set': {'status': 'done', 'file_path': filepath, 'completed_at': datetime.utcnow()}})
        # Log audit
        await db.audit_logs.insert_one({'user_id': rep.get('generated_by'), 'action': 'report_generated', 'report_id': report_id, 'timestamp': datetime.utcnow()})
    except Exception as e:
        logger.error('Report generation failed: %s', e, exc_info=True)
        try:
            await db.reports.update_one({'_id': report_id}, {'$set': {'status': 'failed', 'error': str(e), 'completed_at': datetime.utcnow()}})
        except Exception:
            pass


@router.get('/history')
async def report_history(page: int = 1, limit: int = 50, current_user: dict = Depends(get_current_active_user)):
    skip = (page-1)*limit
    cursor = db.reports.find({}).sort('created_at', -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    total = await db.reports.count_documents({})
    return {'reports': docs, 'total': total, 'page': page, 'pages': (total+limit-1)//limit}


@router.get('/{report_id}/download')
async def download_report(report_id: str, current_user: dict = Depends(get_current_active_user)):
    rep = await db.reports.find_one({'_id': report_id})
    if not rep:
        raise HTTPException(status_code=404, detail='Report not found')
    if rep.get('status') != 'done' or not rep.get('file_path'):
        raise HTTPException(status_code=400, detail='Report not ready')
    path = rep['file_path']
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='File missing')
    def iterfile():
        with open(path, 'rb') as fh:
            while True:
                chunk = fh.read(8192)
                if not chunk: break
                yield chunk
    return StreamingResponse(iterfile(), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename={os.path.basename(path)}'})
