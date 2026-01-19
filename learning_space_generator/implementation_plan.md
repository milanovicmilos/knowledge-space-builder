# Plan Implementacije Projekta: Konstrukcija i Vizuelizacija Prostora Znanja (KST)

Ovaj dokument definiše korake za realizaciju naučnog rada, sa ciljem generisanja strukture znanja kompatibilne sa formatom `profesor_example.json` (Graf stanja znanja / Covering Relation).

## 1. Faza: Priprema i Čišćenje Podataka
**Cilj:** Pripremiti `matheGesamt.csv` za analizu, eliminišući šum koji može poremetiti IITA algoritam.

*   **Učitavanje:** Parsiranje CSV fajla (separator `;`), izdvajanje kolona sa zadacima (`s1m11a091`, itd.).
*   **Tretman Nedostajućih Vrednosti (Napredni pristup - 2026):**
    *   **Data Denoising (Autoencoder):** Implementacija Denoising Autoenkodera (DAE) koristeći PyTorch/TensorFlow.
    *   **Cilj:** Umesto prostog mapiranja `9999` u `0`, mreža će naučiti latentne obrasce iz validnih odgovora i "popuniti" nedostajuće vrednosti ili ispraviti nasumične greške ("careless errors") na osnovu verovatnoće.
    *   **Rezultat:** "Očišćena" binarna matrica koja vernije odražava pravo znanje studenta pre puštanja u IITA algoritam.
*   **Binarizacija:** Osigurati da je matrica odgovora striktno binarna `{0, 1}`.

## 2. Faza: Ekstrakcija Relacija (IITA Algoritam)
**Cilj:** Otkriti zavisnosti između zadataka (npr. "Znanje A je preduslov za Znanje B").

*   **Algoritam:** Implementirati `Corrected IITA` ili `IITA` (Inductive Item Tree Analysis).
*   **Proces:**
    1.  Izračunati stope "kontraprimera" za svaki par zadataka $(j, i)$ u podacima (slučajevi gde student zna teži zadatak $i$, a ne zna lakši $j$).
    2.  Identifikovati parove sa minimalnom stopom greške (npr. $error < 5\%$).
    3.  Konstruisati **Surmise Relaciju** (kvazi-uređenje) zasnovano na ovim podacima.
*   **Izlaz Faze:** Lista implikacija (npr. `s1m11 -> s1m12`).

## 3. Faza: Generisanje Prostora Znanja (JSON Format)
**Cilj:** Transformisati relacije iz Faze 2 u graf stanja znanja identičan `profesor_example.json`.

*   **Birkhoff-ova Teorema:** Iskoristiti matematičku vezu između *surmise* relacije i prostora znanja (familija skupova zatvorena za uniju i presek).
*   **Generisanje Stanja:**
    1.  Početi od praznog skupa `` {} ``.
    2.  Iterativno dodavati zadatke koji nemaju neispunjene preduslove.
    3.  Generisati sva validna "stanja znanja" (skupove zadataka koje je moguće znati).
*   **Konstrukcija Grafa (Covering Relation):**
    *   Kreirati veze između stanja $S_1$ i $S_2$ ako je $S_2 = S_1 \cup \{x\}$ (stanja se razlikuju za tačno jedan zadatak).
*   **Eksport:** Sačuvati rezultat kao JSON:
    ```json
    {
      "{}": ["{a}"],
      "{a}": ["{a, b}"]
      ...
    }
    ```

## 4. Faza: Vizuelizacija i Aplikacija
**Cilj:** Kreirati interaktivni alat za PHSG.

*   **Tehnologija:** Python (Streamlit ili Flask) + biblioteka za grafove (npr. `Graphviz` ili `PyVis`, ili JavaScript `D3.js`).
*   **Funkcionalnosti:**
    *   Učitavanje JSON fajla.
    *   Prikaz Hasse dijagrama (čvorovi su stanja, grane su prelasci).
    *   Označavanje trenutnog stanja studenta na grafu.
    *   Preporuka "sledećeg koraka" za učenje (sledeći čvor u grafu).

## 5. Faza: Naučna Evaluacija
*   Poređenje generisanog grafa sa podacima (koliko studenata se tačno uklapa u neka od stanja).
*   Diskusija o prednostima hibridnog pristupa (Podaci + IITA = Interpretabilan Graf).
