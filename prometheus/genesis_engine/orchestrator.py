# prometheus/genesis_engine/orchestrator.py

import random
import pprint
from typing import List, Optional

# Import konektor dan komponen inti
from prometheus.connectors.postgres_connector import PostgresConnector
from prometheus.connectors.neo4j_connector import Neo4jConnector
from .extractor import SchemaExtractor
from .loader import SchemaLoader
from .core.description_synthesizer import DescriptionSynthesizer
from .core.embedding_generator import EmbeddingGenerator
from .core.cost_calculator import EnrichmentCostCalculator, RelationCostCalculator
from .core.implicit_relation_finder import ImplicitRelationFinder

# Import model data dan Analyzer base
from .models import DatabaseSchema, CoreDescription
from .analyzers.base import BaseAnalyzer, NodeContext, EvidenceChunk

# Impor semua Stock Analyzer
from .analyzers.stock.schema_analyzer import SchemaDetailAnalyzer
from .analyzers.stock.naming_analyzer import NamingConventionAnalyzer
from .analyzers.stock.graph_analyzer import KnowledgeGraphAnalyzer
from .analyzers.stock.data_profilers import SmartDataProfilerAnalyzer


class Orchestrator:
    """
    Manages the entire Genesis Engine workflow:
    Extract -> Load Scaffold -> Enrich -> Discover Relations.
    Acts as the "factory foreman" for the entire process.
    """
    def __init__(self, pg_connector: PostgresConnector, neo4j_connector: Neo4jConnector):
        """
        Initializes the Orchestrator with all necessary components.
        """
        self.pg_connector = pg_connector
        self.neo4j_connector = neo4j_connector
        
        # Initialize core components
        self.extractor = SchemaExtractor(pg_connector)
        self.loader = SchemaLoader(neo4j_connector)
        self.synthesizer = DescriptionSynthesizer()
        self.embedding_generator = EmbeddingGenerator()
        self.enrichment_cost_calculator = EnrichmentCostCalculator()
        self.relation_finder = ImplicitRelationFinder(
            neo4j_connector=self.neo4j_connector, 
            relation_creation_fn=self.loader.create_implicit_relation
        )
        # List to hold all analyzers to be used
        self._analyzers: List[BaseAnalyzer] = []
        
        # Automatically load all stock analyzers on initialization
        self._load_stock_analyzers()

    def _load_stock_analyzers(self):
        """Registers the framework's built-in analyzers."""
        print("Loading stock analyzers...")
        self.register_analyzer(SchemaDetailAnalyzer())
        self.register_analyzer(NamingConventionAnalyzer())
        self.register_analyzer(KnowledgeGraphAnalyzer(self.neo4j_connector))
        self.register_analyzer(SmartDataProfilerAnalyzer())

    def register_analyzer(self, analyzer: BaseAnalyzer):
        """
        Supports registration of custom analyzers, allowing for extensibility.
        """
        print(f"  - Registering analyzer: {analyzer.name}")
        self._analyzers.append(analyzer)

    def run_genesis(self, sample_size: Optional[int] = None, clean_db: bool = True, force_rerun_enrichment: bool = False):
        """
        Executes the full, end-to-end Genesis Engine workflow.
        """
        print("\n--- Running Full Genesis Engine Workflow ---")
        
        try:
            with self.pg_connector, self.neo4j_connector:
                # --- PHASE 1: SCHEMA EXTRACTION & SCAFFOLDING ---
                print("\n[PHASE 1/3] Extracting Schema & Loading Structural Scaffold...")
                db_schema = self.extractor.extract_schema(schema_name="public")
                self.loader.load_schema(db_schema, clean_db=clean_db)
                print("✅ Structural scaffold loaded successfully.")

                # --- PHASE 2: NODE ENRICHMENT ---
                print("\n[PHASE 2/3] Preparing for Node Enrichment...")
                all_entities = self._get_all_entities(db_schema)
                is_forced = force_rerun_enrichment if not clean_db else True
                
                entities_to_process = self._get_entities_to_enrich(all_entities, force_rerun=is_forced)
                if sample_size:
                    random.seed(42)
                    entities_to_process = random.sample(entities_to_process, min(sample_size, len(entities_to_process)))
                    print(f"  - Applying sample size. Will process {len(entities_to_process)} randomly selected entities.")

                if not entities_to_process:
                    print("✅ All target entities are already enriched. Skipping enrichment phase.")
                else:
                    if not self._confirm_enrichment_cost(entities_to_process, db_schema):
                        print("🛑 Genesis Engine stopped by user before enrichment phase. Exiting.")
                        return

                    enriched_count = self._execute_enrichment_phase(entities_to_process, db_schema)
                    print(f"✅ Enrichment phase complete. {enriched_count} entities were successfully enriched.")
                    
                # --- PHASE 3: RELATION DISCOVERY & FINALIZATION ---
                print("\n[PHASE 3/3] Finalizing Knowledge Graph...")
                print("  - Creating Vector Indexes for relation discovery...")
                self.loader.create_vector_index()

                print("  - Discovering Implicit Relations...")
                self.relation_finder.find_and_create_relations()
                
                print("\n--- FINAL COST REPORTS ---")
                print(self.relation_finder.cost_calculator.generate_report())
                
                print("\n🎉 --- Genesis Engine Finished Successfully! --- 🎉")

        except Exception as e:
            print(f"\n💥 A critical error occurred and stopped the Genesis Engine: {e}")
            # Consider adding more detailed logging here in a real application
            import traceback
            traceback.print_exc()

    def _get_all_entities(self, db_schema: DatabaseSchema) -> List[tuple]:
        """Collects all table and column entities from the schema."""
        all_entities = []
        for table in db_schema.tables:
            all_entities.append(("Table", table.table_name))
            for column in table.columns:
                all_entities.append(("Column", f"{table.table_name}.{column.name}"))
        return all_entities

    def _confirm_enrichment_cost(self, entities_to_process: List[tuple], db_schema: DatabaseSchema) -> bool:
        """Gathers evidence, calculates cost, and asks for user confirmation."""
        print("  - Collecting evidence to estimate cost...")
        evidence_map = {}
        for entity_type, entity_name in entities_to_process:
            context = self._create_node_context(entity_type, entity_name, db_schema)
            evidence_map[entity_name] = [
                ev for analyzer in self._analyzers 
                if (ev := analyzer.analyze(context)) is not None
            ]
        
        print("  - Calculating estimated cost for LLM synthesis...")
        cost_report = self.enrichment_cost_calculator.estimate_cost(entities_to_process, evidence_map)
        print("\n--- Enrichment Cost Estimation ---")
        pprint.pprint(cost_report)
        
        import os
        auto_confirm = os.getenv("PROMETHEUS_AUTO_CONFIRM", "false").lower() == "true"
        if auto_confirm:
            print("  - Auto-confirm enabled via PROMETHEUS_AUTO_CONFIRM. Proceeding without prompt.")
            return True
        proceed = input("\n> Do you want to proceed with enrichment? (yes/no): ").lower().strip()
        return proceed == 'yes'

    def _execute_enrichment_phase(self, entities_to_process: List[tuple], db_schema: DatabaseSchema) -> int:
        """Iterates through entities and enriches them one by one."""
        successful_enrichments = 0
        total_count = len(entities_to_process)
        
        for i, (entity_type, entity_name) in enumerate(entities_to_process):
            print(f"\n--- Processing entity {i+1}/{total_count}: {entity_name} ---")
            
            context = self._create_node_context(entity_type, entity_name, db_schema)
            evidence_dossier = [ev for analyzer in self._analyzers if (ev := analyzer.analyze(context))]
            
            if not evidence_dossier:
                print("  - No evidence collected. Skipping enrichment.")
                continue

            print(f"  - Found {len(evidence_dossier)} pieces of evidence.")
            
            # --- Robust Enrichment Workflow for a Single Entity ---
            core_desc = self.synthesizer.synthesize(entity_type, entity_name, evidence_dossier)
            if not core_desc:
                print(f"  - 🛑 Synthesis failed for {entity_name}. Aborting enrichment for this node.")
                continue

            embedding_vector = self.embedding_generator.generate(core_desc.core_description)
            if not embedding_vector:
                print(f"  - 🛑 Embedding generation failed for {entity_name}. Aborting enrichment for this node.")
                continue
            
            self.loader.update_node_enrichment(
                node_type=entity_type, node_name=entity_name,
                description=core_desc, embedding=embedding_vector
            )
            print("  - ✅ Successfully enriched and saved to Knowledge Graph.")
            successful_enrichments += 1
            
        return successful_enrichments

    def _create_node_context(self, entity_type: str, entity_name: str, db_schema: DatabaseSchema) -> NodeContext:
        """Helper to create a NodeContext object."""
        return NodeContext(
            node_type=entity_type,
            node_name=entity_name,
            db_schema=db_schema,
            db_connector=self.pg_connector,
            kg_connector=self.neo4j_connector
        )
    
    def _get_entities_to_enrich(self, all_entities_from_db: List[tuple], force_rerun: bool = False) -> List[tuple]:
        """
        Determines which entities require enrichment.
        By default, it only processes entities that have not been enriched yet.

        Args:
            all_entities_from_db: A list of all (type, name) tuples from the source DB.
            force_rerun: If True, all entities will be returned for re-enrichment.

        Returns:
            A list of (type, name) tuples for entities that need processing.
        """
        if force_rerun:
            print("  - ⚠️ Force re-run enabled. All entities will be targeted for enrichment.")
            return all_entities_from_db

        print("  - Identifying entities that require enrichment (new or not yet enriched)...")
        # Dapatkan daftar nama semua node yang SUDAH diperkaya dari KG
        query = "MATCH (n) WHERE n.is_enriched = true RETURN n.name AS name"
        try:
            with self.neo4j_connector.get_session() as session:
                enriched_node_names = {res['name'] for res in session.run(query).data()}
        except Exception as e:
            print(f"  - ⚠️ Could not query for enriched nodes, proceeding with all entities. Error: {e}")
            return all_entities_from_db

        # Filter daftar entitas dari DB, hanya ambil yang namanya TIDAK ADA di daftar yang sudah diperkaya
        entities_to_process = [
            (entity_type, entity_name) 
            for entity_type, entity_name in all_entities_from_db
            if entity_name not in enriched_node_names
        ]
        
        print(f"  - Found {len(entities_to_process)} entities to enrich out of {len(all_entities_from_db)} total.")
        return entities_to_process