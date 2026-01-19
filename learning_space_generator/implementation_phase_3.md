# Implementation Phase 3: Semantic Enrichment & Ontology Export

## Ciljevi Faze 3
Ova faza ima za cilj povezivanje **Knowledge Space Theory (KST)** rezultata sa **Semantičkim vebom**, čime se zadovoljavaju zahtevi za SOTIS konferenciju.

Glavni zadaci:
1.  **LLM Enrichment**: Automatsko imenovanje klastera (oblasti) korišćenjem besplatnog LLM-a preko OpenRouter API-ja.
2.  **Ontology Generation**: Kreiranje RDF grafova (Ontologije) koji povezuju zadatke, veštine i preduslove.
3.  **Scientific Validation**: Generisanje finalnog izveštaja o validnosti strukture.

---

## 1. LLM Integracija (OpenRouter API)

Koristićemo LLM da "pročita" tekstove zadataka unutar svakog klastera i generiše ljudski čitljiv naziv oblasti (npr. "Razlomci", "Geometrija").

### Izbor Modela (OpenRouter Free Tier)
Preporučeni besplatni modeli (prema trenutnom stanju OpenRouter-a):
1.  **`google/gemini-exp-1206:free` (ili 2.0 Flash)** - Najpametniji besplatni model, odličan kontekst.
2.  **`meta-llama/llama-3-8b-instruct:free`** - Brz, dobar za jednostavne sumizacije.
3.  **`deepseek/deepseek-r1`** (ukoliko je dostupan free) - Odličan za rezonovanje.

*Konfiguracija će biti fleksibilna da podrži bilo koji model menjanjem samo `config.py`.*

### Tehnička Implementacija (`app/services/llm_service.py`)
- **Input**: Lista tekstova zadataka iz jednog klastera (izvađenih iz PDF-a).
- **Prompt**: "Analiziraj ove matematičke zadatke i daj mi kratak naziv (3-4 reči) matematičke oblasti kojoj pripadaju."
- **Output**: Ime klastera (npr. "Sabiranje razlomaka").
- **Biblioteka**: `openai` (OpenRouter je kompatibilan sa OpenAI SDK-om) ili `requests`.

> **Status**: Čeka se API Key od korisnika.

---

## 2. Ontology Export (RDF/Turtle)

Konverzija naših JSON rezultata u standardni format Semantičkog veba.

### Schema Ontologije
Definisaćemo jednostavnu ontologiju:
- **Classes**:
    - `sotis:Item` (Matematički zadatak)
    - `sotis:Concept` (Oblast/Klaster koju je LLM imenovao)
- **Properties**:
    - `sotis:belongsTo` (Item -> Concept)
    - `sotis:prerequisiteOf` (Concept -> Concept) - izvedeno iz IITA implikacija.

### Tehnička Implementacija (`app/services/ontology_service.py`)
- Koristićemo Python biblioteku **`rdflib`**.
- Funkcija `export_to_turtle()` će generisati fajl `knowledge_ontology.ttl`.

### Primer izlaza (.ttl):
```turtle
@prefix sotis: <http://www.sotis-conference.org/ontology#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

sotis:Cluster_6 a sotis:Concept ;
    rdfs:label "Osnovna Geometrija" .

sotis:Item_s1m11a091 a sotis:Item ;
    sotis:belongsTo sotis:Cluster_6 ;
    rdfs:label "Izračunavanje uglova trougla..." .

sotis:Cluster_6 sotis:prerequisiteOf sotis:Cluster_12 .
```

---

## 3. Workflow Implementacije

1.  **Priprema**:
    - Instalacija `rdflib` i `openai`.
    - Ažuriranje `app/core/config.py` sa poljima za `OPENROUTER_API_KEY` i `LLM_MODEL`.

2.  **Korak 1: LLM Service**:
    - Implementacija servisa koji šalje upite OpenRouter-u.
    - Keširanje odgovora (da ne trošimo API limit bezveze).

3.  **Korak 2: Ontology Service**:
    - Mapiranje `item` -> `cluster` (iz `semantic_clusters.json`).
    - Mapiranje `cluster` -> `cluster` (iz `implications.json` - *potrebno agregirati implikacije zadataka na nivo klastera*).
    - Generisanje `.ttl` fajla.

4.  **Korak 3: API/CLI Update**:
    - Dodavanje komande `python -m app.main enrich` (poziva LLM).
    - Dodavanje komande `python -m app.main export-rdf`.

---

## Sledeći koraci za tebe (Korisnik):
1.  Nabavi API Key sa [OpenRouter.ai](https://openrouter.ai/).
2.  Prosledi mi API Key.
3.  Ja krećem sa pisanjem koda.
