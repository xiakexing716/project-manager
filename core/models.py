
# core/models.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class Project:
    id: Optional[int] = None
    project_name: str = ""
    lead_programmer: str = ""
    task_stage: str = ""
    start_date: str = ""
    end_date: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class DatasetRow:
    id: Optional[int] = None
    project_id: Optional[int] = None
    lot_file_id: Optional[int] = None
    required: str = ""
    dataset_label: str = ""
    program_name: str = ""
    output_name: str = ""
    programmer: str = ""
    output_date: str = ""
    status: str = ""
    qc_programmer: str = ""
    qc_program_name: str = ""
    qc_completion_date: str = ""
    qc_status: str = ""
    comments: str = ""
    derived_type: str = ""


@dataclass
class TflRow:
    id: Optional[int] = None
    project_id: Optional[int] = None
    lot_file_id: Optional[int] = None
    required: str = ""
    output_type: str = ""
    tfl_category: str = ""
    output_number: str = ""
    title: str = ""
    repeated: str = ""
    txtname: str = ""
    rtfname: str = ""
    macro: str = ""
    programmer: str = ""
    output_date: str = ""
    status: str = ""
    qc_programmer: str = ""
    qc_program_name: str = ""
    qc_completion_date: str = ""
    qc_status: str = ""
    comments: str = ""