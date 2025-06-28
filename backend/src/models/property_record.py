"""
Data models for Charleston County property records
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

@dataclass
class PropertyRecord:
    """Represents a Charleston County property record"""
    tms_number: str
    owner_name: Optional[str] = None
    property_address: Optional[str] = None
    property_description: Optional[str] = None
    assessed_value: Optional[str] = None
    tax_year: Optional[str] = None
    search_date: datetime = None
    
    def __post_init__(self):
        if self.search_date is None:
            self.search_date = datetime.now()

@dataclass
class PropertyDocument:
    """Represents a downloaded property document"""
    tms_number: str
    document_type: str  # 'property_card', 'deed', etc.
    file_path: Path
    download_date: datetime = None
    file_size: Optional[int] = None
    
    def __post_init__(self):
        if self.download_date is None:
            self.download_date = datetime.now()
        
        if self.file_path.exists():
            self.file_size = self.file_path.stat().st_size
