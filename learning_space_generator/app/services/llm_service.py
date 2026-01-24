import logging
import json
import re
import hashlib
from openai import OpenAI
from learning_space_generator.app.core.config import settings
from pathlib import Path
import time
import math

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = settings.GITHUB_TOKEN
        self.base_url = settings.GITHUB_API_URL
        self.client = None
        self.model = settings.LLM_MODEL
        # alternatives is a comma-separated string in settings
        self.alternatives = [m.strip() for m in settings.LLM_ALTERNATIVES.split(",") if m.strip()]
        self.batch_size = settings.LLM_BATCH_SIZE
        self.batch_pause = settings.LLM_BATCH_PAUSE
        # cache path
        self.cache_path = Path(settings.OUTPUT_DIR) / settings.LLM_CACHE_FILE
        self.cache = {}
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
        
        if self.api_key:
            try:
                self.client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                )
                logger.info(f"LLM Service initialized with GitHub Models - model: {settings.LLM_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        else:
            logger.warning("GITHUB_TOKEN not found. LLM features will be disabled.")

    def name_clusters_batch(self, clusters_data: dict[str, list[str]]) -> dict[str, str]:
        """
        Batches multiple clusters into one prompt to save API calls.
        clusters_data: { 'cluster_id': ['text1', 'text2', ...] }
        """
        # Helper utilities
        def make_snippet(texts):
            return " | ".join([t[:200].replace("\n", " ") for t in texts[:2]])

        def cache_key_for(cid, texts):
            payload = cid + "|" + "|".join([t[:100].replace("\n", " ") for t in texts[:2]])
            return hashlib.sha1(payload.encode("utf-8")).hexdigest()

        # Annotate clusters with snippet and cache key
        annotated = {}
        for cid, texts in clusters_data.items():
            annotated[cid] = {"texts": texts, "snippet": make_snippet(texts), "key": cache_key_for(cid, texts)}

        # If no client, return placeholders but check existing cache (support old keys and new hashed keys)
        result_map = {}
        if not self.client:
            for cid, v in annotated.items():
                key = v["key"]
                if cid in self.cache:
                    result_map[cid] = self.cache[cid]
                elif key in self.cache:
                    result_map[cid] = self.cache[key]
                else:
                    result_map[cid] = f"Oblast_{cid}"
            return result_map

        # Prepare to-request list (only those not cached under either key or legacy cid)
        to_request = {cid: v for cid, v in annotated.items() if (cid not in self.cache and v["key"] not in self.cache)}
        # Fill results from cache
        for cid, v in annotated.items():
            key = v["key"]
            if cid in self.cache:
                result_map[cid] = self.cache[cid]
            elif key in self.cache:
                result_map[cid] = self.cache[key]

        if not to_request:
            return result_map

        # Build prompt function
        def build_prompt(items):
            p = (
                "Du bist ein Mathematik-Experte. Analysiere die folgenden Gruppen von Aufgaben (Cluster) und ordne "
                "jede Gruppe einen prägnanten Titel eines mathematischen Themengebiets zu (3-6 Worte) auf DEUTSCH.\n"
                "Antworte AUSSCHLIESSLICH mit einem gültigen JSON-Objekt, wobei die Schlüssel Cluster-IDs und die Werte Themennamen sind.\n"
                'Beispiel JSON: {"6": "Lineare Funktionen", "7": "Gleichungen lösen"}\n\n'
            )
            for cid, v in items.items():
                p += f"--- Cluster ID: {cid} ---\nAufgaben: {v['snippet']}\n\n"
            p += "JSON Response:"
            return p

        # Process in chunks to respect batch size
        chunk_keys = list(to_request.keys())
        last_error = None
        for start in range(0, len(chunk_keys), self.batch_size):
            chunk_ids = chunk_keys[start:start + self.batch_size]
            chunk_items = {cid: to_request[cid] for cid in chunk_ids}
            prompt = build_prompt(chunk_items)

            models_to_try = [self.model] + [m for m in self.alternatives if m != self.model]
            chunk_success = False
            for model in models_to_try:
                try:
                    logger.info(f"LLM Batch Naming for Clusters: {chunk_ids} with model {model}...")
                    completion = self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                        max_tokens=500,
                    )
                    response_text = completion.choices[0].message.content.strip()

                    # Cleanup possible fences
                    if "```json" in response_text:
                        response_text = response_text.split("```json")[1].split("```")[0].strip()
                    elif response_text.count("```") >= 2:
                        response_text = response_text.split("```")[1].strip()

                    try:
                        names_map = json.loads(response_text)
                    except json.JSONDecodeError:
                        try:
                            s = response_text.find('{')
                            e = response_text.rfind('}')
                            names_map = json.loads(response_text[s:e+1])
                        except Exception:
                            raise

                    # Ensure placeholders for missing
                    for cid in chunk_ids:
                        if cid not in names_map or not names_map[cid]:
                            names_map[cid] = f"Oblast_{cid}_(Missing)"

                    # Save into cache (by key) and result_map
                    for cid, name in names_map.items():
                        key = annotated[cid]["key"]
                        self.cache[key] = name
                        result_map[cid] = name

                    chunk_success = True
                    break

                except Exception as e:
                    last_error = e
                    msg = str(e)
                    logger.warning(f"Model {model} failed: {e}. Trying next model if available.")
                    if "429" in msg or "Rate limit" in msg:
                        logger.warning("Rate limit encountered; aborting further model attempts for this chunk.")
                        break
                    time.sleep(min(10, 2 * (1 + math.log(len(models_to_try)+1))))

            if not chunk_success:
                logger.info("Applying heuristic fallback naming for chunk: %s", chunk_ids)
                for cid in chunk_ids:
                    texts = annotated[cid]["texts"]
                    name = self._heuristic_name(texts, cid)
                    key = annotated[cid]["key"]
                    self.cache[key] = name
                    result_map[cid] = name

            # persist cache after each chunk
            try:
                settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                with open(self.cache_path, 'w', encoding='utf-8') as f:
                    json.dump(self.cache, f, ensure_ascii=False, indent=2)
            except Exception:
                logger.warning("Failed to write LLM cache file.")

            time.sleep(self.batch_pause)

        if last_error:
            logger.error(f"Some errors occurred during batch naming: {last_error}")

        return result_map
    
    def _heuristic_name(self, texts: list[str], cid: str) -> str:
        """Simple fallback: extract top terms from snippets."""
        stopwords = set([
            # English
            "the","and","is","to","a","of",
            # Serbian/Croatian/Bosnian
            "u","na","za","koji","kako","se","je","su","ili","zadataka","zadaci",
            # German
            "der","die","das","ein","eine","und","ist","zu","mit","auf","für","von",
            "nicht","im","in","dem","den","es","sie","er","am","an","bei","aus","sich",
            "wenn","man","haben","werden","wir","ihr","ihre","sein","was","wie","warum",
            "dass","dies","diese","dieser","auch","oder","als","noch","schon","nur",
        ])
        words = {}
        for t in texts[:3]:
            for w in re.findall(r"[A-Za-zÀ-žđĐČčĆćŠšŽž]+", t.lower()):
                if len(w) < 3:
                    continue
                if w in stopwords:
                    continue
                words[w] = words.get(w, 0) + 1

        if not words:
            return f"Oblast_{cid}"

        sorted_words = sorted(words.items(), key=lambda x: (-x[1], x[0]))
        top = [w for w,_ in sorted_words[:3]]
        name = " ".join([w.capitalize() for w in top])
        return name

    def name_cluster(self, cluster_id: str, item_texts: list[str]) -> str:
        # Legacy single call - redirect to batch
        res = self.name_clusters_batch({cluster_id: item_texts})
        return res.get(cluster_id, f"Oblast_{cluster_id}")



    def classify_items_batch(self, items_dict: dict[str, str], batch_size: int = 5, use_cache: bool = True) -> dict[str, str]:
        """
        Classify math items into semantic domains/areas using LLM.
        items_dict: {item_id: item_text_snippet}
        use_cache: If True, load existing classifications from file
        Returns: {item_id: domain_name}
        """
        if not self.client:
            logger.warning("LLM client not available; returning unclassified.")
            return {item: "Unclassified" for item in items_dict}
        
        # Load existing classifications from cache file
        cache_file = settings.OUTPUT_DIR / "llm_item_classifications.json"
        cached_classifications = {}
        if use_cache and cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_classifications = json.load(f)
                logger.info(f"📂 Loaded {len(cached_classifications)} cached item classifications")
            except Exception as e:
                logger.warning(f"Failed to load cached classifications: {e}")
        
        # Filter out already classified items
        items_to_classify = {k: v for k, v in items_dict.items() if k not in cached_classifications}
        result = dict(cached_classifications)  # Start with cached results
        
        if not items_to_classify:
            logger.info("✅ All items already classified (100% cache hit).")
            return result
        
        logger.info(f"🔍 Classifying {len(items_to_classify)}/{len(items_dict)} items ({len(cached_classifications)} from cache)...")
        item_ids = list(items_to_classify.keys())
        
        for start in range(0, len(item_ids), batch_size):
            batch_ids = item_ids[start:start + batch_size]
            batch_items = {iid: items_to_classify[iid] for iid in batch_ids}
            
            # Build prompt
            prompt = (
                "Du bist ein Mathematik-Experte. Analysiere die folgenden mathematischen Aufgaben und "
                "ordne jede einem mathematischen Themengebiet zu.\n"
                "Antworte NUR mit gültigem JSON, keine Erklärung.\n\n"
            )
            
            for iid, text in batch_items.items():
                snippet = text[:1000].replace("\n", " ")
                prompt += f"Aufgabe {iid}:\n{snippet}\n\n"
            
            prompt += 'JSON Format: {"item_id": "Themengebiet", ...}'
            
            # Try LLM
            models_to_try = [self.model] + [m for m in self.alternatives if m != self.model]
            success = False
            for model in models_to_try:
                try:
                    logger.info(f"Classifying batch {batch_ids[:3]}... with model {model}")
                    completion = self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                        max_tokens=2000,
                    )
                    response_text = completion.choices[0].message.content.strip()
                    
                    # Parse JSON flexibly
                    if "```json" in response_text:
                        response_text = response_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in response_text:
                        parts = response_text.split("```")
                        response_text = parts[1] if len(parts) > 1 else response_text
                    
                    try:
                        classifications = json.loads(response_text)
                    except json.JSONDecodeError:
                        s = response_text.find('{')
                        e = response_text.rfind('}')
                        if s >= 0 and e > s:
                            classifications = json.loads(response_text[s:e+1])
                        else:
                            raise
                    
                    for iid in batch_ids:
                        if iid in classifications and classifications[iid]:
                            result[iid] = classifications[iid]
                        else:
                            result[iid] = "Unclassified"
                    
                    success = True
                    break
                    
                except Exception as e:
                    msg = str(e)
                    logger.warning(f"Model {model} failed: {e}")
                    if "429" in msg or "Rate limit" in msg:
                        logger.warning("Rate limit; aborting further attempts.")
                        break
                    time.sleep(2)
            
            if not success:
                logger.warning(f"Classification failed for batch {batch_ids}.")
                for iid in batch_ids:
                    result[iid] = "Unclassified"
            
            time.sleep(self.batch_pause)
        
        # Save updated classifications back to cache file
        try:
            settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Saved {len(result)} item classifications to cache")
        except Exception as e:
            logger.warning(f"Failed to save classifications cache: {e}")
        
        return result

llm_service = LLMService()
