from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from schemas import (
    DieSample, DieSampleCreate, DieSampleDetail, SampleStatus,
    SampleOpenRequest, TestResultSubmit, ModificationSubmit,
    ConfirmRequest, RejectRequest, StatusChangeRequest,
    Token, User, AnomalyReport, RejectReasonDistribution, SpecRiskItem,
    OperationLog, OperationType,
)
from auth import (
    authenticate_user, FAKE_USERS_DB, create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user,
)
from store import DieSampleStore


app = FastAPI(
    title="刀模打样管理 API 服务",
    description="用于团队管理刀模打样、折合测试和封样确认的后端服务",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = DieSampleStore()


@app.get("/api/health", tags=["系统"])
async def health_check():
    return {"status": "ok", "service": "die-sample-management", "port": 8127}


@app.post("/api/auth/login", response_model=Token, tags=["认证"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(FAKE_USERS_DB, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=User, tags=["认证"])
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/api/samples", response_model=DieSample, tags=["刀模打样"], status_code=201)
async def create_sample(
    data: DieSampleCreate,
    current_user: User = Depends(get_current_user),
):
    try:
        return store.create_sample(data, created_by=current_user.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/samples", response_model=List[DieSample], tags=["刀模打样"])
async def list_samples(
    project_name: Optional[str] = Query(None, description="客户项目名称（模糊匹配）"),
    customer_name: Optional[str] = Query(None, description="客户名称（模糊匹配）"),
    board_spec: Optional[str] = Query(None, description="纸板规格（模糊匹配）"),
    die_number: Optional[str] = Query(None, description="刀模编号（模糊匹配）"),
    status: Optional[SampleStatus] = Query(None, description="状态"),
    owner: Optional[str] = Query(None, description="责任人（模糊匹配）"),
    date_from: Optional[datetime] = Query(None, description="创建日期起"),
    date_to: Optional[datetime] = Query(None, description="创建日期止"),
    current_user: User = Depends(get_current_user),
):
    return store.query_samples(
        project_name=project_name,
        customer_name=customer_name,
        board_spec=board_spec,
        die_number=die_number,
        status=status,
        owner=owner,
        date_from=date_from,
        date_to=date_to,
    )


@app.get("/api/samples/{sample_id}", response_model=DieSampleDetail, tags=["刀模打样"])
async def get_sample(
    sample_id: str,
    current_user: User = Depends(get_current_user),
):
    s = store.get_sample(sample_id)
    if not s:
        raise HTTPException(status_code=404, detail="打样记录不存在")
    timeline = store.get_sample_timeline(sample_id)
    return DieSampleDetail(**s.model_dump(), timeline=timeline)


@app.post("/api/samples/{sample_id}/open", response_model=DieSample, tags=["刀模打样-状态流转"])
async def open_sample(
    sample_id: str,
    req: SampleOpenRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        req.opener = current_user.username
        return store.open_sample(sample_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/samples/{sample_id}/test", response_model=DieSample, tags=["刀模打样-状态流转"])
async def submit_test(
    sample_id: str,
    req: TestResultSubmit,
    current_user: User = Depends(get_current_user),
):
    try:
        req.tester = current_user.username
        return store.submit_test_result(sample_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/samples/{sample_id}/modify", response_model=DieSample, tags=["刀模打样-状态流转"])
async def submit_modification(
    sample_id: str,
    req: ModificationSubmit,
    current_user: User = Depends(get_current_user),
):
    try:
        req.modifier = current_user.username
        return store.submit_modification(sample_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/samples/{sample_id}/confirm", response_model=DieSample, tags=["刀模打样-状态流转"])
async def confirm_seal(
    sample_id: str,
    req: ConfirmRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        req.confirmer = current_user.username
        return store.confirm_seal(sample_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/samples/{sample_id}/reject", response_model=DieSample, tags=["刀模打样-状态流转"])
async def reject_sample(
    sample_id: str,
    req: RejectRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        req.rejecter = current_user.username
        return store.reject_sample(sample_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/samples/{sample_id}/status", response_model=DieSample, tags=["刀模打样-状态流转"])
async def change_status(
    sample_id: str,
    req: StatusChangeRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        req.operator = current_user.username
        return store.change_status(sample_id, req.target_status, req.operator, req.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/anomalies", response_model=List[AnomalyReport], tags=["异常识别"])
async def detect_anomalies(current_user: User = Depends(get_current_user)):
    return store.detect_anomalies()


@app.get("/api/reports/reject-reasons", response_model=List[RejectReasonDistribution], tags=["统计报表"])
async def get_reject_reasons(current_user: User = Depends(get_current_user)):
    return store.get_reject_reason_distribution()


@app.get("/api/reports/pending-confirm", response_model=List[DieSample], tags=["统计报表"])
async def get_pending_confirm_list(current_user: User = Depends(get_current_user)):
    return store.get_pending_confirm_list()


@app.get("/api/reports/spec-risk", response_model=List[SpecRiskItem], tags=["统计报表"])
async def get_spec_risk_ranking(current_user: User = Depends(get_current_user)):
    return store.get_spec_risk_ranking()


@app.get("/api/operation-logs", response_model=List[OperationLog], tags=["操作留痕"])
async def query_operation_logs(
    project_name: Optional[str] = Query(None, description="项目名称（模糊匹配）"),
    die_number: Optional[str] = Query(None, description="刀模编号（模糊匹配）"),
    customer_name: Optional[str] = Query(None, description="客户名称（模糊匹配）"),
    status: Optional[SampleStatus] = Query(None, description="操作后状态"),
    operator: Optional[str] = Query(None, description="操作人（模糊匹配）"),
    operation_type: Optional[OperationType] = Query(None, description="操作类型"),
    date_from: Optional[datetime] = Query(None, description="操作时间起"),
    date_to: Optional[datetime] = Query(None, description="操作时间止"),
    current_user: User = Depends(get_current_user),
):
    return store.query_operation_logs(
        project_name=project_name,
        die_number=die_number,
        customer_name=customer_name,
        status=status,
        operator=operator,
        operation_type=operation_type,
        date_from=date_from,
        date_to=date_to,
    )


@app.get("/api/samples/{sample_id}/timeline", response_model=List[OperationLog], tags=["操作留痕"])
async def get_sample_timeline(
    sample_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        return store.get_sample_timeline(sample_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8127,
        reload=False,
    )
