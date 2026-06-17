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
    URGE = "发起催办"
    URGE_HANDLE = "处理催办"


class UrgeStatus(str, Enum):
    PENDING = "待处理"
    PROCESSING = "处理中"
    RESOLVED = "已处理"
    CLOSED = "已关闭"


class UrgeRecord(BaseModel):
    id: str
    sample_id: str
    project_name: str
    customer_name: str
    die_number: str
    urge_type: str
    urge_reason: str
    description: Optional[str] = None
    urge_by: str
    urge_time: datetime = Field(default_factory=datetime.now)
    handler: Optional[str] = None
    handle_time: Optional[datetime] = None
    handle_result: Optional[str] = None
    status: UrgeStatus = UrgeStatus.PENDING
    priority: str = "普通"
    deadline: Optional[datetime] = None


class UrgeCreate(BaseModel):
    sample_id: str
    urge_type: str
    urge_reason: str
    description: Optional[str] = None
    priority: Optional[str] = "普通"
    deadline: Optional[datetime] = None


class UrgeHandle(BaseModel):
    handle_result: str
    handler: Optional[str] = None
    new_status: Optional[UrgeStatus] = None


class UrgeQueryParams(BaseModel):
    sample_id: Optional[str] = None
    status: Optional[UrgeStatus] = None
    urge_by: Optional[str] = None
    handler: Optional[str] = None
    urge_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    project_name: Optional[str] = None
    customer_name: Optional[str] = None
    die_number: Optional[str] = None
    owner: Optional[str] = None


class UrgeSummary(BaseModel):
    total_urges: int
    pending_count: int
    processing_count: int
    resolved_count: int
    closed_count: int
    high_risk_unclosed_count: int
    urge_type_distribution: Dict[str, int]


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


class DieSampleDetail(DieSample):
    timeline: List[OperationLog] = []
    urge_records: List[UrgeRecord] = []


class KanbanRiskFlag(str, Enum):
    NONE = "正常"
    NEAR_DEADLINE = "临近截止"
    OVERDUE = "已超期"
    REPEATED_MODIFICATION = "反复修改"
    MULTIPLE_TEST_FAILURE = "多次测试未通过"


class KanbanSampleItem(BaseModel):
    id: str
    project_name: str
    customer_name: str
    board_spec: str
    die_number: str
    die_version: str
    test_round: int
    owner: str
    status: SampleStatus
    priority: str
    deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: str
    notes: Optional[str] = None
    risk_flags: List[KanbanRiskFlag] = []
    days_remaining: Optional[int] = None
    modification_count: int = 0
    test_failure_count: int = 0
    pending_urge_count: int = 0
    total_urge_count: int = 0
    latest_urge_time: Optional[datetime] = None


class StatusSummaryItem(BaseModel):
    status: SampleStatus
    count: int
    percentage: float
    sample_ids: List[str]


class CustomerSummaryItem(BaseModel):
    customer_name: str
    total: int
    status_breakdown: Dict[str, int]
    overdue_count: int


class BoardSpecSummaryItem(BaseModel):
    board_spec: str
    total: int
    cracking_count: int
    reject_count: int
    risk_level: str


class OwnerSummaryItem(BaseModel):
    owner: str
    total: int
    status_breakdown: Dict[str, int]
    overdue_count: int


class KanbanSummary(BaseModel):
    total_samples: int
    status_summary: List[StatusSummaryItem]
    customer_summary: List[CustomerSummaryItem]
    board_spec_summary: List[BoardSpecSummaryItem]
    owner_summary: List[OwnerSummaryItem]
    high_risk_count: int
    overdue_count: int
    near_deadline_count: int
    pending_urge_count: int
    high_risk_unclosed_urge_count: int


class KanbanQueryParams(BaseModel):
    customer_name: Optional[str] = None
    project_name: Optional[str] = None
    die_number: Optional[str] = None
    status: Optional[SampleStatus] = None
    owner: Optional[str] = None
    priority: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
