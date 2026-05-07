from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FileMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")
    project: str = ""
    company: str = ""
    phase: str = ""
    category: str = ""
    subcategory: str = ""


class ProjectMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")
    project_name: str = ""
    project_year: str = ""
    construction_unit: str = ""
    approval_info: str = ""


class CompanyMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company_name: str = ""
    uscc: str = ""
    address: str = ""
    contact: str = ""


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    file: FileMeta = Field(default_factory=FileMeta)
    project: ProjectMeta = Field(default_factory=ProjectMeta)
    company: CompanyMeta = Field(default_factory=CompanyMeta)
