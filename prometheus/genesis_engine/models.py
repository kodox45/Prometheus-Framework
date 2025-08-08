# prometheus/genesis_engine/models.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ColumnSchema(BaseModel):
    """Represents the schema of a single database column."""
    name: str
    data_type: str
    is_nullable: bool
    comment: str | None = None

class ForeignKeySchema(BaseModel):
    """Represents a single foreign key relationship."""
    constrained_columns: List[str]
    referred_schema: str
    referred_table: str
    referred_columns: List[str]
    on_update: str | None = None
    on_delete: str | None = None

class TableSchema(BaseModel):
    """Represents the complete schema of a single database table."""
    schema_name: str
    table_name: str
    columns: List[ColumnSchema]
    foreign_keys: List[ForeignKeySchema] = Field(default_factory=list)
    primary_key: List[str] = Field(default_factory=list)
    unique_constraints: List[Dict[str, Any]] = Field(default_factory=list)
    indexes: List[Dict[str, Any]] = Field(default_factory=list)
    is_junction_table: bool = False
    
    comment: str | None = None
    
class DatabaseSchema(BaseModel):
    """Represents the entire schema of the database."""
    tables: List[TableSchema] = Field(default_factory=list)

class CoreDescription(BaseModel):
    """
    Represents the core, machine-focused semantic description of an entity.
    """
    core_description: str = Field(..., description="A dense, factual description for vector embedding.")
    inferred_logic: Optional[str] = Field(None, description="Concise inferred business logic.")
    stereotype: str = Field(..., description="Entity classification: Master, Transaction, etc.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="LLM's confidence score.")

class ImplicitRelation(BaseModel):
    """
    Represents the structured analysis of a potential implicit relationship
    between two tables, as determined by an LLM.
    """
    relationship_exists: bool
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    # Jadikan relationship_type opsional, karena hanya ada jika relationship_exists=True
    relationship_type: Optional[str] = None
    justification: str