from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class SampleStatus(str, Enum):
    PENDING_OPEN = "待开样"
    SAMPLING = "打样中"
    PENDING_TEST = "待测试"
    PENDING_CONFIRM = "待确认"
    MODIFYING = "修改中"
    SEALED = "已封样"
    CANCELLED = "已取消"


class TestResultRecord(BaseModel):
    id: str
    round: int = 1
    folding_result: Optional[str] = None
    indentation_result: Optional[str] = None
    cracking_description: Optional[str] = None
    tester: Optional[str] = None
    test_date: Optional[datetime] = None
    is_passed: Optional[bool] = None
    notes: Optional[str] = None


class ModificationRecord(BaseModel):
    id: str
    round: int = 1
    modification_action: str
    modifier: str
    modify_date: datetime = Field(default_factory=datetime.now)
    reason: Optional[str] = None
    notes: Optional[str] = None


class RejectRecord(BaseModel):
    id: str
    round: int = 1
    reason: str
    rejecter: str
    reject_date: datetime = Field(default_factory=datetime.now)
    description: Optional[str] = None


class SealRecord(BaseModel):
    sealer: str
    seal_date: datetime = Field(default_factory=datetime.now)
    version: str
    notes: Optional[str] = None


class SampleOpenRecord(BaseModel):
    opener: str
    open_date: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None


class DieSampleCreate(BaseModel):
    project_name: str
    customer_name: str
    board_spec: str
    die_number: str
    die_version: str
    test_round: int = 1
    owner: str
    priority: Optional[str] = "普通"
    deadline: Optional[datetime] = None
    notes: Optional[str] = None


class DieSample(BaseModel):
    id: str
    project_name: str
    customer_name: str
    board_spec: str
    die_number: str
    die_version: str
    test_round: int = 1
    owner: str
    status: SampleStatus = SampleStatus.PENDING_OPEN
    priority: str = "普通"
    deadline: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str
    notes: Optional[str] = None

    open_record: Optional[SampleOpenRecord] = None
    test_records: List[TestResultRecord] = []
    modification_records: List[ModificationRecord] = []
    reject_records: List[RejectRecord] = []
    seal_record: Optional[SealRecord] = None


class SampleOpenRequest(BaseModel):
    opener: str
    notes: Optional[str] = None


class TestResultSubmit(BaseModel):
    round: int
    folding_result: Optional[str] = None
    indentation_result: Optional[str] = None
    cracking_description: Optional[str] = None
    tester: str
    test_date: Optional[datetime] = None
    is_passed: bool
    notes: Optional[str] = None


class ModificationSubmit(BaseModel):
    round: int
    modification_action: str
    modifier: str
    reason: Optional[str] = None
    notes: Optional[str] = None


class ConfirmRequest(BaseModel):
    confirmer: str
    version: str
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    round: int
    reason: str
    rejecter: str
    description: Optional[str] = None


class StatusChangeRequest(BaseModel):
    target_status: SampleStatus
    operator: str
    notes: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: Optional[str] = None


class UserInDB(User):
    hashed_password: str


class UserLogin(BaseModel):
    username: str
    password: str


class AnomalyReport(BaseModel):
    type: str
    level: str
    description: str
    related_sample_ids: List[str]
    details: Dict[str, Any]


class RejectReasonDistribution(BaseModel):
    reason: str
    count: int
    percentage: float


class SpecRiskItem(BaseModel):
    board_spec: str
    total_samples: int
    cracking_count: int
    reject_count: int
    risk_score: float
    risk_level: str
    related_sample_ids: List[str]


class OperationType(str, Enum):
    CREATE = "新建"
    OPEN = "开样"
    TEST_SUBMIT = "测试提交"
    MODIFY = "修改"
    REJECT = "退回"
    CONFIRM = "封样确认"
    STATUS_CHANGE = "状态调整"


class OperationLog(BaseModel):
    id: str
    sample_id: str
    project_name: str
    customer_name: str
    die_number: str
    operation_type: OperationType
    operator: str
    operation_time: datetime = Field(default_factory=datetime.now)
    previous_status: Optional[SampleStatus] = None
    current_status: SampleStatus
    notes: Optional[str] = None
    business_result: Optional[Dict[str, Any]] = None


class OperationLogQuery(BaseModel):
    project_name: Optional[str] = None
    die_number: Optional[str] = None
    customer_name: Optional[str] = None
    status: Optional[SampleStatus] = None
    operator: Optional[str] = None
    operation_type: Optional[OperationType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
