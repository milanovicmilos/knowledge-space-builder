# Izveštaj o prostoru znanja — Projekat 3 (SOTIS 2026)

U okviru video demonstracije ste videli kako web aplikacija funkcioniše od upload-a CSV fajla sa test podacima do prikaza rezultata, grafikona i istorije. Ovde želim da objasnim šta se zapravo dešava u pozadini, kako algoritam radi, i da pokažem par konkretnih primera iz generisanog prostora znanja koji potvrđuju da algoritam pravi smislen pedagoški redosled.

---

## Kako funkcioniše algoritam (osnovni koraci)

Kada uploadujem CSV sa odgovorima studenata na test iz matematike, sistem prolazi kroz nekoliko faza:

**1. Priprema podataka (DAE preprocessing)**
Prvo se podaci očiste pomoću denoising autoencoder-a koji uklanja šum i normalizuje odgovore. Ovo je bitno jer realni podaci često imaju grešaka ili nedostajućih vrednosti. Algoritam trenira neuronsku mrežu koja uči da "popuni" šum i da prepozna pravilnost u matrici odgovora.

**2. Semantička klasifikacija (LLM + embeddings)**
Test stavke se automatski grupišu u koncepte preko LLM-a (GPT-4o-mini). Algoritam uzima tekstove pitanja i traži semantičku sličnost, npr. "lineare Funktionen", "Geradengleichungen", "Steigung" itd. Ovo je ključno jer ne radim sa pojedinačnim pitanjima već sa konceptima (npr. umesto 50 pitanja o linearnim funkcijama, imam jedan koncept "Lineare Funktionen").

**3. Agregacija koncepata**
Za svakog studenta se računa koliko je uspešan na svakom konceptu. Na primer, ako je student rešio 7 od 10 zadataka o pravama, a threshold je 0.5 (50%), to znači da je savladao koncept "Geradengleichungen". Na kraju se dobija binarna matrica: svaki student ili zna ili ne zna dati koncept.

**4. Analiza preduslova (IITA algoritam)**
Ovde algoritam analizira redosled u kojem su studenti savladavali koncepte i ekstrahuje **impliciranje**: ako je student A savladao koncept X, obično je prvo savladao koncept Y. Tako se dobija "prerequisite graf" — npr. da bi neko znao "Analytische Geometrie", prvo mora "Geradengleichungen". Ovo je bitno za tutorski sistem da ne gura studente na teže koncepte pre nego što su spremni.

**5. Generisanje prostora znanja**
Na osnovu preduslova se generiše prostor svih mogućih **stanja znanja**. Početno stanje je prazno (student ništa ne zna), i onda postepeno dodajem koncepte poštujući preduslove. Na primer:
- `{}` (prazan, nema znanja)
- `{Lineare Funktionen}` (naučio osnove)
- `{Lineare Funktionen, Geradengleichungen}` (sada može i prave jer ima bazu)
- `{Lineare Funktionen, Geradengleichungen, Analytische Geometrie}` (napreduje u geometriju)

Nije svaka kombinacija dozvoljena! Ako algoritam vidi da niko nikad nije znao "Analytische Geometrie" a da ne zna "Geradengleichungen", neće praviti takva stanja.

**6. Ostalo (vizualizacija, ontologija, validacija)**
Na kraju se generiše graf strukture, exportuje ontologija za SOTIS, i proverava konzistentnost podataka.

---

## Parametri i prilagođavanje

U demonstraciji sam koristio podrazumevane parametre, ali sistem je dizajniran tako da se sve może parametrizovati kroz konfiguraciju bez menjanja koda. To znači da profesori/istraživači mogu da eksperimentišu sa različitim podesima:

- **DAE parametri**: koliko epoha trenirati autoencoder, koliko "buke" dodati, kakav prag koristiti za čišćenje
- **Binarizacija**: na primer, da li student mora 50% ili 60% zadataka za mastery
- **IITA threshold**: koliko strogo tumačiti preduslove (veći threshold = manje ivica u grafu)
- **Max state size**: koliko najviše koncepata može biti u jednom stanju (sprečava eksploziju broja stanja)

Ovo se sve postavlja kroz `.env` fajl, pa sistem može da se prilagodi različitim domenima i različitim pedagoškim pristupima.

---

## Rezultati: 2938 stanja znanja

U trenutnom testu (sa matematičkim podacima od PHSG i podrazumevanim parametrima), algoritam je generisao **2938 mogućih stanja znanja**. To nije slučajan broj — to su samo ona stanja koja ili:
- Postoje u realnim studentskim podacima (posmatrana stanja), ili
- Leže na logičnim putanjama između njih (rana faza učenja).

Ovako izbegavam da sistem generiše milion teoretskih stanja koja nikad ne postoje u praksi.

---

## Konkretni primeri iz prostora znanja

Evo nekoliko ilustrativnih putanja koje pokazuju kako bi student mogao da napreduje kroz matematiku (svaka putanja počinje od praznog stanja):

### Primer 1: Putanja fokusirana na linearne funkcije

```
{} 
  → {Lineare Funktionen}
  → {Funktion und Gleichungen, Lineare Funktionen}
  → {Funktion und Gleichungen, Geradengleichungen, Lineare Funktionen}
  → {Funktion und Gleichungen, Geradengleichungen, Lineare Funktionen, Gleichungen}
```

**Zašto je ovo logično?**
Student prvo uči osnovni koncept linearnih funkcija. Kad to savlada, prirodno prelazi na opštije funkcije i jednačine. Tek onda dodaje specifičan koncept jednačina pravih (geradengleichungen), jer sad ima teorijsku bazu. Na kraju spaja to sa formalnim pristupom jednačinama. Preduslovi su poštovani: ne može neko učiti jednačine pravih ako ne razume šta je funkcija.

### Primer 2: Geometrijska putanja sa pravama

```
{} 
  → {Geradengleichungen}
  → {Geradengleichungen, Lineare Funktionen}
  → {Funktion und Gleichungen, Geradengleichungen, Lineare Funktionen}
  → {Analytische Geometrie, Funktion und Gleichungen, Geradengleichungen}
```

**Zašto je ovo logično?**
Ovde student kreće direktno od jednačina pravih (možda geometrijski pristup). Onda povezuje prave sa linearnim funkcijama (ista stvar, različit ugao). Kad razume funkcijske odnose, prelazi na opštiju analitičku geometriju. Preduslovi kažu: "Geradengleichungen → Analytische Geometrie", što se vidi u podacima: skoro niko ne zna analitičku geometriju a da ne zna prave.

### Primer 3: Funkcionalno-grafička putanja

```
{}
  → {Funktion und Gleichungen}
  → {Funktion und Gleichungen, Funktionen und Graphen}
  → {Funktion und Gleichungen, Funktionen und Graphen, Lineare Funktionen}
  → {Funktion und Gleichungen, Funktionen und Graphen, Lineare Funktionen, Steigung}
```

**Zašto je ovo logično?**
Student počinje sa opštim razumevanjem funkcija i jednačina. Onda dodaje vizualni pristup (grafovi). Kad ima teorijsku i vizuelnu bazu, konkretizuje kroz linearne funkcije. Tek na kraju dolazi koncept nagiba (Steigung), što je sofisticiraniji element. Ovo prati tipičan pedagoški redosled: prvo apstraktno, pa konkretno, pa detaljnije.

### Primer 4: Primena u finansijskoj matematici

```
{Funktion und Gleichungen, Geradengleichungen}
  → {Finanzmathematik, Funktion und Gleichungen, Geradengleichungen}
  → {Finanzmathematik, Funktion und Gleichungen, Geradengleichungen, Ratenzahlungen und Finanzmathematik}
```

**Zašto je ovo logično?**
Student koji već zna funkcije i prave može primeniti to u finansijskoj matematici (linearne funkcije su odlične za kamate i rate). Tek kad razume opštu finansijsku matematiku, može da ulazi u specifičniji deo (ratenzahlungen = rateizacija). Preduslovi su zadovoljeni: ne možeš razumeti rate ako ne razumeš osnovnu matematiku funkcija.

---

## Što je sistem pronašao u podacima

Algoritam je pronašao **40 prerequisite relacija** (kao "Geradengleichungen → Analytische Geometrie") .Na primer:

- `Lineare Funktionen → Grundlagen der Algebra` (najpre algebra, pa funkcije)
- `Anwendungsaufgaben / Gleichungen → Steigung` (zadaci sa jednačinama vode ka nagibu)
- `Geradengleichungen → Gleichungen` (prave su poseban slučaj jednačina)
- `Finanzmathematik → Funktionen` (finansijska matematika traži razumevanje funkcija)

---
