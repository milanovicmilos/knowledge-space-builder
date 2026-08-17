import json
import logging
import time
import hashlib
from rdflib import Graph, Literal, RDF, RDFS, Namespace, URIRef, BNode
from learning_space_generator.app.core.config import settings
from learning_space_generator.app.services.semantic_service import semantic_service
from learning_space_generator.app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

class OntologyService:
    def __init__(self):
        # Define SOTIS namespace
        self.SOTIS = Namespace("http://www.sotis-conference.org/ontology#")
        self.SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
        self.DCTERMS = Namespace("http://purl.org/dc/terms/")

    def _init_graph(self) -> Graph:
        g = Graph()
        g.bind("sotis", self.SOTIS)
        g.bind("rdfs", RDFS)
        g.bind("skos", self.SKOS)
        g.bind("dcterms", self.DCTERMS)

        g.add((self.SOTIS.LearningGoal, RDF.type, RDFS.Class))
        g.add((self.SOTIS.LearningGoal, RDFS.label, Literal("Learning Goal")))
        g.add((self.SOTIS.LearningObject, RDF.type, RDFS.Class))
        g.add((self.SOTIS.LearningObject, RDFS.label, Literal("Learning Object")))
        g.add((self.SOTIS.achievesGoal, RDF.type, RDF.Property))
        g.add((self.SOTIS.achievesGoal, RDFS.label, Literal("achieves goal")))
        g.add((self.SOTIS.hasPrerequisite, RDF.type, RDF.Property))
        g.add((self.SOTIS.hasPrerequisite, RDFS.label, Literal("has prerequisite")))
        g.add((self.SOTIS.mapsToConcept, RDF.type, RDF.Property))
        g.add((self.SOTIS.mapsToConcept, RDFS.label, Literal("maps to concept")))
        return g

    def _generate_concept_level_ontology(self, concept_mapping_file, implications_file, difficulties_file, output_path):
        logger.info("Concept-level ontology mode: using concept_to_items_mapping + implications directly.")

        with open(concept_mapping_file, 'r', encoding='utf-8') as f:
            concept_to_items = json.load(f)

        implications = []
        if implications_file.exists():
            with open(implications_file, 'r', encoding='utf-8') as f:
                implications = json.load(f)

        item_difficulties = {}
        if difficulties_file.exists():
            with open(difficulties_file, 'r', encoding='utf-8') as f:
                item_difficulties = json.load(f)

        g = self._init_graph()

        all_items = []
        for items in concept_to_items.values():
            all_items.extend(items)
        all_texts = semantic_service.extract_item_texts(all_items)

        concept_uri_map = {}
        for concept_name in sorted(concept_to_items.keys()):
            digest = hashlib.sha1(concept_name.encode("utf-8")).hexdigest()[:10]
            concept_uri = self.SOTIS[f"Concept_{digest}"]
            concept_uri_map[concept_name] = concept_uri

            items = concept_to_items.get(concept_name, [])
            g.add((concept_uri, RDF.type, self.SOTIS.Concept))
            g.add((concept_uri, RDF.type, self.SOTIS.LearningGoal))
            g.add((concept_uri, RDF.type, self.SKOS.Concept))
            g.add((concept_uri, RDFS.label, Literal(concept_name)))
            g.add((concept_uri, self.SKOS.prefLabel, Literal(concept_name)))
            g.add((concept_uri, self.DCTERMS.identifier, Literal(f"Concept_{digest}")))
            g.add((concept_uri, self.SOTIS.itemCount, Literal(len(items))))

            diffs = [item_difficulties.get(item) for item in items if item in item_difficulties]
            if diffs:
                avg_diff = sum(diffs) / len(diffs)
                g.add((concept_uri, self.SOTIS.avgDifficulty, Literal(avg_diff)))

            goal_desc = None
            for item in items:
                desc = all_texts.get(item, "")
                if desc:
                    goal_desc = desc[:240].replace('\n', ' ')
                    break
            if goal_desc:
                g.add((concept_uri, self.DCTERMS.description, Literal(goal_desc)))

            for item_code in items:
                item_uri = self.SOTIS[f"Item_{item_code}"]
                g.add((item_uri, RDF.type, self.SOTIS.Item))
                g.add((item_uri, RDF.type, self.SOTIS.LearningObject))
                g.add((item_uri, RDFS.label, Literal(item_code)))
                g.add((item_uri, self.DCTERMS.identifier, Literal(item_code)))
                g.add((item_uri, self.SOTIS.belongsTo, concept_uri))
                g.add((item_uri, self.SOTIS.achievesGoal, concept_uri))
                if item_code in item_difficulties:
                    g.add((item_uri, self.SOTIS.difficulty, Literal(item_difficulties[item_code])))
                desc = all_texts.get(item_code, "")
                if desc:
                    short_desc = desc[:200].replace('\n', ' ')
                    g.add((item_uri, RDFS.comment, Literal(short_desc)))
                    g.add((item_uri, self.SOTIS.fullText, Literal(desc)))

        edge_counts = {}
        for edge in implications:
            src = edge.get("source")
            dst = edge.get("target")
            if not src or not dst or src == dst:
                continue
            if src not in concept_uri_map or dst not in concept_uri_map:
                continue
            key = (src, dst)
            edge_counts[key] = edge_counts.get(key, 0) + 1

        for (src_name, dst_name), count in edge_counts.items():
            src_uri = concept_uri_map[src_name]
            dst_uri = concept_uri_map[dst_name]
            g.add((src_uri, self.SOTIS.prerequisiteOf, dst_uri))
            g.add((dst_uri, self.SOTIS.hasPrerequisite, src_uri))
            link_node = BNode()
            g.add((link_node, RDF.type, self.SOTIS.PrerequisiteLink))
            g.add((link_node, self.SOTIS.source, src_uri))
            g.add((link_node, self.SOTIS.target, dst_uri))
            g.add((link_node, self.SOTIS.evidenceCount, Literal(count)))

        g.serialize(destination=output_path, format="turtle")
        logger.info(f"Concept-level ontology exported to: {output_path}")
        
    def generate_ontology(self):
        logger.info("Starting Ontology Generation...")
        
        # 1. Load Data
        if not settings.OUTPUT_DIR.exists():
            logger.error("Output directory missing.")
            return

        clusters_file = settings.OUTPUT_DIR / "semantic_clusters.json"
        implications_file = settings.IMPLICATIONS_FILE
        difficulties_file = settings.OUTPUT_DIR / "item_difficulties.json"
        concept_mapping_file = settings.OUTPUT_DIR / "concept_to_items_mapping.json"
        
        if settings.USE_CONCEPT_LEVEL_IITA and concept_mapping_file.exists():
            self._generate_concept_level_ontology(
                concept_mapping_file=concept_mapping_file,
                implications_file=implications_file,
                difficulties_file=difficulties_file,
                output_path=settings.OUTPUT_DIR / "sotis_ontology.ttl"
            )
            return

        if not clusters_file.exists():
            logger.error(f"Clusters file missing at {clusters_file}. Run 'python -m app.main extract' first.")
            return
            
        if not implications_file.exists():
            logger.warning(f"Implications file missing at {implications_file}. Ontology won't have prerequisite links.")
            implications = {}
        else:
            with open(implications_file, 'r') as f:
                implications = json.load(f)

        with open(clusters_file, 'r') as f:
            clusters = json.load(f)

        item_difficulties = {}
        if difficulties_file.exists():
            with open(difficulties_file, 'r', encoding='utf-8') as f:
                item_difficulties = json.load(f)

        # 2. Initialize RDF Graph
        g = self._init_graph()
        
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
            g.add((cluster_uri, RDF.type, self.SOTIS.LearningGoal))
            g.add((cluster_uri, RDF.type, self.SKOS.Concept))
            g.add((cluster_uri, RDFS.label, Literal(cluster_name)))
            g.add((cluster_uri, self.SKOS.prefLabel, Literal(cluster_name)))
            g.add((cluster_uri, self.DCTERMS.identifier, Literal(f"Concept_{cluster_id}")))
            g.add((cluster_uri, self.SOTIS.itemCount, Literal(len(items))))

            goal_desc = None
            for text in cluster_texts_map.get(cluster_id, []):
                if text:
                    goal_desc = text[:240].replace('\n', ' ')
                    break
            if goal_desc:
                g.add((cluster_uri, self.DCTERMS.description, Literal(goal_desc)))

            # Compute concept difficulty as mean of item difficulties when available
            diffs = [item_difficulties.get(item) for item in items if item in item_difficulties]
            if diffs:
                avg_diff = sum(diffs) / len(diffs)
                g.add((cluster_uri, self.SOTIS.avgDifficulty, Literal(avg_diff)))
            
            for item_code in items:
                item_uri = self.SOTIS[f"Item_{item_code}"]
                g.add((item_uri, RDF.type, self.SOTIS.Item))
                g.add((item_uri, RDF.type, self.SOTIS.LearningObject))
                g.add((item_uri, RDFS.label, Literal(item_code)))
                g.add((item_uri, self.DCTERMS.identifier, Literal(item_code)))
                g.add((item_uri, self.SOTIS.belongsTo, cluster_uri))
                g.add((item_uri, self.SOTIS.achievesGoal, cluster_uri))

                if item_code in item_difficulties:
                    g.add((item_uri, self.SOTIS.difficulty, Literal(item_difficulties[item_code])))
                
                desc = all_texts.get(item_code, "")
                if desc:
                    short_desc = desc[:200].replace('\n', ' ')
                    g.add((item_uri, RDFS.comment, Literal(short_desc)))
                    g.add((item_uri, self.SOTIS.fullText, Literal(desc)))


        # 4. Lift Implications to Concept Level
        # (Prerequisite Learning Paths)
        if implications:
            logger.info("Building Concept Prerequisite Map (concept names → cluster goals)...")
            
            # Load concept-to-items mapping (if available)
            concept_to_items = {}
            if concept_mapping_file.exists():
                try:
                    with open(concept_mapping_file, 'r', encoding='utf-8') as f:
                        concept_to_items = json.load(f)
                    logger.info(f"Loaded {len(concept_to_items)} concept-to-items mappings")
                except Exception as e:
                    logger.warning(f"Failed to load concept mapping: {e}")
            
            # Build item-to-concept reverse map
            item_to_concept = {}
            for concept_name, items in concept_to_items.items():
                for item in items:
                    item_to_concept[item] = concept_name
            
            cluster_links = {}
            
            # Implications is a list of {"source": "concept_name", "target": "concept_name"}
            # Map concept names back to items, then to clusters
            for edge in implications:
                src_concept = edge.get("source")
                dst_concept = edge.get("target")
                
                if not src_concept or not dst_concept:
                    continue
                
                # Get items that belong to source concept
                src_items = concept_to_items.get(src_concept, [])
                if not src_items:
                    logger.debug(f"Source concept '{src_concept}' has no items, skipping edge")
                    continue
                
                # Map items to clusters
                src_clusters = set()
                for item in src_items:
                    if item in item_to_cluster:
                        src_clusters.add(item_to_cluster[item])
                
                if not src_clusters:
                    logger.debug(f"Source concept '{src_concept}' maps to no clusters, skipping edge")
                    continue
                
                # Get items that belong to target concept
                dst_items = concept_to_items.get(dst_concept, [])
                if not dst_items:
                    logger.debug(f"Target concept '{dst_concept}' has no items, skipping edge")
                    continue
                
                # Map items to clusters
                dst_clusters = set()
                for item in dst_items:
                    if item in item_to_cluster:
                        dst_clusters.add(item_to_cluster[item])
                
                if not dst_clusters:
                    logger.debug(f"Target concept '{dst_concept}' maps to no clusters, skipping edge")
                    continue
                
                # Create links between all source and target cluster pairs
                # SAFEGUARD: Skip self-loops to prevent cycles
                for src_cluster in src_clusters:
                    for dst_cluster in dst_clusters:
                        if src_cluster != dst_cluster:
                            link = (src_cluster, dst_cluster)
                            cluster_links[link] = cluster_links.get(link, 0) + 1
                            logger.debug(f"Link: Concept '{src_concept}' (cluster {src_cluster}) → Concept '{dst_concept}' (cluster {dst_cluster})")
            
            # Detect and remove cycles from cluster_links using DFS
            def detect_and_break_cycles(edges: dict) -> dict:
                """Remove backward edges that would create cycles"""
                if not edges:
                    return edges
                
                # Build adjacency list
                graph = {}
                for src, dst in edges:
                    if src not in graph:
                        graph[src] = set()
                    graph[src].add(dst)
                
                # DFS to find backward edges
                visited = set()
                rec_stack = set()
                broken = set()
                
                def dfs(node, parent_path):
                    visited.add(node)
                    rec_stack.add(node)
                    
                    for neighbor in graph.get(node, set()):
                        if neighbor in rec_stack:
                            # Cycle detected - mark backward edge for removal
                            broken.add((node, neighbor))
                            logger.warning(f"Cycle detected: {node} → {neighbor}, removing backward edge")
                        elif neighbor not in visited:
                            dfs(neighbor, parent_path | {node})
                    
                    rec_stack.remove(node)
                
                for cluster in graph:
                    if cluster not in visited:
                        dfs(cluster, set())
                
                # Return only non-broken edges
                return {edge: count for edge, count in edges.items() if edge not in broken}
            
            cluster_links = detect_and_break_cycles(cluster_links)
            
            # Add links with sufficient evidence
            # Since our graph is sparse, even 1 link is significant
            logger.info(f"Creating {len(cluster_links)} cluster prerequisite links (after cycle removal)...")
            for (src, dst), count in cluster_links.items():
                src_uri = self.SOTIS[f"Concept_{src}"]
                dst_uri = self.SOTIS[f"Concept_{dst}"]
                g.add((src_uri, self.SOTIS.prerequisiteOf, dst_uri))
                g.add((dst_uri, self.SOTIS.hasPrerequisite, src_uri))
                link_node = BNode()
                g.add((link_node, RDF.type, self.SOTIS.PrerequisiteLink))
                g.add((link_node, self.SOTIS.source, src_uri))
                g.add((link_node, self.SOTIS.target, dst_uri))
                g.add((link_node, self.SOTIS.evidenceCount, Literal(count)))
                logger.info(f"Added relation: Concept_{src} → Concept_{dst} (evidence: {count})")

        # 5. Serialize
        output_path = settings.OUTPUT_DIR / "sotis_ontology.ttl"
        g.serialize(destination=output_path, format="turtle")
        logger.info(f"Ontology successfully exported to: {output_path}")

ontology_service = OntologyService()
