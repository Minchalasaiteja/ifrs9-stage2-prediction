from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import re

# ==============================
# Enums
# ==============================

class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    USER = "user"
    VIEWER = "viewer"

class RiskTier(str, Enum):
    VERY_LOW = "Very Low"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"

class ActionUrgency(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"

class IFRS9Stage(str, Enum):
    STAGE_1 = "Stage 1"
    STAGE_2 = "Stage 2"
    STAGE_3 = "Stage 3"

# ==============================
# User Schemas
# ==============================

class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    company: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserLogin(BaseModel):
    """User login schema"""
    username: str = Field(..., description="Email or username")
    password: str = Field(...)
    two_factor_code: Optional[str] = Field(None, min_length=6, max_length=6)

class UserResponse(UserBase):
    """User response schema"""
    id: str = Field(..., alias="_id")
    role: UserRole
    is_active: bool
    is_verified: bool
    two_factor_enabled: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class UserUpdate(BaseModel):
    """User update schema"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    company: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

class PasswordChange(BaseModel):
    """Password change schema"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class PasswordReset(BaseModel):
    """Password reset schema"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

class TwoFactorSetup(BaseModel):
    """2FA setup response"""
    secret: str
    qr_code: str
    manual_key: str

class TwoFactorVerify(BaseModel):
    """2FA verification schema"""
    code: str = Field(..., min_length=6, max_length=6)

class TwoFactorDisable(BaseModel):
    """2FA disable schema"""
    password: str
    code: str = Field(..., min_length=6, max_length=6)

# ==============================
# Token Schemas
# ==============================

class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    requires_2fa: bool = False

class RefreshToken(BaseModel):
    """Refresh token schema"""
    refresh_token: str

class TokenData(BaseModel):
    """Token payload data"""
    sub: str
    role: Optional[str] = None
    exp: Optional[datetime] = None

# ==============================
# Loan Input Schemas
# ==============================

class LoanInput(BaseModel):
    """Enhanced loan input schema with comprehensive validation"""
    model_config = ConfigDict(extra='allow', populate_by_name=True, str_strip_whitespace=True)

    # Core loan information
    loan_id: str = Field(..., min_length=1, max_length=50, description="Unique loan identifier")
    loan_amount_gbp: float = Field(..., gt=0, le=50000000, description="Original loan amount in GBP")
    outstanding_balance_gbp: float = Field(..., ge=0, description="Current outstanding balance")
    original_loan_term_months: int = Field(..., gt=0, le=600, description="Original term in months")
    remaining_term_months: int = Field(..., ge=0, description="Remaining term in months")
    interest_rate_pct: float = Field(..., ge=0, le=100, description="Current interest rate percentage")
    vintage_year: int = Field(..., ge=2000, le=2030, description="Year of origination")
    
    # Credit score information
    internal_credit_score: float = Field(..., ge=300, le=900, description="Internal behavioral score")
    credit_score_change_last_quarter: float = Field(default=0.0, description="Score change in last quarter")
    bureau_inquiries_last_6m: int = Field(default=0, ge=0, le=50, description="Recent credit inquiries")
    
    # Payment behavior
    days_past_due_current: int = Field(default=0, ge=0, le=365, description="Current days past due")
    missed_payments_last_12m: int = Field(default=0, ge=0, le=12, description="Missed payments in last 12 months")
    months_on_book: int = Field(..., ge=0, description="Age of the loan in months")
    
    # PD information
    pd_12m_at_origination_pct: float = Field(..., ge=0, le=100, description="Original 12-month PD")
    pd_12m_current_pct: float = Field(..., ge=0, le=100, description="Current 12-month PD")
    pd_relative_change_pct: float = Field(..., description="Relative change in PD percentage")
    
    # Additional optional fields
    loan_to_value_ratio: Optional[float] = Field(None, ge=0, le=200, description="Loan to value ratio")
    debt_to_income_ratio: Optional[float] = Field(None, ge=0, le=100, description="Debt to income ratio")
    employment_length_years: Optional[float] = Field(None, ge=0, le=50, description="Years of employment")
    
    @field_validator('outstanding_balance_gbp')
    @classmethod
    def balance_not_exceed_loan(cls, v: float, info: Dict[str, Any]) -> float:
        """Validate outstanding balance doesn't exceed loan amount"""
        if 'loan_amount_gbp' in info.data and v > info.data['loan_amount_gbp']:
            raise ValueError(f'Outstanding balance ({v}) cannot exceed loan amount ({info.data["loan_amount_gbp"]})')
        return v

    @field_validator('remaining_term_months')
    @classmethod
    def term_not_exceed_original(cls, v: int, info: Dict[str, Any]) -> int:
        """Validate remaining term doesn't exceed original term"""
        if 'original_loan_term_months' in info.data and v > info.data['original_loan_term_months']:
            raise ValueError(f'Remaining term ({v}) cannot exceed original term ({info.data["original_loan_term_months"]})')
        return v
    
    @field_validator('vintage_year')
    @classmethod
    def validate_vintage_year(cls, v: int) -> int:
        """Validate vintage year is not in the future"""
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError(f'Vintage year ({v}) cannot be in the future')
        return v
    
    @model_validator(mode='after')
    def validate_pd_change(self) -> 'LoanInput':
        """Validate PD relative change calculation"""
        if self.pd_12m_at_origination_pct > 0:
            expected_change = ((self.pd_12m_current_pct - self.pd_12m_at_origination_pct) / 
                             self.pd_12m_at_origination_pct) * 100
            if abs(self.pd_relative_change_pct - expected_change) > 1.0:
                # Allow small rounding differences
                pass
        return self

# ==============================
# Prediction Output Schemas
# ==============================

class PredictionOutput(BaseModel):
    """Prediction result schema"""
    loan_id: str
    migration_probability: float = Field(..., ge=0, le=1)
    probability_percentage: float = Field(..., ge=0, le=100)
    predicted_migration: int = Field(..., ge=0, le=1)
    migration_status: str
    ifrs9_stage: int = Field(..., ge=1, le=3)
    risk_tier: str
    risk_color: str
    recommended_action: str
    action_urgency: str
    confidence_score: float = Field(..., ge=0, le=1)
    model_version: str = "3.0.0"
    threshold_used: float = 0.5
    processing_time_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    cached: bool = False
    simulation: Optional[bool] = False
    risk_factors: Optional[List[str]] = None

class BatchPredictionOutput(BaseModel):
    """Batch prediction response"""
    predictions: List[PredictionOutput]
    batch_size: int
    successful: int
    failed: int = 0
    total_processing_time_ms: float
    average_processing_time_ms: float
    cached_count: int = 0

class PredictionRequest(BaseModel):
    """Prediction request wrapper"""
    loans: List[LoanInput] = Field(..., min_length=1, max_length=1000)
    
class PredictionResponse(BaseModel):
    """Prediction response wrapper"""
    success: bool = True
    data: Union[PredictionOutput, BatchPredictionOutput]
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# ==============================
# Monitoring Schemas
# ==============================

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float
    services: Dict[str, bool]
    metrics: Dict[str, Any]

class MetricsOverview(BaseModel):
    """Metrics overview schema"""
    total_predictions: int
    active_connections: int
    avg_latency_ms: float
    prediction_rates: List[Dict[str, Any]]
    latency_distribution: List[Dict[str, Any]]

class PerformanceMetrics(BaseModel):
    """Model performance metrics"""
    auc_roc: float
    f1_score: float
    precision: float
    recall: float
    accuracy: float
    total_evaluated: int
    confusion_matrix: List[List[int]]

class RiskDistribution(BaseModel):
    """Risk tier distribution"""
    risk_distribution: List[Dict[str, Any]]
    total_predictions: int

class ResourceUsage(BaseModel):
    """System resource usage"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, float]
    process_memory_mb: float

# ==============================
# Admin Schemas
# ==============================

class AdminStats(BaseModel):
    """Admin dashboard statistics"""
    total_users: int
    active_users: int
    active_sessions: int
    api_calls_today: int
    user_growth_labels: List[str]
    user_growth_data: List[int]
    api_usage_labels: List[str]
    api_usage_data: List[int]

class UserActivity(BaseModel):
    """User activity log entry"""
    user_id: str
    action: str
    target_user: Optional[str] = None
    timestamp: datetime
    details: str
    ip_address: Optional[str] = None

class SessionInfo(BaseModel):
    """Session information"""
    user_id: str
    username: str
    created_at: datetime
    expires_at: datetime
    is_active: bool

# ==============================
# API Usage Schemas
# ==============================

class APIUsageLog(BaseModel):
    """API usage log entry"""
    user_id: str
    endpoint: str
    request_type: str
    count: int = 1
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class APIUsageStats(BaseModel):
    """API usage statistics"""
    total_calls: int
    unique_users: int
    calls_by_endpoint: Dict[str, int]
    calls_by_type: Dict[str, int]
    time_range: Dict[str, datetime]

# ==============================
# Audit Schemas
# ==============================

class AuditLog(BaseModel):
    """Audit log entry"""
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    action: str
    target_user: Optional[str] = None
    timestamp: datetime
    details: str
    ip_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AuditLogResponse(BaseModel):
    """Audit log response with pagination"""
    logs: List[AuditLog]
    total: int
    page: int
    pages: int