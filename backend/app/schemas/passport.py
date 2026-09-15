from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int

class DocumentInfo(BaseModel):
    type: str = "passport"
    document_type_code: str = "P"
    issuing_country: Optional[str] = None
    issuing_country_name: Optional[str] = None

class HolderInfo(BaseModel):
    surname: Optional[str] = None
    surname_mrz: Optional[str] = None
    given_names: Optional[str] = None
    given_names_mrz: Optional[str] = None
    nationality: Optional[str] = None
    nationality_name: Optional[str] = None
    date_of_birth: Optional[str] = None  # ISO YYYY-MM-DD
    date_of_birth_raw_mrz: Optional[str] = None  # YYMMDD
    sex: Optional[str] = None  # M, F, X, etc.
    place_of_birth: Optional[str] = None

class PassportData(BaseModel):
    passport_number: Optional[str] = None
    issue_date: Optional[str] = None  # ISO YYYY-MM-DD
    expiry_date: Optional[str] = None  # ISO YYYY-MM-DD
    expiry_date_raw_mrz: Optional[str] = None  # YYMMDD
    issuing_authority: Optional[str] = None
    personal_number: Optional[str] = None

class PortraitInfo(BaseModel):
    url: Optional[str] = None  # base64 data URL or relative endpoint
    confidence: float = 0.0
    bbox: Optional[List[int]] = None  # [x, y, w, h]

class MRZChecks(BaseModel):
    document_number_checksum: bool = False
    birth_date_checksum: bool = False
    expiry_date_checksum: bool = False
    personal_number_checksum: Optional[bool] = None
    composite_checksum: bool = False

class MRZData(BaseModel):
    format: str = "TD3"
    raw_lines: List[str] = []
    valid: bool = False
    checks: MRZChecks = Field(default_factory=MRZChecks)
    error_corrections_applied: List[str] = []

class QualityData(BaseModel):
    acceptable: bool = True
    blur_score: float = 1.0  # normalized (0-1)
    laplacian_variance: float = 0.0
    glare_detected: bool = False
    glare_ratio: float = 0.0
    resolution_ok: bool = True
    dimensions: List[int] = [0, 0]  # [width, height]
    passport_fully_visible: bool = True
    actionable_feedback: List[str] = []

class FieldEvidence(BaseModel):
    value: Optional[str] = None
    confidence: float = 0.0
    source: str = "unknown"  # "mrz", "visual", "reconciled", "manual"
    mrz_value: Optional[str] = None
    visual_value: Optional[str] = None
    checksum_valid: Optional[bool] = None
    sources_match: bool = False
    review_required: bool = False
    status: str = "NEEDS REVIEW"  # "VERIFIED", "VERIFIED WITH WARNING", "NEEDS REVIEW"
    note: Optional[str] = None

class ConfidenceScores(BaseModel):
    overall: float = 0.0
    fields: Dict[str, FieldEvidence] = Field(default_factory=dict)

class PassportAnalysisResponse(BaseModel):
    session_id: str
    document: DocumentInfo
    holder: HolderInfo
    passport: PassportData
    portrait: Optional[PortraitInfo] = None
    mrz: MRZData
    quality: QualityData
    confidence: ConfidenceScores
    review_required: bool = False
    warnings: List[str] = []
    annotated_image_url: Optional[str] = None
    normalized_image_url: Optional[str] = None

class ConfirmationRequest(BaseModel):
    document: DocumentInfo
    holder: HolderInfo
    passport: PassportData
    confirmed_by_user: bool = True
    user_notes: Optional[str] = None

class ConfirmationResponse(BaseModel):
    session_id: str
    status: str = "confirmed"
    confirmed_at: str
    data: Dict[str, Any]
