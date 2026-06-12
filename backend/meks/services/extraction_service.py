import json
import re
from datetime import date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from meks.llm.base import LLMProvider
from meks.llm.prompts.extraction import MEDICAL_RECORD_EXTRACTION_PROMPT
from meks.models.medical_record import MedicalRecord, Severity, TreatmentOutcome


def _parse_extraction_response(raw: str) -> dict:
    raw = raw.strip()
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {}


def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y.%m.%d"):
        try:
            return datetime.strptime(val, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _parse_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _parse_json_list(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, list):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        return json.dumps([val], ensure_ascii=False)
    return None


def _mask_id_number(val: str | None) -> str | None:
    if not val or len(val) < 4:
        return val
    return "*" * (len(val) - 4) + val[-4:]


def _parse_enum(val: str | None, enum_cls: type) -> object | None:
    if not val:
        return None
    try:
        return enum_cls(val.lower())
    except ValueError:
        return None


async def extract_medical_record(text: str, provider: LLMProvider) -> dict:
    prompt = MEDICAL_RECORD_EXTRACTION_PROMPT.format(text=text[:8000])
    raw_response = await provider.completion(prompt)
    return _parse_extraction_response(raw_response)


async def save_medical_record(
    db: AsyncSession, document_id: UUID, data: dict
) -> MedicalRecord:
    record = MedicalRecord(
        document_id=document_id,
        patient_name=data.get("patient_name"),
        gender=data.get("gender"),
        age=_parse_int(data.get("age")),
        phone=data.get("phone"),
        id_number=_mask_id_number(data.get("id_number")),
        occupation=data.get("occupation"),
        admission_date=_parse_date(data.get("admission_date")),
        discharge_date=_parse_date(data.get("discharge_date")),
        hospital_days=_parse_int(data.get("hospital_days")),
        department=data.get("department"),
        attending_doctor=data.get("attending_doctor"),
        admission_number=data.get("admission_number"),
        primary_diagnosis=data.get("primary_diagnosis"),
        icd10_code=data.get("icd10_code"),
        secondary_diagnoses=_parse_json_list(data.get("secondary_diagnoses")),
        severity=_parse_enum(data.get("severity"), Severity),
        medications=_parse_json_list(data.get("medications")),
        procedures=_parse_json_list(data.get("procedures")),
        treatment_type=data.get("treatment_type"),
        treatment_outcome=_parse_enum(data.get("treatment_outcome"), TreatmentOutcome),
        discharge_instructions=data.get("discharge_instructions"),
        follow_up=data.get("follow_up"),
        chief_complaint=data.get("chief_complaint"),
        present_illness=data.get("present_illness"),
        past_history=data.get("past_history"),
        allergy_history=data.get("allergy_history"),
    )
    db.add(record)
    return record
