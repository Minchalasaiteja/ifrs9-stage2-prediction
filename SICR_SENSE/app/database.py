from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import asyncio
from datetime import datetime, timedelta
import logging
from .config import settings

logger = logging.getLogger(__name__)

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect_db(cls):
        """Create database connection"""
        try:
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            
            # Verify connection
            await cls.client.admin.command('ping')
            logger.info("  MongoDB connected successfully")
            
            # Create indexes
            await cls.create_indexes()
            
        except Exception as e:
            logger.error(f"    MongoDB connection failed: {e}")
            raise
    
    @classmethod
    async def close_db(cls):
        """Close database connection"""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")
    
    @classmethod
    async def create_indexes(cls):
        """Create necessary database indexes"""
        try:
            # Users collection
            await cls.db.users.create_index("email", unique=True)
            await cls.db.users.create_index("username", unique=True)
            await cls.db.users.create_index("created_at")
            
            # Predictions collection
            await cls.db.predictions.create_index("timestamp")
            await cls.db.predictions.create_index("loan_id")
            await cls.db.predictions.create_index([("user_id", 1), ("timestamp", -1)])
            
            # Audit logs
            await cls.db.audit_logs.create_index("timestamp")
            await cls.db.audit_logs.create_index("user_id")
            
            # Sessions
            await cls.db.sessions.create_index("access_token")
            await cls.db.sessions.create_index("expires_at", expireAfterSeconds=0)
            
            # API usage tracking
            await cls.db.api_usage.create_index([("user_id", 1), ("endpoint", 1)])
            await cls.db.api_usage.create_index("timestamp")
            
            # Model performance
            await cls.db.model_metrics.create_index("timestamp")
            
            logger.info("Database indexes created")
            
        except Exception as e:
            logger.error(f"Index creation error: {e}")
    
    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        if cls.db is None:
            raise Exception("Database not initialized")
        return cls.db

# Collections helper
class Collections:
    @property
    def users(self):
        return Database.get_db().users
    
    @property
    def predictions(self):
        return Database.get_db().predictions
    
    @property
    def audit_logs(self):
        return Database.get_db().audit_logs
    
    @property
    def sessions(self):
        return Database.get_db().sessions
    
    @property
    def api_usage(self):
        return Database.get_db().api_usage
    
    @property
    def model_metrics(self):
        return Database.get_db().model_metrics

db = Collections()