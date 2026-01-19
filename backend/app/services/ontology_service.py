import json
import logging
import time
from rdflib import Graph, Literal, RDF, RDFS, Namespace, URIRef
from app.config import settings
from app.services.semantic_service import semantic_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

class OntologyService:
    def __init__(self):
        # Define SOTIS namespace
        self.SOTIS = Namespace("http://www.sotis-conference.org/ontology#")
        
    def generate_ontology(self, clusters_file=None, implications_file=None, output_file=None):
        logger.info("Starting Ontology Generation...")
        
        # 1. Load Data
        if clusters_file:
            from pathlib import Path
            cluster_path = Path(clusters_file)
        else:
            cluster_path = settings.OUTPUT_DIR / "semantic_clusters.json"
            
        if implications_file:
            from pathlib import Path
            imp_path = Path(implications_file)
        else:
            imp_path = settings.IMPLICATIONS_FILE
        
        if not cluster_path.exists():
            logger.error(f"Clusters file missing at {cluster_path}. Run semantic clustering first.")
            return

        # Check implications
        if not imp_path.exists():
            logger.warning(f"Implications file missing at {imp_path}. Ontology won't have prerequisite links.")
            implications = {} # Should be [] actually if it's a list. Let's check type below.
        else:
            with open(imp_path, 'r') as f:
                implications = json.load(f)

        with open(cluster_path, 'r') as f:
            clusters = json.load(f)

        # 2. Initialize RDF Graph
        g = Graph()
        g.bind("sotis", self.SOTIS)
        g.bind("rdfs", RDFS)
        
        # 3. Process Clusters and Name them (BATCHED)
        item_to_cluster = {}
        all_items = []
        for items in clusters.values():
            all_items.extend(items)
            
        logger.info("Pre-fetching item texts for context...")
        all_texts = semantic_service.extract_item_texts(all_items)
        
        # Prepare Data for Batch Processing
        cluster_texts_map = {}
        for cluster_id, items in clusters.items():
            for item in items:
                item_to_cluster[item] = cluster_id
            
            # Gather texts
            texts = [all_texts.get(i,"") for i in items if len(all_texts.get(i,"")) > 20]
            cluster_texts_map[cluster_id] = texts

        # Process in configurable batches
        cluster_ids = list(clusters.keys())
        batch_size = getattr(settings, 'LLM_BATCH_SIZE', 5)
        cluster_names = {}
        
        for i in range(0, len(cluster_ids), batch_size):
            batch_ids = cluster_ids[i : i+batch_size]
            logger.info(f"Processing Batch {i//batch_size + 1}: {batch_ids}")
            
            # Prepare batch input
            batch_input = {cid: cluster_texts_map.get(cid, []) for cid in batch_ids}
            
            # Call LLM (batch); results will be cached inside the service
            batch_results = llm_service.name_clusters_batch(batch_input)
            cluster_names.update(batch_results)
            
            # Rate limit pause between batches (configurable)
            time.sleep(getattr(settings, 'LLM_BATCH_PAUSE', 2))

        # Add to Graph
        for cluster_id, items in clusters.items():
            cluster_name = cluster_names.get(cluster_id, f"Oblast_{cluster_id}")
            logger.info(f"Cluster {cluster_id} -> {cluster_name}")
            
            cluster_uri = self.SOTIS[f"Concept_{cluster_id}"]
            g.add((cluster_uri, RDF.type, self.SOTIS.Concept))
            g.add((cluster_uri, RDFS.label, Literal(cluster_name)))
            
            for item_code in items:
                item_uri = self.SOTIS[f"Item_{item_code}"]
                g.add((item_uri, RDF.type, self.SOTIS.Item))
                g.add((item_uri, RDFS.label, Literal(item_code)))
                g.add((item_uri, self.SOTIS.belongsTo, cluster_uri))
                
                desc = all_texts.get(item_code, "")
                if desc:
                    g.add((item_uri, RDFS.comment, Literal(desc[:150].replace('\n', ' '))))


        # 4. Lift Implications to Concept Level
        # (Prerequisite Learning Paths)
        if implications:
            logger.info("Building Concept Prerequisite Map...")
            cluster_links = {}
            
            # Implications is a list of {"source": "...", "target": "..."}
            for edge in implications:
                src_item = edge.get("source")
                dst_item = edge.get("target")
                
                if not src_item or not dst_item: continue
                if src_item not in item_to_cluster: continue
                
                src_cluster = item_to_cluster[src_item]
                
                if dst_item not in item_to_cluster: continue
                dst_cluster = item_to_cluster[dst_item]
                
                if src_cluster != dst_cluster:
                    link = (src_cluster, dst_cluster)
                    cluster_links[link] = cluster_links.get(link, 0) + 1
            
            # Add links with sufficient evidence
            # Since our graph is sparse (27 edges), even 1 link is significant
            for (src, dst), count in cluster_links.items():
                src_uri = self.SOTIS[f"Concept_{src}"]
                dst_uri = self.SOTIS[f"Concept_{dst}"]
                g.add((src_uri, self.SOTIS.prerequisiteOf, dst_uri))
                logger.info(f"Added relation: {src} -> {dst} (weight: {count})")

        # 5. Serialize
        if output_file:
            output_path = Path(output_file)
        else:
            output_path = settings.OUTPUT_DIR / "sotis_ontology.ttl"
            
        g.serialize(destination=output_path, format="turtle")
        logger.info(f"Ontology successfully exported to: {output_path}")

ontology_service = OntologyService()
