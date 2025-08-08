# prometheus/genesis_engine/analyzers/stock/naming_analyzer.py

from typing import Optional, List
from prometheus.genesis_engine.analyzers.base import BaseAnalyzer, NodeContext, EvidenceChunk

class NamingConventionAnalyzer(BaseAnalyzer):
    """
    Analyzes entity names to find clues based on common ERP/database
    naming conventions, outputting concise tags.
    """
    @property
    def name(self) -> str:
        return "NamingConventions"

    def analyze(self, context: NodeContext) -> Optional[EvidenceChunk]:
        
        if context.node_type == "Table":
            tags = self._analyze_table_name(context.node_name)
        elif context.node_type == "Column":
            tags = self._analyze_column_name(context.node_name)
        else:
            return None

        if not tags:
            return None
            
        return EvidenceChunk(
            analyzer_name=self.name,
            content="\n".join([f"tag: {tag}" for tag in tags])
        )

    def _analyze_table_name(self, name: str) -> List[str]:
        tags: List[str] = []
        # Structural patterns
        if name.endswith(('_rel', '_rel_id')):
            tags.append('junction_table_suffix')
        if name.endswith(('_line', '_lines', '_item', '_items')):
            tags.append('detail_table_suffix')
        
        # System/Framework patterns
        if name.startswith('ir_'):
            tags.append('system_internal_prefix') # e.g., ir_model, ir_ui_view
        if name.startswith('res_'):
            tags.append('master_data_prefix') # e.g., res_partner, res_users
            
        # Customization patterns
        if name.startswith(('x_', 'x_studio_')):
            tags.append('custom_entity_prefix')
            
        return tags

    def _analyze_column_name(self, full_name: str) -> List[str]:
        tags: List[str] = []
        try:
            _, name = full_name.split('.', 1)
        except ValueError:
            return []

        # Exact matches (highest priority)
        if name == 'id':
            tags.append('primary_key_candidate')
        if name in ('create_uid', 'write_uid'):
            tags.append('audit_user')
        if name in ('create_date', 'write_date'):
            tags.append('audit_timestamp')
            
        # Suffix-based patterns
        if name.endswith('_id'):
            tags.append('foreign_key_single_suffix')
        if name.endswith('_ids'):
            tags.append('foreign_key_many_suffix')
            
        # Prefix-based patterns for booleans
        if name.startswith(('is_', 'has_', 'can_', 'allow_')):
            tags.append('boolean_flag_prefix')
            
        # Content-based patterns (lower priority)
        if any(term in name for term in ['amount', 'total', 'price', 'cost', 'value', 'revenue', 'balance']):
            tags.append('monetary_value_keyword')
        if any(term in name for term in ['qty', 'quantity', 'count', 'number']):
            tags.append('quantity_keyword')
        if any(term in name for term in ['date', 'due', '_at', '_on']):
            tags.append('date_time_keyword')
        if any(term in name for term in ['email', 'phone', 'mobile', 'fax', 'website', 'url']):
            tags.append('contact_info_keyword')

        # Remove duplicates and return
        return sorted(list(set(tags)))