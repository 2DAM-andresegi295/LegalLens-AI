from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from apps.api.app.services.pdf import PDFExtractionError, extract_text_from_pdf
from packages.agents import LegalAnalysisAgent
from packages.domain import Document

router = APIRouter(prefix="/v1", tags=["legal-analysis"])
agent = LegalAnalysisAgent()


class AnalyzeRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    text: str = Field(..., min_length=20)
    source_type: str = Field(default="text", min_length=2, max_length=50)
    contract_type: str = Field(default="general", min_length=3, max_length=20)


class FindingResponse(BaseModel):
    clause_title: str
    severity: str
    label: str
    evidence: str
    recommendation: str


class AnalyzeResponse(BaseModel):
    title: str
    risk_level: str
    summary: str
    key_data: dict[str, str]
    source_type: str
    text: str
    engine: str
    llm_used: bool
    findings: list[FindingResponse]


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_contract(payload: AnalyzeRequest) -> dict[str, object]:
    document = Document(
        title=payload.title,
        text=payload.text,
        source_type=payload.source_type,
        contract_type=payload.contract_type,
    )
    result = agent.analyze(document)
    return result.to_dict()


@router.post("/analyze-file", response_model=AnalyzeResponse)
async def analyze_contract_file(
    title: str = Form(..., min_length=3, max_length=150),
    contract_type: str = Form("general"),
    file: UploadFile = File(...),
) -> dict[str, object]:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Solo se admiten archivos PDF en esta fase.")

    file_bytes = await file.read()
    try:
        text = extract_text_from_pdf(file_bytes)
    except PDFExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document = Document(
        title=title,
        text=text,
        source_type="pdf",
        contract_type=contract_type,
    )
    result = agent.analyze(document)
    return result.to_dict()


