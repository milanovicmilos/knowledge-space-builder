# Progress i dokumentacija izvršavanja projekta

Ovaj dokument opisuje kompletan tok izvršavanja tvog projekta od momenta upload-a CSV fajla, značenje svih relevantnih argumenata (CLI i API), detalje algoritama koji se koriste, trenutnu arhitekturu sistema i poređenje tvoje NEAT implementacije sa projektom https://github.com/nemanja-m/learning-space-generator. Sadržaj je na srpskom jeziku.

---

**1) Ulaz: upload CSV fajla**

- Frontend:
  - Korisnik u `frontend` upload-uje CSV kroz komponentu `UploadForm.tsx` (UI šalje fajl na backend API endpoint).
  - `TaskForm.tsx` omogućava korisniku da postavi parametre zadatka, uključujući `max_item_clusters` (podrazumevano `null` = auto), `min_pairs`, `row_coverage_thresh` i ostale parametre NEAT/LSG.
- API:
  - Frontend koristi `axios` klijent (`frontend/src/api/client.ts`) da pošalje POST zahtev sa fajlom i parametrima na backend API (`/api/v1/tasks` ili sličan endpoint u `backend/app/api/v1`).
  - Backend endpoint prima fajl, skladišti ga (obično u privremeni folder ili upload storage), i enqueues Celery zadatak koji pokreće obradu.

**2) Pokretanje zadatka (backend / Celery)**

- `backend/app/celery_app/tasks.py` kreira i pokreće proces koji izvršava learning-space-generator (LSG) ili NEAT skriptu.
- Ako korisnik postavi `max_item_clusters`, backend dodaje CLI flag `--max-item-clusters N` u poziv skripte; ako je `None`, flag se NE šalje i LSG bira K automatski.
- CLI primer pokretanja (ilustracija):
  - `python -m lsg.run --input path/to/upload.csv --min-pairs 500 --row-coverage-thresh 0.8 --max-item-clusters 3`
  - (Tačan CLI interfejs zavisi od argparser-a u `lsg/run.py`.)

**3) Preprocessing podataka (u LSG / `lsg/run.py`)**

- Učitavanje CSV: `pandas.read_csv(path, sep=...)` i identifikacija binarnih kolona (`_identify_binary_columns`).
- Formiranje matrice `sub` koja sadrži odgovore (items x students), sa NaN za nepostojeće odgovore.
- Parametri uticaja: `row_coverage_thresh`, `min_pairs`, `randomize`, `items_min`, `items_max`, `max_item_clusters`.
- Računa se `m = broj item-a` i `overall_density` = popunjenost matrice (ne-NaN ćelije / ukupne ćelije).
- Na osnovu `overall_density` se postavlja preporučeni opseg K (`k_range_min`, `k_range_max`) adaptivno:
  - Vrlo retko (<10%): velika očekivanja klastera (manji broj K)
  - 10-30%: srednji klasteri
  - >30%: fini (manji) klasteri
- Računa se `absolute_max_k` na osnovu minimalne veličine klastera (npr. min 3 items po klasteru).

**4) Računanje sličnosti (pairwise similarity)**

- Funkcija `_pairwise_item_similarity(values_df, min_pairs=500)` radi:
  - Za svaki par item-a (i, j):
    - Uzme samo učenike koji su odgovorili na oba item-a (maskiranje NaN)
    - Ako broj zajedničkih posmatranja < `min_pairs`, sličnost = 0 (nedovoljno podataka)
    - Inače: izračuna Pearson korelaciju između vektora odgovora `vi` i `vj`
    - Mapira korelaciju iz opsega [-1,1] u [0,1]: `sim = 0.5*(corr + 1)` i kroji u [0,1]
  - Vraća sim_matrix (m x m). Distanca se računa kao `dist_matrix = 1.0 - sim_matrix` i dijagonala se postavlja na 0.

- Napomena: ovo znači da su negativne korelacije tretirane blizu 0 (nema sličnosti).

**5) Automatski izbor broja klastera K (silhouette)**

- Ako `max_item_clusters` nije eksplicitno zadat, LSG sam bira optimalan `K` tako što testira sve vrednosti `k_test` u opsegu `k_min`..`k_max`.
- Za svaki `k_test` se koristi `AgglomerativeClustering(n_clusters=k_test, linkage='average')` i dobija `labels_test` na `dist_matrix`.
- Računa se `silhouette_score(dist_matrix, labels_test, metric='precomputed')`.
- Najbolji `k_test` koji daje najveći silhouette score se bira kao `k_optimal`.
- Konačno se izvršava finalni clustering sa `k_optimal` i dobijaju se `item_labels`.

**6) Post-clustering obrada i konstrukcija learning-space (NEAT i IITA deo)**

- Nakon grupisanja item-a, za svaki klaster se generiše lokalni response pattern set (IITA / NEAT pipeline). U projektu se nalaze dve opcije/algoritma za generisanje learning-space strukture:
  - IITA (Formal Concept Analysis / implication mining)
  - NEAT (evolutivni algoritam za učenje zavisnosti / prerequisite strukture)

- NEAT pipeline (u `learning-space-generator/lsg/algorithms/neat/` ili sličan path) radi sledeće (sažeto):
  - Inicijalizacija populacije kandidata (mreža veza između item-a reprezentuju mogućnost prerequisite-a)
  - Evaluacija svake jedinke prema fitness funkciji koja meri koliko dobro model predviđa odgovore / zadovoljava statističke odnose
  - Operatori selekcije, mutacije, i križanja koji evoluiraju populaciju kroz N generacija
  - Izbor najbolje jedinke i transformacija u strukturu znanja (usmereni graf prelazaka/prerequisite-a)

- IITA/ostatak: dodatna logika za ispis/strukturiranje rezultata u formatu `structured_output` sa poljima:
  - `metadata` (stats, korišćeni parametri)
  - `clusters` (list of clusters with their local learning_spaces)
  - `isolated_items` (items koji nisu u klasterima ili su izdvojeni)
  - `merged_learning_space` (kompozitni graf spojen preko klastera ili globalna struktura)

**7) Rezultati i njihovo skladištenje**

- Skripta generiše JSON/Pickles/MD artefakte u `output/` folderu (npr. `learning_space.json`, `iita_final.json`, `neat_final.json`).
- Backend beleži rezultate u bazu (opciono) i/ili vraća rezultat korisniku preko API. Frontend periodično proverava status Celery zadatka i kad je gotov preuzima rezultat i prikazuje ga kroz `GraphVisualization.tsx`.

**8) Značenje svih mogućih argumenata (pregled najvažnijih, verovatni nazivi prema `lsg/run.py`)**

- `--input` / `path`: putanja do CSV fajla (obavezno)
- `--min-pairs`: minimalan broj zajedničkih posmatranja između dva item-a da bi se računala korelacija (podrazumevano npr. 500)
- `--row-coverage-thresh`: minimalna pokrivenost reda da bi student bio uključen u analizu (npr. 0.8)
- `--max-item-clusters`: maksimalan broj klastera koje će algoritam razmotriti/ograničiti; ako nije postavljeno, koristi se automatski izbor (silhouette)
- `--items-min`, `--items-max`: korisnikom zadat opseg željene prosečne veličine klastera (utice na predloženi K)
- `--randomize`: random seed ili flag da se podaci permutuju pre analize
- `--output-dir`: direktorijum u koji se upisuju rezultati
- `--min-items-per-cluster` (ili policy): minimalna veličina klastera za izračunavanje `absolute_max_k`
- NEAT-specifični parametri (ako primenjeni):
  - `--generations`, `--population-size`, `--mutation-rate`, `--crossover-rate`, `--fitness-weight-*` itd.
  - Ovi parametri utiču na ponašanje evolucije i kvalitet finalne mreže.

(Napomena: tačni nazivi argumenata treba potvrditi iz `lsg/run.py` parser-a; ovde sam naveo najverovatnije i tipične opcije koje su prisutne u kodu.)

**9) Trenutna arhitektura sistema**

- Komponenta: Frontend
  - `frontend/`: React + TypeScript aplikacija (Vite), koristi `axios`, prikazuje formular, grafik, kontrolne elemente.
  - Ključne datoteke: `UploadForm.tsx`, `TaskForm.tsx`, `GraphVisualization.tsx`.

- Komponenta: Backend
  - `backend/`: FastAPI (verovatno), Pydantic sheme (`backend/app/schemas`), Celery zadaci u `backend/app/celery_app/tasks.py`.
  - Pokreće se kao webserver + worker (Celery) + broker (Redis) + baza (Postgres).
  - `celery_app/tasks.py` enqueues poziv koji pokreće externu Python skriptu `learning-space-generator` ili lokalne funkcije iz `lsg/`.

- Komponenta: Learning Space Generator (LSG / NEAT)
  - `learning-space-generator/`: nezavisan modul / paket koji sadrži `lsg/run.py`, implementacije algoritama (NEAT, IITA), utilse i runner.
  - Generiše artefakte u `output/`.

- DevOps / Deploy
  - `docker-compose.yml` orkestrira `frontend`, `backend`, `redis`, `postgres` i eventualno worker servise.

**10) Poređenje tvoje NEAT implementacije sa `nemanja-m/learning-space-generator`**

Napomena: Na osnovu dostupnih fajlova u workspace-u i attachmenta pretpostavljam da je tvoj projekat u velikoj meri baziran na `learning-space-generator` i da koristi slične module. Evo poređenja u ključnim tačkama:

- 1) Ulazni pipeline i preprocessing:
  - Oba projekta: koriste `pandas` za čitanje CSV i tretman NaN vrednosti.
  - Tvoj repo: `_pairwise_item_similarity` koristi Pearson korelaciju + prag `min_pairs` (isto ili veoma slično kao u `nemanja-m`).

- 2) Metoda za particionisanje item-a:
  - Tvoj repo: koristi agglomerative clustering + silhouette za automatski izbor K.
  - `nemanja-m` repo: iz istog URL-a takođe implementira silhouette-based K selection (ili vrlo sličnu logiku); u principu isti pristup.

- 3) NEAT implementacija (evolucija):
  - Tvoj repo: integrisan NEAT pipeline koji evoluira grafove i koristi fitness funkciju zasnovanu na predikciji/poklapanju statistike.
  - `nemanja-m`: verovatno slična implementacija NEAT ili eksterni NEAT modul; glavne razlike obično nastaju u detaljima fitness funkcije, reprezentaciji jedinki (directed acyclic graph vs adjacency matrices), i operatorima mutacije.

- 4) Heuristike i sigurnosni pragovi:
  - Tvoj projekt: ima pragove `min_pairs`, `row_coverage_thresh`, i adaptive K range na osnovu `overall_density`.
  - `nemanja-m`: po dostupnom kodu, koristi silhouette i slično podešavanje; moguće razlike: izbor linkage metode (`average`), korišćenje dist_matrix kao `precomputed`, i fallback vrednosti ako silhouette ne radi.

- 5) Celokupna integracija i UI:
  - Tvoj projekat: kompletna integracija sa frontend-om i ReactFlow vizualizacijom; UI bonusi (fullscreen, hover label expand, dagre layout).
  - `nemanja-m`: orijentisan više kao research/CLI alat (manje UI integracije) — iz URL-a se vidi LSG repo koji je primarno biblioteka/skripta.

Zaključak poređenja: implementacija u tvom projektu i `nemanja-m/learning-space-generator` su veoma bliske — isti osnovni principi (pairwise similarity, precomputed dist matrix, agglomerative clustering, silhouette selection). Moguće razlike su u konkretnoj NEAT fitness funkciji, parametrima i UI integraciji; tvoje rešenje je lepše integrisano u web-aplikaciju.

**Detaljno: razlike u računanju fitness/discrepancy**

- Sažetak razlika:
  - `Nemanjin (evolution.py)`: diskrepancija se računa preko particionisanja pattern-a na najbliže knowledge state-ove (centroid) i zatim sumiranjem ponderisane bit-distance: za svaki response pattern i svaki state sabira se `partition_value * dissimilarity`.
  - `Workspace` (`evaluation.py` u `lsg/algorithms/neat`): diskrepancija je suma po pattern-ima od `min_loss` preko svih states, gde je `loss = mismatches * mismatch_penalty - matches * match_reward`. Nedostajuće vrednosti se ignorišu preko `pattern_mask` u vektorisanoj verziji.

- Konsekvence razlika:
  - Agregacija: Nemanjin pristup agregira grešku kroz particije (težina = broj ponavljanja pattern-a), dok workspace pristup bira najbolje objašnjenje za svaki pattern (min-loss). Rezultat: workspace pristup je otporniji na outliere i bolje koristi pojedinačne dobre poklapanja.
  - Parametrizacija: Nemanjin pristup ne koristi `mismatch_penalty`/`match_reward`, kazna po različitosti je implicitno 1 po bitu; workspace pristup omogućava fino podešavanje odnosa kazne/nagrade.
  - Missing values: Nemanjin kod nema eksplicitno maskiranje missing pozicija (računa bit-distance direktno), dok workspace kod eksplicitno ignoriše missing položaje prilikom računanja loss-a, što menja ponašanje na realnim nepotpunim dataset-ima.
  - Skaliranje kazne za veličinu: oba imaju `node_size_penalty` i `valid_learning_space_weight`, ali default vrednosti se razlikuju (`25.6` vs `50.0` ili varijante), što menja relativni uticaj kompleksnosti LS.

- Primer (intuicija): za pattern sa par posmatranih položaja koji se savršeno slaže sa jednim state-om, workspace pristup dodeljuje malenu ili nultu kaznu (min-loss = 0), dok Nemanjin pristup može dati veću doprinosu diskrepanciji ako particija i ponderi utiču drugačije.

**Preporuka**

- Ako želiš da oba pristupa daju poredivije rezultate, uradi tri koraka:
  1. Uskladi `node_size_penalty` i `valid_learning_space_weight` među kopijama.
  2. Dodaj `pattern_mask` tretman u Nemanjin kod ili isključi maskiranje pri testiranju u workspace verziji za direktno poređenje.
  3. Napravi mali testni skript koji izračunava `discrepancy` za isti skup pattern-a i istih knowledge states koristeći obe funkcije i uporedi izlaze.

Želiš da ubacim ovaj test skript i rezultate u `progress.md`? (Mogu odmah kreirati skript `tools/compare_discrepancy.py` i pokrenuti ga na primer CSV-u iz `learning-space-generator/data`.)

---

Ako želiš, mogu da:
- Izlistam tačne CLI argumente čitajući početak `lsg/run.py` (argparse sekciju) i ubacim ih eksplicitno u `progress.md`.
- Dodatno: ubacim sample log fajl sa silhouette skorovima po testiranom K (ako želiš da vidiš za tvoj konkretan upload). 

Javi šta želiš dalje (da li da dodam tačan `argparse` iz `lsg/run.py` u `progress.md` i da ga popunim kompletno?).

**DODATNO: Detaljna objašnjenja (Silhouette, NEAT nagrade/kažnjavanja, tretman NaN)**

- **Silhouette score — šta je i kako se računa**
  - Silhouette koeficijent za pojedinačni primerak i označava koliko je primerak dobro uklopljen u svoj klaster u odnosu na najbliži drugi klaster.
  - Matematika (pojednostavljeno): za primerak i definišemo
    - `a(i)` = prosečna distanca između i i svih ostalih u istom klasteru (intra-cluster)
    - `b(i)` = najmanja prosečna distanca između i i članova nekog drugog klastera (najbliži sused-klaster)
    - Silhouette: `s(i) = (b(i) - a(i)) / max(a(i), b(i))`
  - Domen vrednosti: `s(i)` ∈ [-1, 1]. Veće vrednosti znače bolje odvojene i homogenije grupe. Globalni silhouette za K je prosečna vrednost `s(i)` preko svih uzoraka.
  - U praksi: algoritam testira više K i bira onaj sa najvišim prosečnim silhouette score — to je upravo pristup koji koristi `lsg/run.py`.

- **NEAT fitness / nagrade i kažnjavanja (kako radi u ovom projektu)**
  - U `lsg/algorithms/neat/evaluation.py` fitness se računa preko posredne vrednosti koja se zove *discrepancy* (diskrepancija). Niža diskrepancija = bolji fit, a genome.fitness je negativna funkcija diskrepancije plus dodatne komponente.
  - Ključni elementi:
    - `mismatch_penalty` (podrazumevano 1.0): kazna po svim neslaganjima između odgovora i stanja znanja.
    - `match_reward` (podrazumevano 0.0): nagrada (smanjuje gubitak) za svako slaganje između odgovora i stanja.
    - `node_size_penalty`: dodatna kazna proporcionalna broju čvorova/stanja u learning-space-u (sprečava prevelike strukture).
    - `valid_learning_space_weight`: nagrada (velika vrednost) ako je konstrukcija validna (sadrži prazno i puno stanje i zatvorena je pod unijom), podstiče konzistentne LS.
  - Kako se diskrepancija računa (sa maskom za nedostajuće vrednosti): za svaki observed response pattern računaju se
    - `mismatches`: broj posmatranih položaja gde state != response
    - `matches`: broj posmatranih položaja gde state == response
    - `loss` = `mismatches * mismatch_penalty - matches * match_reward`
    - Za jedan response pattern, diskrepancija je `min` od `loss` preko svih knowledge states (pronalazi se najbliže stanje koje najbolje objašnjava odgovor). Ukupna diskrepancija je suma tih minimalnih gubitaka za sve pattern-e.
  - Fitness se zatim postavlja ovako (pojednostavljeno):
    - `fitness = -(discrepancy + size_fitness) + valid_ls_fitness`
    - Gde `size_fitness = num_nodes * node_size_penalty` i `valid_ls_fitness = int(is_valid) * valid_learning_space_weight`.

- **Tretman nedostajućih vrednosti (NaN / '-')**
  - Pristup: pattern stringovi parsimovani su u dve matrice: `pattern_array` (0/1 vrednosti) i `pattern_mask` (1 = observed, 0 = missing).
  - U vektorisanoj verziji (`_compute_discrepancy_vectorized`) se operacije `eq` i `neq` maskiraju sa `pattern_mask`, tako da se **nedostajući položaji uopšte ne računaju** ni kao match ni kao mismatch.
  - U pairwise similarity (`_pairwise_item_similarity` u `lsg/run.py`) parovi item-a koji imaju premalo zajedničkih posmatranja (`min_pairs`) dobijaju sličnost 0 — dakle ti parovi se tretiraju kao nerelevantni za klasterovanje.

- **Uticaj parametara na ponašanje NEAT-a**
  - Povećanje `mismatch_penalty` → jače kažnjavanje neslaganja → evolucija favorizuje genome koje pokrivaju odgovore tačno, moguće uz veću kompleksnost (više stanja) ako nije dovoljno stroga `node_size_penalty`.
  - Povećanje `match_reward` (>0) → nagrađuje tačna slaganja (smanjuje loss) i može dovesti do preferiranja jednostavnih stanja koja dobro objašnjavaju veliki broj pattern-a.
  - Visok `node_size_penalty` → penalizuje kompleksnost i favorizuje manje learning-space-ove.
  - `valid_learning_space_weight` služi kao veliki bonus za striktno validne LS; to često balansira kaznu za veličinu i vodi sistem ka konzistentnim, zatvorenim strukturama.

- **Poređenje sa "nemanja-m/learning-space-generator"**
  - Napomena: nemam direktan pristup putanji `C:\Users\Milos\PythonProjects\sot\learning-space-generator` iz ovog radnog okruženja (ograničenja workspace-a). Međutim, u repozitorijumu koji se nalazi u workspace-u (`learning-space-generator/lsg/algorithms/neat`) nalazimo sledeće konkretne elemente:
    - Vektorisana i fallback (non-vectorized) implementacija diskrepancije koja eksplicitno koristi `pattern_mask` da ignoriše nedostajuće vrednosti.
    - Parametri `mismatch_penalty`, `match_reward`, `node_size_penalty` i `valid_learning_space_weight` koje sam opisao iznad.
  - Ako je "nemanja-m" originalni repozitorijum iz koga si preuzeo kod, onda su verovatno mehanike nagrade/kažnjavanja identične (jer isti fajl `evaluation.py` implementira logiku). Ako želiš strogo poređenje između dve fizičke kopije (tvoj projekt vs nemanjin folder na drugom mestu), kopiraj taj repozitorij u workspace (`sot/learning-space-generator`) ili priloži relevantne fajlove i ja ću uporediti liniju-po-liniju.

**Zaključak i sledeći koraci**

- Dodatno sam objasnio Silhouette metod, detaljno opisao kako NEAT u ovom projektu dodeljuje kazne i nagrade, i kako se tretiraju nedostajuće vrednosti.
- Ako želiš kompletno, liniju-po-liniju poređenje sa nemanjinom kopijom iz `C:\Users\Milos\PythonProjects\sot\learning-space-generator`, prebaci taj direktorijum u workspace ili pošalji fajlove; ja ću uraditi diferencijalnu analizu i ubaciti je u `progress.md`.

---

