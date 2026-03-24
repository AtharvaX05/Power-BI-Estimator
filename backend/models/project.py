"""Project and estimation models / schemas."""
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List, Optional
from enum import Enum


class Complexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DataVolume(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DeploymentType(str, Enum):
    SERVICE = "power_bi_service"
    EMBEDDED = "embedded"
    GATEWAY = "gateway"
    FULL = "full"


class PerformanceLevel(str, Enum):
    NONE = "none"
    STANDARD = "standard"
    COMPLEX = "complex"


class EstimationInput(BaseModel):
    """All input fields for effort estimation (hours-based engine v2)."""

    # Project Metadata & Scoping
    scoping_hours: float = 4.0

    # Data Source Integration
    num_data_sources: int = 1
    data_source_types: List[str] = ["database"]  # database, api, excel, sharepoint
    data_source_complexity: Complexity = Complexity.MEDIUM
    # Kept for backward compat with v1 versions (ignored by v2 engine)
    data_volume: DataVolume = DataVolume.MEDIUM

    # Data Transformation
    num_tables: int = 5
    transformation_complexity: Complexity = Complexity.MEDIUM

    # Data Modeling (multiple models support)
    num_data_models: int = 1
    modeling_complexity: Complexity = Complexity.MEDIUM
    incremental_refresh: bool = False

    # DAX / Business Logic
    dax_complexity: Complexity = Complexity.MEDIUM
    num_measures: int = 10

    # Report Development
    num_reports: int = 1
    pages_per_report: int = 5
    report_complexity: Complexity = Complexity.MEDIUM
    # Per-report feature flags
    feature_tooltips: bool = False
    feature_subscriptions: bool = False
    feature_alerts: bool = False
    # UI/UX Designer contribution (1.2x on report effort)
    ui_ux_designer: bool = False

    # Security
    rls_required: bool = False
    # Kept for backward compat; v2 uses fixed 6h base → 12h final
    rls_complexity: Complexity = Complexity.LOW

    # Performance Optimization (standard / complex / none)
    performance_optimization: bool = False
    performance_level: PerformanceLevel = PerformanceLevel.NONE

    # Deployment
    deployment_type: DeploymentType = DeploymentType.SERVICE
    deployment_hours: float = 8.0

    # UAT & Iterations
    uat_cycles: int = 2

    # Documentation
    documentation_required: bool = True

    # Resource Overhead
    tl_percentage: float = 10.0   # Team Lead %
    ba_percentage: float = 10.0   # Business Analyst %
    buffer_percentage: float = 0.0  # Buffer % applied per module

    @field_validator("tl_percentage", "ba_percentage", "buffer_percentage")
    @classmethod
    def _validate_overhead(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError("Percentage must be between 0 and 100")
        return v

    @field_validator("num_data_sources", "num_tables", "num_data_models",
                     "num_measures", "num_reports", "pages_per_report", "uat_cycles")
    @classmethod
    def _no_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Value must not be negative")
        return v


class ModuleEffort(BaseModel):
    """Effort breakdown for a single estimation module."""
    module_name: str
    base_effort_hours: float
    complexity_multiplier: float
    computed_effort_hours: float
    notes: str = ""
    # Backward-compat aliases so old templates still resolve
    @property
    def base_effort_days(self) -> float:
        return round(self.base_effort_hours / 8, 2)
    @property
    def computed_effort_days(self) -> float:
        return round(self.computed_effort_hours / 8, 2)


class EstimationOutput(BaseModel):
    """Calculated estimation output."""
    total_effort_hours: float          # sum of all buffered modules
    total_effort_days: float           # = total_effort_hours / 8
    base_effort_hours: float           # sum of 11 core modules (before TL/BA & buffer)
    tl_percentage: float = 0.0
    ba_percentage: float = 0.0
    tl_hours: float = 0.0
    ba_hours: float = 0.0
    buffer_percentage: float = 0.0
    total_buffer_percentage: float = 0.0
    module_breakdown: List[ModuleEffort]
    assumptions: List[str]
    confidence_level: str              # Low / Medium / High
    confidence_reason: str


class ProjectVersion(BaseModel):
    """A single versioned snapshot of estimation."""
    version_id: str
    version_number: int
    timestamp: datetime
    inputs: EstimationInput
    outputs: EstimationOutput


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    name: str
    client_name: str
    description: str = ""


class Project(BaseModel):
    """Full project representation."""
    id: str
    name: str
    client_name: str
    description: str
    created_by: str  # user id
    created_at: datetime
    updated_at: datetime
    versions: List[ProjectVersion] = []
