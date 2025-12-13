# Pokretanje Learning Space Generator

## Osnovno Pokretanje

Program se pokreće kao Python modul iz root direktorijuma projekta:

```bash
cd C:\Users\Milos\PythonProjects\knowledge-space-builder\learning-space-generator
python -m lsg.run [argumenti]
```

## Izbor Algoritma

### IITA (Default za velike domene)
```bash
python -m lsg.run --use-iita
```

### NEAT (Default)
```bash
python -m lsg.run
```

---

## Argumenti

### 🔹 Zajednički Argumenti (rade za oba algoritma)

| Argument | Skraćeno | Tip | Default | Opis |
|----------|----------|-----|---------|------|
| `--data-path` | `-d` | string | `data/ks_data.csv` | Putanja do CSV fajla sa response patterns |
| `--json` | `-j` | string | `learning_space.json` | Ime/putanja za JSON output |
| `--png` | `-i` | string | - | Ime/putanja za PNG graf (opciono) |
| `--silent` | `-s` | flag | `False` | Isključi verbose logovanje |
| `--config` | `-c` | string | `config/default.ini` | Putanja do config fajla |
| `--randomize-items` | `-r` | flag | `False` | Slučajan izbor kolona iz data |
| `--clear-cache` | - | flag | `False` | Obriši matrix completion cache pre pokretanja |
| `--no-cache` | - | flag | `False` | Onemogući caching (sporije) |

### 🔹 NEAT-Only Argumenti

| Argument | Skraćeno | Tip | Default | Opis |
|----------|----------|-----|---------|------|
| `--generations` | `-g` | int | `15` | Broj generacija evolucije |
| `--patience` | `-t` | int | `20` | Early stopping: zaustavi posle N generacija bez napretka |
| `--parallel` | `-p` | flag | `False` | Paralelna evaluacija genoma (brže) |
| `--plot` | `-l` | flag | `False` | Prikaži graf evolucije |
| `--greedy` | `-y` | flag | `False` | Radi dok ne nađe validnu learning space |

### 🔹 IITA-Only Argumenti

| Argument | Tip | Default | Opis |
|----------|-----|---------|------|
| `--use-iita` | flag | `False` | Koristi IITA umesto NEAT |
| `--iita-max-diff` | float | `0.05` | Threshold za prerequisite odnose (0.01-0.20) |

---

## Primeri Pokretanja

### IITA - Osnovni Primer
```bash
python -m lsg.run --use-iita --json rezultat.json
```

### IITA - Sa Vizualizacijom
```bash
python -m lsg.run --use-iita --json rezultat.json --png prerequisite_graph.png
```

### IITA - Sa Stellwerk Podacima i Grafom
```bash
python -m lsg.run \
  --use-iita \
  --data "data/ResponsePatterns_Stellwerk_Math_2018-2024(in).csv" \
  --iita-max-diff 0.08 \
  --json stellwerk_prerequisites.json \
  --png stellwerk_graph.png
```

### IITA - Silent Mode (bez verbose output-a)
```bash
python -m lsg.run --use-iita --silent --json tihi_output.json
```

### IITA - Različiti Thresholds
```bash
# Strožiji threshold (manje relacija, više root nodes)
python -m lsg.run --use-iita --iita-max-diff 0.05 --json strict.json

# Blaži threshold (više relacija, manje root nodes)
python -m lsg.run --use-iita --iita-max-diff 0.15 --json loose.json
```

---

### NEAT - Osnovni Primer
```bash
python -m lsg.run --generations 100 --json learning_space.json
```

### NEAT - Sa Paralelizacijom (brže)
```bash
python -m lsg.run --generations 100 --parallel --json ls_parallel.json
```

### NEAT - Greedy Mode (radi dok ne uspe)
```bash
python -m lsg.run --greedy --json ls_greedy.json
```

### NEAT - Sa Vizualizacijom
```bash
python -m lsg.run \
  --generations 100 \
  --parallel \
  --plot \
  --json ls_full.json \
  --png ls_full.png
```

### NEAT - Silent Mode
```bash
python -m lsg.run --generations 50 --silent --json tihi_neat.json
```

### NEAT - Custom Config
```bash
python -m lsg.run \
  --config config/custom.ini \
  --generations 200 \
  --patience 30 \
  --json custom_ls.json
```

---

## Detalji Argumenata

### `--data-path` (Putanja do podataka)
- Očekuje CSV fajl sa binary response patterns
- Format: studenti u redovima, pitanja u kolonama
- Vrednosti: `0` (netačno), `1` (tačno), `NA` (nije pokušano)
- Primer: `--data-path "data/moji_podaci.csv"`

### `--json` (JSON Output)
- Ako je samo ime fajla (bez `/` ili `\`), čuva u `output/data/`
- Ako je puna putanja, čuva tamo gde je navedeno
- **IITA format:** Prerequisite struktura sa item names
- **NEAT format:** Learning space sa knowledge states
- Primeri:
  ```bash
  --json rezultat.json              # → output/data/rezultat.json
  --json C:/moj_folder/data.json    # → C:/moj_folder/data.json
  ```

### `--png` (PNG Vizualizacija)
- Kreira graf learning space/prerequisites
- Ako je samo ime, čuva u `output/visualizations/`
- **NEAT:** Prikazuje knowledge states i njihove veze
- **IITA:** Prikazuje prerequisite graf sa bojama prema nivou
- Primer: `--png graph.png` → `output/visualizations/graph.png`

### `--silent` (Tihi Režim)
- Onemogućava verbose logovanje oba algoritma
- I dalje prikazuje osnovne info poruke
- Korisno za skripte/automatizaciju

### `--generations` (NEAT: Broj Generacija)
- Koliko generacija genetskog algoritma će se izvršiti
- Više generacija = bolja learning space, ali sporije
- Default: `15`
- Za production: `100-200`
- Primer: `--generations 150`

### `--patience` (NEAT: Early Stopping)
- Zaustavi ako nema napretka `N` generacija
- Štedi vreme ako algoritam stagnira
- Default: `20`
- Primer: `--patience 30`

### `--parallel` (NEAT: Paralelizacija)
- Koristi multiprocessing za evaluaciju
- **Samo za NEAT** - IITA je već dovoljno brz
- **Značajno brže** na multi-core procesorima
- Primer: `--parallel`

### `--plot` (NEAT: Plot Evolution)
- Prikazuje graf evolucije fitnessa tokom generacija
- **Samo za NEAT** - IITA nema generacije
- Korisno za debugging i analizu
- Primer: `--plot`

### `--greedy` (NEAT: Greedy Mode)
- Radi dok ne nađe **validnu learning space**
- Ignoriše `--generations` (beskonačno generacija)
- Zaustavlja se čim pronađe validan rezultat
- Primer: `--greedy`

### `--iita-max-diff` (IITA: Threshold)
- Kontroliše "strogost" prerequisite odnosa
- **Niži (0.01-0.05):** Strože, manje relacija, više root nodes
- **Srednji (0.05-0.10):** Balansiran (preporučeno)
- **Viši (0.10-0.20):** Blažije, više relacija, manje root nodes
- Default: `0.05`
- Preporučeno za Stellwerk: `0.08`
- Primer: `--iita-max-diff 0.08`

### `--clear-cache` (Obriši Cache)
- Briše sačuvanu matrix completion
- Korisno ako se podaci promene
- Primer: `--clear-cache`

### `--no-cache` (Bez Caching-a)
- Onemogućava cache za matrix completion
- Sporije (svaki put radi ALS iznova)
- Primer: `--no-cache`

---

## Output Fajlovi

### IITA JSON Format
```json
{
  "items": ["item1", "item2", ...],
  "prerequisites": {
    "item1": ["item5", "item7"],
    "item2": ["item8"]
  },
  "metadata": {
    "n_items": 120,
    "n_patterns": 224611,
    "max_diff": 0.08,
    "total_relations": 222
  }
}
```

### NEAT JSON Format
```json
{
  "∅": ["a"],
  "a": ["ab", "ac"],
  "ab": ["abc"],
  ...
}
```

---

## Upozorenja

### ⚠️ NEAT-Only Argumenti sa IITA
Ako koristiš NEAT-only argumente sa `--use-iita`, dobićeš upozorenje:
```
[WARNING] ⚠️  NEAT-only arguments will be ignored with --use-iita: --parallel, --plot
```

**NEAT-only argumenti:**
- `--parallel` - IITA je već brz, ne treba mu paralelizacija
- `--plot` - IITA nema generacije, ne može plotovati evoluciju
- `--greedy` - IITA uvek pronalazi prerequisite strukturu
- `--generations` - IITA nema generacije
- `--patience` - IITA nema early stopping

---

## Preporuke

### Za Male Domene (< 50 pitanja)
```bash
python -m lsg.run --generations 100 --parallel --json result.json
```

### Za Velike Domene (100+ pitanja)
```bash
python -m lsg.run --use-iita --iita-max-diff 0.08 --json result.json
```

### Za Stellwerk Production Data
```bash
python -m lsg.run \
  --use-iita \
  --data "data/ResponsePatterns_Stellwerk_Math_2018-2024(in).csv" \
  --iita-max-diff 0.08 \
  --json stellwerk_output.json
```

### Za Brzi Test
```bash
python -m lsg.run --generations 10 --silent --json quick_test.json
```

---

## Troubleshooting

### Problem: "FileNotFoundError: data/ks_data.csv"
**Rešenje:** Pokreni iz root direktorijuma projekta ili koristi `--data-path` sa punom putanjom

### Problem: NEAT je prespor
**Rešenje:** Koristi `--parallel` ili pređi na `--use-iita` za velike domene

### Problem: IITA daje previše prerequisite relacija
**Rešenje:** Smanji `--iita-max-diff` (npr. sa 0.08 na 0.05)

### Problem: IITA daje premalo prerequisite relacija
**Rešenje:** Povećaj `--iita-max-diff` (npr. sa 0.05 na 0.10)

### Problem: Previše logova u konzoli
**Rešenje:** Koristi `--silent`

---

## Performance

| Algoritam | 30 items | 120 items | Brzina |
|-----------|----------|-----------|--------|
| **NEAT** | ~30 sec | ❌ Ne radi | Spor |
| **NEAT --parallel** | ~15 sec | ❌ Ne radi | Brži |
| **IITA** | ~2 sec | ~2 min | Brz |

**Zaključak:** Za >50 items, koristi IITA.
