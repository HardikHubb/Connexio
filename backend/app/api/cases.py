from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import CaseCreateRequest, CaseSummary, IngestResponse, ParsedDocument, SourceType
from app.services import case_service, ingestion_service

router = APIRouter()


@router.post("/cases", response_model=CaseSummary)
def create_case(payload: CaseCreateRequest):
    try:
        return case_service.create_case(name=payload.name, case_id=payload.case_id)
    except case_service.CaseAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/cases", response_model=list[CaseSummary])
def list_cases():
    return case_service.list_cases()


@router.get("/cases/{case_id}")
def get_case(case_id: str):
    try:
        return case_service.get_case(case_id)
    except case_service.CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/cases/{case_id}/ingest", response_model=IngestResponse)
def ingest_file(case_id: str, source_type: SourceType = Form(...), file: UploadFile = File(...)):
    try:
        return ingestion_service.ingest_file(case_id, source_type, file)
    except ingestion_service.IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cases/{case_id}/documents", response_model=list[ParsedDocument])
def list_documents(case_id: str):
    try:
        return ingestion_service.list_parsed_documents(case_id)
    except case_service.CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/cases/{case_id}/documents/{source_id}", response_model=ParsedDocument)
def get_document(case_id: str, source_id: str):
    try:
        return ingestion_service.get_parsed_document(case_id, source_id)
    except ingestion_service.IngestionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
