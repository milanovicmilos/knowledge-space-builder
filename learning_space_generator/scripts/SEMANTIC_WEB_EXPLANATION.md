# SEMANTIČKI WEB INTEGRACIJA - Kako funkcioniše u Knowledge Space Sistemu

## 📚 Uvod: Šta je Semantički Web?

**Semantički web** je tehnologija koja čini da računari razumeju ZNAČENJE podataka, ne samo njihov oblik.

Primeri:
- **Običan web:** "s1m11a091" (samo tekst/ID, nema značenja)
- **Semantički web:** "s1m11a091 = zadatak o linearnim funkcijama koji zahteva znanje o nagibima"

---

## 🎯 Kako Semantički Web Funkcioniše u Tvom Sistemu

### 1. **LLM MAPIRANJE** (Dodavanje Semantike)

```
INPUT (121 sirovih pitanja):
  s1m11a091  (samo ID)
  s1m11a101  (samo ID)
  s1m12a191  (samo ID)
  
                ↓ (LLM procesa)
         
SEMANTIČKA TRANSFORMACIJA:
  s1m11a091 = "Lineare Funktionen" (znači: zadatak o linearnim funkcijama)
  s1m11a101 = "Gleichungen" (znači: zadatak o jednačinama)
  s1m12a191 = "Steigung" (znači: zadatak o nagibu)
  
REZULTAT: 121 ID-a sada ima ZNAČENJE!
```

**Šta to znači?**
- Računar sada "razume" da s1m11a091 i s1m11b131 oba govore o linearnim funkcijama
- Može grupisati slične zadatke zajedno
- Može preporučiti zadatke na osnovu ZNAČENJA, ne samo ID-a

---

### 2. **ONTOLOGIJA** (Formalni Opis Znanja)

Tvoj sistem generiše `sotis_ontology.ttl` fajl koji je u RDF (Resource Description Framework) formatu:

```turtle
# Primer iz tvoje ontologije:

@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

# Koncept: Linearne Funkcije
<http://sotis.phsg.ch/concept/LineareFunktionen> 
    a skos:Concept ;
    skos:prefLabel "Lineare Funktionen" ;
    skos:definition "Funkcije oblika f(x) = mx + b" ;
    skos:broader <http://sotis.phsg.ch/concept/Funktionen> ;
    skos:narrower <http://sotis.phsg.ch/concept/Steigung> ;
    skos:related <http://sotis.phsg.ch/concept/Gleichungen> .
```

**Šta to znači?**
- Ontologija definiše RELACIJE između koncepata
- `broader` = nadređeni koncept (Linearne funkcije → Funkcije)
- `narrower` = podređeni koncept (Steigung → Linearne funkcije)
- `related` = povezani koncepti (Linearne funkcije ↔ Jednačine)

---

### 3. **PREREQUISITE RELACIJE** (Znanja Potrebna za Napredovanje)

Tvoj Knowledge Space definiše prerequisite-e:

```
Algebra → Analytička Geometrija
(Učenik mora znati Algebru pre nego što može razumeti Analitičku Geometriju)

Jednačine → Linearne Funkcije
(Učenik mora znati Jednačine pre nego što može razumeti Linearne Funkcije)
```

**Semantički web koristi ove relacije** da bi:
1. Automatski detektovao grešne prerequisite-e
2. Razumeo odnose između koncepata
3. Pronašao alternative (ako jedno ne radi, šta je alternativa?)

---

## 🔗 Konkretni Primeri - Kako Semantički Web Pomaže

### PRIMER 1: Pronalaženje Povezanih Teme

```
Učenik je naučio: "Steigung" (Nagib)

Semantički web pronalazi:
  ✓ Povezani koncepti:
    - Lineare Funktionen (koristi nagib)
    - Geradengleichungen (koristi nagib za jednačine)
    - Funkcionalne Zavisnosti (nagib = derivacija)

Rekomendacija: "Već znaš nagib, hajde da naučimo linearne funkcije!"
```

### PRIMER 2: Detektovanje Manjkavog Znanja

```
Učenik pokušava: "Lineare Funktionen" ali NE razume

Semantički web traži unazad (prerequisiti):
  ✗ Nema Steigung (nagib) znanja
  ✗ Nema Gleichungen (jednačine) znanja
  
Dijagnoza: "Trebaju ti osnove iz Steigung i Gleichungen!"
Preporuka: Vrati se na te koncepte prvo
```

### PRIMER 3: Pronalaženje Alternativnih Putanja

```
Učenik želi: Diferencijalnu Računicu

Direktna putanja je komplikovana. Semantički web pronalazi:

Putanja A (preko Funkcija):
  Funkcije → Linearne Funkcije → Grafički Prikazi → Nagib → Derivacija

Putanja B (preko Algebre):
  Algebra → Polinomi → Faktori → Derivacija

Preporuka: "Koji pristup te više zanima - grafički ili algebarski?"
```

---

## 💡 Ključne PREDNOSTI Semantičkog Web-a u Tvom Sistemu

### 1. **Automatska Povezanost**
```
Bez semantičkog web-a: s1m11a091 i s1m11b131 su samo dva odvojena ID-a
Sa semantičkim web-om: Oba su "Linearne Funkcije" - POVEZANI!
```

### 2. **Inteligentne Preporuke**
```
Bez: "Igraj sledeći nasumični zadatak"
Sa: "Završio si 3 od 6 Steigung zadataka. 
      Sada možeš početi sa Lineare Funktionen jer znaš sve prerequisite-e!"
```

### 3. **Pronalaženje Grešaka**
```
Bez: Učenik radi loše na zadatku - čudi što je to?
Sa: Ontologija pokazuje da je Gleichungen prerequisite.
    "Možda treba da vidiš gdje greške u Gleichungen znanju!"
```

### 4. **Prilagođeno Učenje**
```
Svaki učenik ima drugačiji learning style:
- Neki počinju sa Steigung (nagib)
- Neki počinju sa Gleichungen (jednačine)
- Neki počinju sa Funkcije i Grafici

Semantički web to omogućava kroz ontologiju!
```

---

## 🏗️ Arhitektura: Kako Sve Radi Zajedno

```
┌─────────────────────────────────────────────────────────────┐
│                   INPUT: 121 PITANJA (CSV)                  │
│              s1m11a091, s1m11a101, s1m12a191...            │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│         FAZA 1: LLM MAPIRA PITANJA NA KONCEPTE              │
│  "s1m11a091 je o Linearne Funktionen"                       │
│  LLM_ITEM_CLASSIFICATIONS.JSON (121 mapiranja)             │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│    FAZA 2: SEMANTIČKA ANALIZA - GRUPISANJE U KLASTER      │
│  "Ova 6 pitanja su o linearnim funkcijama - grupi ih!"      │
│  SEMANTIC_CLUSTERS.JSON (24 klastera)                       │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│   FAZA 3: AGREGACIJA - 121 PITANJA → 23 KONCEPTA           │
│  "Svi s1m* pitanja o linearnim funkcijama = 1 koncept"      │
│  AGGREGATED_CONCEPTS.CSV (23 koncepta)                      │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│    FAZA 4: IITA - PRONALAŽENJE PREREQUISITI                 │
│  "Steigung je prerequisit za Linearne Funkcije"             │
│  IMPLICATIONS.JSON (30 prerequisite relacija)               │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  FAZA 5: KNOWLEDGE SPACE - MOGUĆE STATE-OVE UČENIKA         │
│  {} → {Steigung} → {Steigung, Gleichungen} → ...           │
│  KNOWLEDGE_SPACE.JSON (355 mogućih kombinacija)             │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  FAZA 6: ONTOLOGIJA - FORMALNI SEMANTIČKI OPIS             │
│  RDF/TURTLE format za integraciju sa SOTIS platformom       │
│  SOTIS_ONTOLOGY.TTL (semantic web standard)                 │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│        PRIMENA: ADAPTIVE INTELLIGENT TUTORING               │
│  - Detektuje gde je učenik u knowledge space-u              │
│  - Pronalazi sledeće koncepte koje treba da nauči           │
│  - Preporučuje zadatke na osnovu semantic-a                 │
│  - Detektuje manjka znanja na osnovu ontologije            │
│  - Integruje se sa SOTIS platformom                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎓 PEDAGOGIJSKA PRIMENA - Kako Tutor Koristi Ontologiju

### Primer Dialog sa Adaptive Tutora:

```
TUTOR: "Pozdrav! Hajde da naučimo Matematiku!"
STUDENT: "OK, šta prvo?"

TUTOR (koristi ontologiju):
  "Pronašao sam 8 mogućih početnih koncepata.
   Šta te više zanima?"
   
  1. Steigung (Nagib) - vizuelno intuitivan
  2. Gleichungen (Jednačine) - algebarski pristup
  3. Funktionen (Funkcije) - apstraktan pristup
  
STUDENT: "Voleo bih grafički pristup!"

TUTOR (koristi semantic relationships):
  "Super! Hajde sa Steigung.
   Saznićeš kako se nagib crta na grafikonu.
   Zatim ćemo naučiti Lineare Funktionen.
   Na kraju će biti jednostavno!"

[Student završava Steigung zadatke]

TUTOR (koristi implications iz Knowledge Space):
  "Odličan posao! Završio si Steigung.
   Sada možeš početi sa Lineare Funktionen
   jer su svi prerequisiti zadovoljeni!
   
   PREREQUISITI PROVERA:
   ✓ Steigung (završeno!)
   ✓ Gleichungen (trebalo bi! Želiš li da vidiš osnove?)"

STUDENT: "Gde su osnove Gleichungen?"

TUTOR (koristi ontologiju za pronalaženje):
  "Pronašao sam 6 relativnih osnova zadataka.
   Hajde da vidimo koja je greška..."
```

---

## 📊 Kako Semantički Web Štiti Kvalitet Edukacije

### 1. **Konzistentnost**
- Svi učenici koriste ISTU ontologiju
- Nema "random" redosleda učenja
- Svi prerequisiti su proveereni

### 2. **Prilagođenost**
- Različiti učenici mogu različitim putanjama
- Ali sve putanje su matematički validne
- Ontologija osigurava da niko ne bude "izgubljen"

### 3. **Trazaviljivost**
- Svaki koncept je eksplicitno definisan
- Relacije su dokumentovane
- Lako je dodavati nove koncepte bez narušavanja sistema

### 4. **Interoperabilnost**
- Ontologija je u standardnom RDF formatu
- Može se koristiti u različitim platformama
- SOTIS može direktno učitati ovu ontologiju!

---

## 🚀 Zaključak: Zašto je Ovo Revolucionarno?

**Stari pristup (bez semantičkog web-a):**
```
PDF lekcija → Učenik radi random zadatke → Greške → Ponos/Obeznađenost
```

**Tvoj pristup (sa Knowledge Space + Semantičkim web-om):**
```
Učenik → Tutor RAZUME gde je učenik (state u KS)
       → Tutor ZOOZEZNAJE prerequisite (ontologija)
       → Tutor PERSONALIZUJE preporuke (multiple paths)
       → Učenik NAPREDUJE garantovano (no dead-ends)
       → SOTIS integriše sve (ITS sistem)
```

**REZULTAT:**
✅ Inteligentno Tutoriranje (ITS)
✅ Adaptivno Učenje (personalizovano)
✅ Potpuna Trazaviljivost (znamo gde je student)
✅ Međusobna Kompatibilnost (standardni web formati)
✅ Naučna Validnost (Knowledge Space Theory)
