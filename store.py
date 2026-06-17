import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from schemas import (
    DieSample, DieSampleCreate, SampleStatus,
    SampleOpenRecord, SampleOpenRequest,
    TestResultRecord, TestResultSubmit,
    ModificationRecord, ModificationSubmit,
    RejectRecord, RejectRequest,
    SealRecord, ConfirmRequest,
    AnomalyReport, RejectReasonDistribution, SpecRiskItem,
)


CRACKING_CONCENTRATION_THRESHOLD = 3
TEST_OVERDUE_DAYS = 7
UNCONFIRMED_AFTER_MODIFY_DAYS = 3
HIGH_REJECTION_THRESHOLD = 3


class DieSampleStore:
    def __init__(self):
        self.samples: Dict[str, DieSample] = {}
        self._index_project_version: Dict[str, str] = {}

    def _make_key(self, project_name: str, die_number: str, die_version: str) -> str:
        return f"{project_name}|{die_number}|{die_version}"

    def create_sample(self, data: DieSampleCreate, created_by: str) -> DieSample:
        key = self._make_key(data.project_name, data.die_number, data.die_version)
        if key in self._index_project_version:
            raise ValueError(
                f"项目 {data.project_name} 下刀模 {data.die_number} 版本 {data.die_version} 已存在，禁止重复创建"
            )
        sample_id = str(uuid.uuid4())
        sample = DieSample(
            id=sample_id,
            **data.model_dump(),
            created_by=created_by,
        )
        self.samples[sample_id] = sample
        self._index_project_version[key] = sample_id
        return sample

    def get_sample(self, sample_id: str) -> Optional[DieSample]:
        return self.samples.get(sample_id)

    def query_samples(
        self,
        project_name: Optional[str] = None,
        customer_name: Optional[str] = None,
        board_spec: Optional[str] = None,
        die_number: Optional[str] = None,
        status: Optional[SampleStatus] = None,
        owner: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[DieSample]:
        results = []
        for s in self.samples.values():
            if project_name and project_name not in s.project_name:
                continue
            if customer_name and customer_name not in s.customer_name:
                continue
            if board_spec and board_spec not in s.board_spec:
                continue
            if die_number and die_number not in s.die_number:
                continue
            if status and s.status != status:
                continue
            if owner and owner not in s.owner:
                continue
            if date_from and s.created_at < date_from:
                continue
            if date_to and s.created_at > date_to:
                continue
            results.append(s)
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    def open_sample(self, sample_id: str, req: SampleOpenRequest) -> DieSample:
        s = self._require(sample_id)
        self._check_status(s, [SampleStatus.PENDING_OPEN], "开样")
        s.open_record = SampleOpenRecord(
            opener=req.opener,
            open_date=datetime.now(),
            notes=req.notes,
        )
        s.status = SampleStatus.SAMPLING
        s.updated_at = datetime.now()
        return s

    def submit_test_result(self, sample_id: str, req: TestResultSubmit) -> DieSample:
        s = self._require(sample_id)
        self._check_status(s, [SampleStatus.SAMPLING, SampleStatus.PENDING_TEST, SampleStatus.MODIFYING], "提交测试")
        record = TestResultRecord(
            id=str(uuid.uuid4()),
            round=req.round,
            folding_result=req.folding_result,
            indentation_result=req.indentation_result,
            cracking_description=req.cracking_description,
            tester=req.tester,
            test_date=req.test_date or datetime.now(),
            is_passed=req.is_passed,
            notes=req.notes,
        )
        s.test_records.append(record)
        s.test_round = req.round
        if req.is_passed:
            s.status = SampleStatus.PENDING_CONFIRM
        else:
            s.status = SampleStatus.MODIFYING
        s.updated_at = datetime.now()
        return s

    def submit_modification(self, sample_id: str, req: ModificationSubmit) -> DieSample:
        s = self._require(sample_id)
        self._check_status(
            s, [SampleStatus.PENDING_CONFIRM, SampleStatus.MODIFYING, SampleStatus.SAMPLING], "提交修改"
        )
        record = ModificationRecord(
            id=str(uuid.uuid4()),
            round=req.round,
            modification_action=req.modification_action,
            modifier=req.modifier,
            modify_date=datetime.now(),
            reason=req.reason,
            notes=req.notes,
        )
        s.modification_records.append(record)
        s.status = SampleStatus.MODIFYING
        s.updated_at = datetime.now()
        return s

    def confirm_seal(self, sample_id: str, req: ConfirmRequest) -> DieSample:
        s = self._require(sample_id)
        self._check_status(s, [SampleStatus.PENDING_CONFIRM], "封样确认")

        if len(s.test_records) == 0:
            raise ValueError("未有测试记录，禁止封样")
        latest_test = s.test_records[-1]
        if not latest_test.is_passed:
            raise ValueError("最新测试结果未通过，禁止封样")

        other_versions = self._find_other_versions(s)
        for ov in other_versions:
            if ov.status == SampleStatus.PENDING_CONFIRM or ov.status == SampleStatus.MODIFYING:
                pass

        for ov in other_versions:
            if ov.die_version == req.version and ov.status == SampleStatus.SEALED and ov.id != s.id:
                raise ValueError(
                    f"项目 {s.project_name} 下刀模 {s.die_number} 版本 {req.version} 已被其他记录封样，禁止重复封样"
                )

        if s.die_version != req.version:
            key_new = self._make_key(s.project_name, s.die_number, req.version)
            key_old = self._make_key(s.project_name, s.die_number, s.die_version)
            if key_new in self._index_project_version and self._index_project_version[key_new] != s.id:
                raise ValueError(
                    f"项目 {s.project_name} 下刀模 {s.die_number} 版本 {req.version} 已存在，不能变更为此版本号"
                )
            del self._index_project_version[key_old]
            s.die_version = req.version
            self._index_project_version[key_new] = s.id

        s.seal_record = SealRecord(
            sealer=req.confirmer,
            seal_date=datetime.now(),
            version=req.version,
            notes=req.notes,
        )
        s.status = SampleStatus.SEALED
        s.updated_at = datetime.now()
        return s

    def reject_sample(self, sample_id: str, req: RejectRequest) -> DieSample:
        s = self._require(sample_id)
        self._check_status(s, [SampleStatus.PENDING_CONFIRM], "退回")
        record = RejectRecord(
            id=str(uuid.uuid4()),
            round=req.round,
            reason=req.reason,
            rejecter=req.rejecter,
            reject_date=datetime.now(),
            description=req.description,
        )
        s.reject_records.append(record)
        s.status = SampleStatus.MODIFYING
        s.updated_at = datetime.now()
        return s

    ALLOWED_STATUS_TRANSITIONS: Dict[SampleStatus, List[SampleStatus]] = {
        SampleStatus.PENDING_OPEN: [SampleStatus.SAMPLING, SampleStatus.CANCELLED],
        SampleStatus.SAMPLING: [SampleStatus.PENDING_TEST, SampleStatus.MODIFYING, SampleStatus.CANCELLED],
        SampleStatus.PENDING_TEST: [SampleStatus.SAMPLING, SampleStatus.CANCELLED],
        SampleStatus.PENDING_CONFIRM: [SampleStatus.MODIFYING, SampleStatus.CANCELLED],
        SampleStatus.MODIFYING: [SampleStatus.SAMPLING, SampleStatus.PENDING_TEST, SampleStatus.CANCELLED],
        SampleStatus.SEALED: [SampleStatus.CANCELLED],
        SampleStatus.CANCELLED: [],
    }

    def change_status(self, sample_id: str, target_status: SampleStatus, operator: str) -> DieSample:
        s = self._require(sample_id)
        if target_status == SampleStatus.SEALED:
            raise ValueError("已封样状态仅可通过封样确认接口设置，禁止直接切换")
        if target_status == SampleStatus.PENDING_CONFIRM:
            raise ValueError("待确认状态仅可通过提交测试结果触发，禁止直接切换")
        if s.status == SampleStatus.CANCELLED:
            raise ValueError("已取消的记录不可重新激活，如需恢复请新建记录")
        allowed = self.ALLOWED_STATUS_TRANSITIONS.get(s.status, [])
        if target_status not in allowed:
            allowed_str = "、".join(x.value for x in allowed) if allowed else "无"
            raise ValueError(f"当前状态 {s.status.value} 不允许切换为 {target_status.value}，允许的目标状态: [{allowed_str}]")
        if target_status == SampleStatus.CANCELLED:
            key = self._make_key(s.project_name, s.die_number, s.die_version)
            if key in self._index_project_version:
                del self._index_project_version[key]
        s.status = target_status
        s.updated_at = datetime.now()
        return s

    def detect_anomalies(self) -> List[AnomalyReport]:
        anomalies: List[AnomalyReport] = []
        now = datetime.now()

        spec_cracking: Dict[str, set] = defaultdict(set)
        for s in self.samples.values():
            for t in s.test_records:
                if t.cracking_description and str(t.cracking_description).strip():
                    spec_cracking[s.board_spec].add(s.id)
                    break
        for spec, ids in spec_cracking.items():
            if len(ids) >= CRACKING_CONCENTRATION_THRESHOLD:
                unique_ids = list(ids)
                anomalies.append(AnomalyReport(
                    type="同规格开裂集中",
                    level="high" if len(unique_ids) >= 5 else "medium",
                    description=f"纸板规格 {spec} 有 {len(unique_ids)} 条记录报告开裂问题，超过阈值 {CRACKING_CONCENTRATION_THRESHOLD}",
                    related_sample_ids=unique_ids,
                    details={
                        "board_spec": spec,
                        "sample_count": len(unique_ids),
                        "threshold": CRACKING_CONCENTRATION_THRESHOLD,
                    },
                ))

        overdue_ids = []
        for s in self.samples.values():
            if s.status in [SampleStatus.SAMPLING, SampleStatus.PENDING_TEST, SampleStatus.MODIFYING]:
                last_date = s.updated_at
                if s.deadline:
                    target_date = s.deadline
                    if now > target_date:
                        overdue_ids.append(s.id)
                else:
                    if (now - last_date).days >= TEST_OVERDUE_DAYS:
                        overdue_ids.append(s.id)
        if overdue_ids:
            anomalies.append(AnomalyReport(
                type="测试超期",
                level="medium",
                description=f"有 {len(overdue_ids)} 条记录测试/修改超期（超过 {TEST_OVERDUE_DAYS} 天或已过截止日期）",
                related_sample_ids=overdue_ids,
                details={
                    "count": len(overdue_ids),
                    "overdue_days_threshold": TEST_OVERDUE_DAYS,
                },
            ))

        unconfirmed_ids = []
        for s in self.samples.values():
            if s.status == SampleStatus.MODIFYING and len(s.modification_records) > 0:
                last_mod = s.modification_records[-1]
                if (now - last_mod.modify_date).days >= UNCONFIRMED_AFTER_MODIFY_DAYS:
                    unconfirmed_ids.append(s.id)
        if unconfirmed_ids:
            anomalies.append(AnomalyReport(
                type="修改后未确认",
                level="medium",
                description=f"有 {len(unconfirmed_ids)} 条记录在修改后 {UNCONFIRMED_AFTER_MODIFY_DAYS} 天仍未重新确认",
                related_sample_ids=unconfirmed_ids,
                details={
                    "count": len(unconfirmed_ids),
                    "days_threshold": UNCONFIRMED_AFTER_MODIFY_DAYS,
                },
            ))

        high_reject_ids = []
        reject_details = []
        for s in self.samples.values():
            if len(s.reject_records) >= HIGH_REJECTION_THRESHOLD:
                high_reject_ids.append(s.id)
                reject_details.append({
                    "sample_id": s.id,
                    "project_name": s.project_name,
                    "die_number": s.die_number,
                    "reject_count": len(s.reject_records),
                })
        if high_reject_ids:
            anomalies.append(AnomalyReport(
                type="退回次数过高",
                level="high",
                description=f"有 {len(high_reject_ids)} 条记录退回次数超过阈值 {HIGH_REJECTION_THRESHOLD} 次",
                related_sample_ids=high_reject_ids,
                details={
                    "items": reject_details,
                    "threshold": HIGH_REJECTION_THRESHOLD,
                },
            ))

        return anomalies

    def get_reject_reason_distribution(self) -> List[RejectReasonDistribution]:
        counter: Dict[str, int] = defaultdict(int)
        total = 0
        for s in self.samples.values():
            for r in s.reject_records:
                counter[r.reason] += 1
                total += 1
        if total == 0:
            return []
        result = []
        for reason, count in counter.items():
            result.append(RejectReasonDistribution(
                reason=reason,
                count=count,
                percentage=round(count / total * 100, 2),
            ))
        result.sort(key=lambda x: x.count, reverse=True)
        return result

    def get_pending_confirm_list(self) -> List[DieSample]:
        samples = []
        for s in self.samples.values():
            if s.status == SampleStatus.PENDING_CONFIRM:
                samples.append(s)
        samples.sort(key=lambda x: (
            {"紧急": 0, "高": 1, "普通": 2, "低": 3}.get(x.priority, 2),
            x.updated_at,
        ))
        return samples

    def get_spec_risk_ranking(self) -> List[SpecRiskItem]:
        spec_stats: Dict[str, Dict] = defaultdict(lambda: {
            "total": 0,
            "cracking_ids": set(),
            "reject_ids": set(),
            "ids": set(),
        })
        for s in self.samples.values():
            st = spec_stats[s.board_spec]
            st["total"] += 1
            st["ids"].add(s.id)
            for t in s.test_records:
                if t.cracking_description and str(t.cracking_description).strip():
                    st["cracking_ids"].add(s.id)
                    break
            if len(s.reject_records) > 0:
                st["reject_ids"].add(s.id)

        result = []
        for spec, data in spec_stats.items():
            total = data["total"]
            cracking_count = len(data["cracking_ids"])
            reject_count = len(data["reject_ids"])
            cracking_rate = cracking_count / max(total, 1)
            reject_rate = reject_count / max(total, 1)
            risk_score = round((cracking_rate * 0.5 + reject_rate * 0.5) * 100, 2)

            if risk_score >= 50:
                risk_level = "high"
            elif risk_score >= 25:
                risk_level = "medium"
            elif risk_score >= 10:
                risk_level = "low"
            else:
                risk_level = "safe"

            result.append(SpecRiskItem(
                board_spec=spec,
                total_samples=total,
                cracking_count=cracking_count,
                reject_count=reject_count,
                risk_score=risk_score,
                risk_level=risk_level,
                related_sample_ids=list(data["ids"]),
            ))
        result.sort(key=lambda x: x.risk_score, reverse=True)
        return result

    def _require(self, sample_id: str) -> DieSample:
        s = self.samples.get(sample_id)
        if not s:
            raise ValueError(f"刀模打样记录 {sample_id} 不存在")
        return s

    def _check_status(self, s: DieSample, allowed: List[SampleStatus], action: str) -> None:
        if s.status not in allowed:
            allowed_str = "、".join(x.value for x in allowed)
            raise ValueError(f"操作 [{action}] 失败：当前状态为 {s.status.value}，仅允许在状态 [{allowed_str}] 下执行")

    def _find_other_versions(self, s: DieSample) -> List[DieSample]:
        others = []
        for x in self.samples.values():
            if x.id == s.id:
                continue
            if x.project_name == s.project_name and x.die_number == s.die_number:
                others.append(x)
        return others
