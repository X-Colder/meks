import csv
import json
import math
import re
import zipfile
from collections import Counter
from io import BytesIO, StringIO
from uuid import UUID
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meks.api.schemas.clinical_datasets import (
    ClinicalColumn,
    ClinicalDatasetDetail,
    ClinicalDatasetResponse,
    ClinicalLongitudinalResponse,
    ClinicalPatientSummary,
    ClinicalStatsResponse,
    ClinicalTimelineEvent,
    ResearchSuggestionRequest,
)
from meks.core.exceptions import NotFoundException, MeksException
from meks.core.rbac import Permission
from meks.dependencies import require_permission
from meks.models.base import get_db
from meks.models.clinical_dataset import ClinicalDataset
from meks.models.user import User

router = APIRouter()

MISSING_VALUES = {"", "na", "n/a", "null", "none", "nan", "-", "--", "未知", "缺失"}


def _normalize_cell(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_csv(file_data: bytes) -> list[dict]:
    text = file_data.decode("utf-8-sig")
    rows = list(csv.DictReader(StringIO(text)))
    return [{k.strip(): _normalize_cell(v) for k, v in row.items() if k is not None} for row in rows]


def _xlsx_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.get("t")
    value_el = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
    inline_el = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is")
    if inline_el is not None:
        text = "".join(inline_el.itertext())
        return _normalize_cell(text)
    if value_el is None or value_el.text is None:
        return ""
    if cell_type == "s":
        try:
            return shared_strings[int(value_el.text)]
        except (ValueError, IndexError):
            return ""
    return _normalize_cell(value_el.text)


def _col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch.upper()) - ord("A") + 1)
    return max(0, value - 1)


def _parse_xlsx(file_data: bytes) -> list[dict]:
    with zipfile.ZipFile(BytesIO(file_data)) as z:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for item in root.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                shared_strings.append("".join(item.itertext()))

        sheet_name = "xl/worksheets/sheet1.xml"
        if sheet_name not in z.namelist():
            sheet_name = next((name for name in z.namelist() if name.startswith("xl/worksheets/sheet")), "")
        if not sheet_name:
            return []
        root = ET.fromstring(z.read(sheet_name))
        raw_rows: list[list[str]] = []
        for row in root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
            values: list[str] = []
            for cell in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                idx = _col_index(cell.get("r", "A1"))
                while len(values) <= idx:
                    values.append("")
                values[idx] = _xlsx_cell_value(cell, shared_strings)
            raw_rows.append(values)

    if not raw_rows:
        return []
    headers = [_normalize_cell(v) or f"column_{i + 1}" for i, v in enumerate(raw_rows[0])]
    rows: list[dict] = []
    for raw in raw_rows[1:]:
        row = {headers[i]: _normalize_cell(raw[i]) if i < len(raw) else "" for i in range(len(headers))}
        if any(v for v in row.values()):
            rows.append(row)
    return rows


def _is_missing(value: str) -> bool:
    return _normalize_cell(value).lower() in MISSING_VALUES


def _is_number(value: str) -> bool:
    if _is_missing(value):
        return False
    try:
        float(value)
        return True
    except ValueError:
        return False


def _infer_type(values: list[str]) -> str:
    present = [v for v in values if not _is_missing(v)]
    if not present:
        return "unknown"
    numeric_rate = sum(1 for v in present if _is_number(v)) / len(present)
    if numeric_rate >= 0.85:
        return "numeric"
    unique_count = len(set(present))
    if unique_count <= min(20, max(2, len(present) // 2)):
        return "categorical"
    return "text"


def _role_for_column(name: str) -> str | None:
    lower = name.lower()
    if any(key in lower for key in ("outcome", "event", "death", "recurrence", "复发", "死亡", "结局")):
        return "outcome"
    if any(key in lower for key in ("group", "treatment", "exposure", "分组", "治疗", "暴露")):
        return "exposure"
    if any(key in lower for key in ("age", "sex", "gender", "bmi", "年龄", "性别")):
        return "covariate"
    if any(key in lower for key in ("id", "住院号", "患者")):
        return "identifier"
    return None


def _find_column(columns: list[str], keywords: tuple[str, ...]) -> str | None:
    lower_by_col = {col: col.lower().replace(" ", "").replace("_", "") for col in columns}
    for col, lower in lower_by_col.items():
        if any(key in lower for key in keywords):
            return col
    return None


def _find_columns(columns: list[str], keywords: tuple[str, ...]) -> list[str]:
    matched = []
    for col in columns:
        lower = col.lower().replace(" ", "").replace("_", "")
        if any(key in lower for key in keywords):
            matched.append(col)
    return matched


def _date_sort_key(value: str | None) -> str:
    return value or "9999-99-99"


def _compact_details(row: dict, columns: list[str]) -> dict:
    details = {}
    for col in columns:
        value = _normalize_cell(row.get(col, ""))
        if value and not _is_missing(value):
            details[col] = value
    return details


def _longitudinal_view(dataset: ClinicalDataset) -> ClinicalLongitudinalResponse:
    rows = json.loads(dataset.rows_json)
    columns = list(rows[0].keys()) if rows else []
    warnings: list[str] = []
    patient_col = _find_column(
        columns,
        (
            "researchpatientid", "patientid", "patientno", "patient", "empi", "mrn",
            "personid", "subjectid", "患者id", "病人id", "患者编号", "研究编号",
            "住院号", "门诊号", "就诊卡号",
        ),
    )
    date_col = _find_column(
        columns,
        (
            "encounterdate", "visitdate", "admissiondate", "dischargedate", "eventdate",
            "date", "time", "就诊日期", "入院日期", "出院日期", "记录时间", "发生时间",
        ),
    )
    sex_col = _find_column(columns, ("sex", "gender", "性别"))
    age_col = _find_column(columns, ("age", "年龄"))
    encounter_type_col = _find_column(columns, ("encountertype", "visittype", "eventtype", "就诊类型", "事件类型"))
    diagnosis_cols = _find_columns(columns, ("diagnosis", "diagnose", "icd", "disease", "诊断", "疾病"))
    medication_cols = _find_columns(columns, ("medication", "drug", "medicine", "用药", "药品"))
    procedure_cols = _find_columns(columns, ("procedure", "operation", "surgery", "手术", "操作", "治疗"))
    outcome_cols = _find_columns(columns, ("outcome", "death", "recurrence", "readmission", "结局", "死亡", "复发", "再入院"))

    if not patient_col:
        warnings.append("未识别到患者 ID 字段，系统暂按每行一个患者生成研究编号；真实医院数据应优先映射患者主索引。")
    if not date_col:
        warnings.append("未识别到就诊/事件日期字段，时间线只能按导入顺序展示。")
    if not diagnosis_cols:
        warnings.append("未识别到诊断字段，无法形成疾病/共病摘要。")

    grouped: dict[str, list[dict]] = {}
    for idx, row in enumerate(rows):
        pid = _normalize_cell(row.get(patient_col, "")) if patient_col else f"ROW-{idx + 1:06d}"
        if not pid:
            pid = f"UNKNOWN-{idx + 1:06d}"
        grouped.setdefault(pid, []).append(row)

    patients: list[ClinicalPatientSummary] = []
    events: list[ClinicalTimelineEvent] = []
    diagnosis_counter: Counter[str] = Counter()
    cohort_preview: list[dict] = []
    detail_cols = [col for col in [
        date_col, encounter_type_col, age_col, sex_col,
        *diagnosis_cols[:3], *medication_cols[:2], *procedure_cols[:2], *outcome_cols[:2],
    ] if col]

    for pid, patient_rows in grouped.items():
        sorted_rows = sorted(patient_rows, key=lambda item: _date_sort_key(_normalize_cell(item.get(date_col, "")) if date_col else None))
        diagnoses: list[str] = []
        risk_flags: list[str] = []
        for row in sorted_rows:
            for col in diagnosis_cols:
                value = _normalize_cell(row.get(col, ""))
                if value and not _is_missing(value):
                    for diag in re.split(r"[;；|、]", value):
                        diag = diag.strip()
                        if diag and diag not in diagnoses:
                            diagnoses.append(diag)
                            diagnosis_counter[diag] += 1
            for col in outcome_cols:
                value = _normalize_cell(row.get(col, ""))
                if value and value not in {"0", "否", "无", "none", "None"}:
                    risk_flags.append(f"{col}: {value}")

        first_visit = _normalize_cell(sorted_rows[0].get(date_col, "")) if date_col and sorted_rows else None
        last_visit = _normalize_cell(sorted_rows[-1].get(date_col, "")) if date_col and sorted_rows else None
        patients.append(
            ClinicalPatientSummary(
                patient_id=pid,
                age=_normalize_cell(sorted_rows[-1].get(age_col, "")) if age_col and sorted_rows else None,
                sex=_normalize_cell(sorted_rows[-1].get(sex_col, "")) if sex_col and sorted_rows else None,
                first_visit=first_visit or None,
                last_visit=last_visit or None,
                encounter_count=len(sorted_rows),
                diagnosis_count=len(diagnoses),
                diagnoses=diagnoses[:8],
                risk_flags=risk_flags[:5],
            )
        )
        cohort_preview.append(
            {
                "research_patient_id": pid,
                "age": _normalize_cell(sorted_rows[-1].get(age_col, "")) if age_col and sorted_rows else "",
                "sex": _normalize_cell(sorted_rows[-1].get(sex_col, "")) if sex_col and sorted_rows else "",
                "first_visit": first_visit or "",
                "last_visit": last_visit or "",
                "encounter_count": len(sorted_rows),
                "diagnoses": "；".join(diagnoses[:6]),
                "comorbidity_count": max(0, len(diagnoses) - 1),
                "outcome_signals": "；".join(risk_flags[:3]),
            }
        )
        for row in sorted_rows:
            date_value = _normalize_cell(row.get(date_col, "")) if date_col else None
            event_type = _normalize_cell(row.get(encounter_type_col, "")) if encounter_type_col else "临床事件"
            title_parts = []
            for col in diagnosis_cols[:2]:
                value = _normalize_cell(row.get(col, ""))
                if value and not _is_missing(value):
                    title_parts.append(value)
            title = " / ".join(title_parts) or event_type or "临床事件"
            events.append(
                ClinicalTimelineEvent(
                    patient_id=pid,
                    date=date_value or None,
                    event_type=event_type or "临床事件",
                    title=title,
                    details=_compact_details(row, detail_cols),
                )
            )

    patients.sort(key=lambda item: (item.encounter_count, item.diagnosis_count), reverse=True)
    events.sort(key=lambda item: (item.patient_id, _date_sort_key(item.date)))
    return ClinicalLongitudinalResponse(
        patient_id_column=patient_col,
        date_column=date_col,
        diagnosis_columns=diagnosis_cols,
        patient_count=len(grouped),
        event_count=len(rows),
        patients=patients[:100],
        events=events[:300],
        top_diagnoses=[{"diagnosis": name, "count": count} for name, count in diagnosis_counter.most_common(12)],
        cohort_preview=cohort_preview[:100],
        warnings=warnings,
    )


def _profile_columns(rows: list[dict]) -> list[ClinicalColumn]:
    columns = list(rows[0].keys()) if rows else []
    result: list[ClinicalColumn] = []
    for name in columns:
        values = [_normalize_cell(row.get(name, "")) for row in rows]
        missing = sum(1 for v in values if _is_missing(v))
        present = [v for v in values if not _is_missing(v)]
        result.append(
            ClinicalColumn(
                name=name,
                label=name,
                inferred_type=_infer_type(values),
                missing_count=missing,
                missing_rate=round(missing / len(values), 4) if values else 0,
                unique_count=len(set(present)),
                role=_role_for_column(name),
            )
        )
    return result


def _numeric_summary(rows: list[dict], columns: list[ClinicalColumn]) -> dict:
    summary = {}
    for col in columns:
        if col.inferred_type != "numeric":
            continue
        nums = [float(row[col.name]) for row in rows if _is_number(_normalize_cell(row.get(col.name, "")))]
        if not nums:
            continue
        nums.sort()
        mean = sum(nums) / len(nums)
        summary[col.name] = {
            "count": len(nums),
            "mean": round(mean, 4),
            "min": nums[0],
            "max": nums[-1],
            "median": nums[len(nums) // 2],
        }
    return summary


def _categorical_summary(rows: list[dict], columns: list[ClinicalColumn]) -> dict:
    summary = {}
    for col in columns:
        if col.inferred_type != "categorical":
            continue
        values = [_normalize_cell(row.get(col.name, "")) for row in rows if not _is_missing(_normalize_cell(row.get(col.name, "")))]
        counts = Counter(values).most_common(10)
        summary[col.name] = [{"value": value, "count": count} for value, count in counts]
    return summary


def _dataset_stats(dataset: ClinicalDataset) -> ClinicalStatsResponse:
    rows = json.loads(dataset.rows_json)
    columns = [ClinicalColumn(**item) for item in json.loads(dataset.columns_json)]
    return ClinicalStatsResponse(
        columns=columns,
        numeric_summary=_numeric_summary(rows, columns),
        categorical_summary=_categorical_summary(rows, columns),
        missing_summary=[
            {
                "name": col.name,
                "missing_count": col.missing_count,
                "missing_rate": col.missing_rate,
            }
            for col in sorted(columns, key=lambda item: item.missing_rate, reverse=True)
        ],
    )


async def _get_dataset(dataset_id: str, user: User, db: AsyncSession) -> ClinicalDataset:
    result = await db.execute(
        select(ClinicalDataset).where(
            ClinicalDataset.id == UUID(dataset_id),
            ClinicalDataset.owner_id == user.id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise NotFoundException("病例数据集")
    return dataset


@router.post("/upload", response_model=ClinicalDatasetDetail)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    user: User = Depends(require_permission(Permission.DOC_UPLOAD)),
    db: AsyncSession = Depends(get_db),
):
    file_data = await file.read()
    filename = file.filename or "dataset.csv"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "csv":
        rows = _parse_csv(file_data)
    elif ext == "xlsx":
        rows = _parse_xlsx(file_data)
    else:
        raise MeksException(400, "仅支持 CSV 或 XLSX 数据集")
    if not rows:
        raise MeksException(400, "未解析到有效数据行")
    columns = _profile_columns(rows)
    dataset = ClinicalDataset(
        name=name or filename.rsplit(".", 1)[0],
        original_filename=filename,
        row_count=len(rows),
        column_count=len(columns),
        columns_json=json.dumps([col.model_dump() for col in columns], ensure_ascii=False),
        rows_json=json.dumps(rows, ensure_ascii=False),
        owner_id=user.id,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return ClinicalDatasetDetail(
        **ClinicalDatasetResponse.model_validate(dataset).model_dump(),
        columns=columns,
        preview_rows=rows[:20],
    )


@router.get("", response_model=list[ClinicalDatasetResponse])
async def list_datasets(
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClinicalDataset)
        .where(ClinicalDataset.owner_id == user.id)
        .order_by(ClinicalDataset.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{dataset_id}", response_model=ClinicalDatasetDetail)
async def get_dataset(
    dataset_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    dataset = await _get_dataset(dataset_id, user, db)
    rows = json.loads(dataset.rows_json)
    columns = [ClinicalColumn(**item) for item in json.loads(dataset.columns_json)]
    return ClinicalDatasetDetail(
        **ClinicalDatasetResponse.model_validate(dataset).model_dump(),
        columns=columns,
        preview_rows=rows[:50],
    )


@router.get("/{dataset_id}/stats", response_model=ClinicalStatsResponse)
async def get_dataset_stats(
    dataset_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    dataset = await _get_dataset(dataset_id, user, db)
    return _dataset_stats(dataset)


@router.get("/{dataset_id}/longitudinal", response_model=ClinicalLongitudinalResponse)
async def get_longitudinal_view(
    dataset_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    dataset = await _get_dataset(dataset_id, user, db)
    return _longitudinal_view(dataset)


@router.post("/{dataset_id}/research-suggestions")
async def generate_research_suggestions(
    dataset_id: str,
    request: ResearchSuggestionRequest,
    user: User = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
):
    dataset = await _get_dataset(dataset_id, user, db)
    rows = json.loads(dataset.rows_json)
    stats = _dataset_stats(dataset)
    prompt = f"""你是一位临床科研方法学顾问。请根据以下病例数据集字段和统计概况，为医生提出可行科研方向。

数据集名称：{dataset.name}
样本量：{dataset.row_count}
字段数：{dataset.column_count}
医生关注问题：{request.clinical_question or '未提供'}
指定暴露变量：{request.exposure or '未指定'}
指定结局变量：{request.outcome or '未指定'}

字段概况：
{json.dumps([col.model_dump() for col in stats.columns], ensure_ascii=False)[:6000]}

数值变量摘要：
{json.dumps(stats.numeric_summary, ensure_ascii=False)[:4000]}

分类变量摘要：
{json.dumps(stats.categorical_summary, ensure_ascii=False)[:4000]}

请输出：
1. 适合该数据集的研究题目（3-5个）
2. 推荐的暴露变量、结局变量和协变量
3. 推荐统计方法
4. 数据质量风险与补充建议
5. 可写入论文方法/结果部分的段落草稿
"""
    from meks.llm.router import get_llm_provider

    provider = get_llm_provider()
    return {"content": await provider.completion(prompt)}
