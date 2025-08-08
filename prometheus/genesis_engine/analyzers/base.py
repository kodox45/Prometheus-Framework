# prometheus/genesis_engine/analyzers/base.py

from abc import ABC, abstractmethod
from typing import Optional, Any
from pydantic import BaseModel

# Model ini digunakan untuk membawa konteks tentang entitas yang sedang dianalisis.
# Orchestrator akan membuat objek ini dan memberikannya ke setiap analyzer.
class NodeContext(BaseModel):
    # Info dari KG
    node_type: str  # "Table" atau "Column"
    node_name: str  # Nama unik (e.g., res_users atau res_users.id)
    
    # Info tambahan yang relevan
    db_schema: Any  # Objek DatabaseSchema lengkap untuk referensi
    db_connector: Any # Objek konektor untuk query ke DB jika perlu
    kg_connector: Any # Objek Neo4jConnector

# Model ini adalah "output" standar dari setiap analyzer.
class EvidenceChunk(BaseModel):
    analyzer_name: str
    content: str

class BaseAnalyzer(ABC):
    """
    Kelas dasar abstrak untuk semua modul analyzer.
    Setiap analyzer bertugas memeriksa sebuah NodeContext dan menghasilkan
    sepotong bukti (EvidenceChunk) untuk LLM.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """Nama unik untuk analyzer ini, akan digunakan di EvidenceChunk."""
        pass

    @abstractmethod
    def analyze(self, context: NodeContext) -> Optional[EvidenceChunk]:
        """
        Metode utama yang akan dijalankan oleh Orchestrator.
        Jika analyzer ini relevan dan menemukan sesuatu yang berharga,
        ia akan mengembalikan sebuah EvidenceChunk. Jika tidak, ia mengembalikan None.
        """
        pass