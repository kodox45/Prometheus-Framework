# scripts/verify_vector_search.py

from prometheus.config.settings import settings
from prometheus.connectors.neo4j_connector import Neo4jConnector

def main():
    print("--- Verifying Native Vector Search (Separate Indexes) ---")
    
    with Neo4jConnector(settings) as neo4j_connector:
        
        print("\n[1/3] Fetching a sample vector from a Column node...")
        sample_column_vector = None
        with neo4j_connector.get_session() as session:
            result = session.run("MATCH (c:Column) WHERE c.embedding IS NOT NULL RETURN c.embedding AS vec, c.name as name LIMIT 1").single()
            if result:
                sample_column_vector = result['vec']
                sample_node_name = result['name']
                print(f"  - Sample vector fetched from '{sample_node_name}'.")
            else:
                print("  - ⚠️ No Column nodes with embeddings found. Run enrichment first.")
                return

        print("\n[2/3] Querying the 'column_embeddings' index...")
        if sample_column_vector:
            query = """
            CALL db.index.vector.queryNodes('column_embeddings', 5, $query_vector)
            YIELD node, score
            RETURN node.name AS similar_node, score
            """
            with neo4j_connector.get_session() as session:
                results = session.run(query, query_vector=sample_column_vector).data()
                print("  - Column vector search successful! Top 5 similar columns:")
                for record in results:
                    print(f"    - Node: {record['similar_node']} (Score: {record['score']:.4f})")
                
                if results and results[0]['similar_node'] == sample_node_name:
                    print("\n✅ Verification successful for column index.")
                else:
                    print("\n❌ Verification failed for column index.")
        
        print("\n[3/3] Verifying that both indexes exist...")
        with neo4j_connector.get_session() as session:
            indexes = session.run("SHOW INDEXES YIELD name, type WHERE type = 'VECTOR' RETURN name").data()
            index_names = {idx['name'] for idx in indexes}
            if 'table_embeddings' in index_names and 'column_embeddings' in index_names:
                print("  - Both 'table_embeddings' and 'column_embeddings' indexes exist.")
                print("\n🎉 --- Full Vector Search Functionality Verified! --- 🎉")
            else:
                print(f"  - ❌ Missing vector indexes. Found: {index_names}")

if __name__ == "__main__":
    main()