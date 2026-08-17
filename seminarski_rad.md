




Seminarski rad

Automatizovano generisanje prostora znanja
zasnovano na studentskim odgovorima

Arhitektura i implementacija veb platforme








Autor:	 Miloš Milanović
Predmet: Savremene obrazovne tehnologije i standardi, Semantički veb
Datum: Februar 2026.
 
Sadržaj
Sažetak	1
1. Uvod	2
1.1 Ciljevi istraživanja	2
1.2 Organizacija rada	2
2. Teorijske osnove	4
2.1 Teorija prostora znanja	4
2.2 Algoritam induktivne analize stabla stavki	4
2.3 Mreža za uklanjanje šuma	4
2.4 Semantička klasifikacija stavki	5
2.5 Semantički veb i obrazovne ontologije	5
3. Arhitektura sistema	6
4. Primenjene tehnologije	7
5. Model podataka	9
6. Analitički tok obrade	10
6.1 Popunjavanje podataka i uklanjanje šuma	10
6.2 Semantička klasifikacija stavki	10
6.3 Sažimanje na nivo koncepta	11
6.4 Analiza zahtevnosti stavki	11
6.5 Ekstrakcija relacija preduslova	11
6.6 Generisanje prostora stanja znanja	11
6.7 Vizualizacija, validacija i generisanje ontologije	11
7. Pozadinski server i REST API	13
8. Korisnički interfejs	15
8.1 Unos podataka	15
8.2 Praćenje napretka	15
8.3 Pregled rezultata	16
8.4 Istorija analiza	18
9. Evaluacija sistema	19
9.1 Strukturna validacija	19
9.2 Semantičko-pedagoška validacija	20
9.2.1 Primer preporučene putanje učenja	20
9.3 Operativna validacija	20
10. Diskusija	22
10.1 Prednosti predloženog rešenja	22
10.2 Ograničenja	22
10.3 Pravci budućeg unapređenja	22
10.3.1 Pedagoška proširivost	22
10.3.2 Tehnička robustnost	22
10.3.3 Interoperabilnost	23
11. Zaključak	24
Literatura	25
 
Sažetak
U savremenom obrazovnom okruženju personalizovano učenje pretpostavlja sposobnost sistema da precizno modelira znanje učenika i na osnovu tog modela predloži optimalan redosled usvajanja novih sadržaja. Teorija prostora znanja nudi matematički rigorozan okvir za takvo modeliranje, ali njena primena na empirijske obrazovne podatke ostaje izazovna — naročito kada su ulazni podaci nepotpuni, a domeni znanja semantički bogati.
Ovaj rad opisuje arhitekturu i implementaciju veb platforme koja automatizuje generisanje prostora znanja iz empirijskih podataka o postignućima studenata, primenom integrisanog analitičkog toka od devet uzastopnih faza. Sistem kombinuje mreže za uklanjanje šuma za popunjavanje nepotpunih podataka, transformerske modele za semantičku klasifikaciju obrazovnih stavki i algoritam induktivne analize stabla stavki za ekstrakciju relacija preduslova. Završni model znanja mapira se na ontološki sloj u okviru projekta Savremenih obrazovnih tehnologija i standarda (SOTIS).
Evaluacija je sprovedena na skupu podataka sa 692 studenta i 121 obrazovnom stavkom organizovanom u 7 koncepata. Rezultujući prostor znanja sadrži 44 validna stanja, a strukturna validacija potvrdila je punu matematičku ispravnost modela.
 
1. Uvod
Personalizovano učenje počiva na sposobnosti obrazovnog sistema da za svakog učenika odredi šta zna, šta još nije savladao i kojim redosledom treba da usvaja nova znanja. Teorija prostora znanja, koju su formulisali Doignon i Falmagne (1985), nudi matematički okvir koji upravo to čini mogućim: domen znanja modeluje se kao delimično uređen skup u kome relacija preduslova između obrazovnih stavki određuje skup dostižnih stanja znanja svakog učenika. Ovakav pristup omogućava sistematsko zaključivanje o kompetencijama i automatizovano kreiranje optimalnih nastavnih putanja.
Praktična primena ove teorije suočava se sa dva ključna izazova. Ručno definisanje relacija preduslova vremenski je zahtevno i podložno subjektivnim greškama, naročito u domenima sa velikim brojem stavki. Obrazovni podaci u stvarnim okruženjima retko su potpuni: nedostajuće vrednosti i merni šum ozbiljno ugrožavaju kvalitet svakog analitičkog postupka. U skupu podataka analiziranom u ovom radu, udeo nedostajućih odgovora iznosi oko 59%, što čini prethodno popunjavanje podataka neophodnim korakom pre strukturne analize.
Ovaj rad prezentuje sistem koji oba izazova prevazilazi na integrativan način. Mreža za uklanjanje šuma obezbeđuje robustno popunjavanje nepotpunih matrica odgovora; transformerski modeli za semantičku reprezentaciju rečenica omogućavaju automatsko grupisanje stavki u koherentne koncepte; algoritam induktivne analize stabla stavki iz tako pripremljene matrice izvlači strukturu preduslova bez ručne ekspertske intervencije. Sistem je pozicioniran u okviru projekta SOTIS i generiše model znanja koji se mapira na ontološki sloj radi semantičke interoperabilnosti.
1.1 Ciljevi istraživanja
Istraživanje ima četiri cilja:
1. opisati arhitekturu sistema i međusobne zavisnosti njegovih podsistema;
2. dokumentovati metodološke odluke svake od devet faza analitičkog toka obrade;
3. prikazati model podataka koji koordiniše asinhronim tokom izvršavanja;
4. evaluirati sistem na dostupnom skupu podataka kroz strukturnu, pedagošku i operativnu validaciju.
1.2 Organizacija rada
Rad je organizovan na sledeći način. U odeljku 2 daju se teorijske osnove teorije prostora znanja, algoritma induktivne analize stabla stavki, mreža za uklanjanje šuma i semantičkog veba. Odeljak 3 opisuje arhitekturu sistema, odeljak 4 primenjene tehnologije, a odeljak 5 model podataka. Odeljci 6, 7 i 8 dokumentuju implementaciju triju podsistema. Odeljak 9 prikazuje rezultate evaluacije, odeljak 10 diskusiju, a odeljak 11 zaključuje rad.
 
2. Teorijske osnove
2.1 Teorija prostora znanja
Teoriju prostora znanja formulisali su Doignon i Falmagne (1985) kao matematički okvir za modeliranje domena znanja. Neka je Q konačan skup obrazovnih stavki. Prostor znanja (Q, K) definiše se kao kolekcija K ⊆ 2^Q dostiživih stanja znanja, zatvorena na presecima:
∀K₁, K₂ ∈ K : K₁ ∩ K₂ ∈ K
Svako stanje K ∈ K predstavlja skup stavki koje student može tačno da reši. Praktična vrednost modela ogleda se u definisanju nastavne putanje — minimalnog niza koraka kojim se student vodi od praznog stanja do ciljnog — što omogućava efikasno personalizovano poučavanje (Falmagne et al., 2013).
2.2 Algoritam induktivne analize stabla stavki
Algoritam induktivne analize stabla stavki (IITA, eng. Inductive Item Tree Analysis) razvili su Dowling (1993) i Schrepp (2003) kao metod za automatsku ekstrakciju relacija preduslova iz empirijskih matrica odgovora. Centralna veličina algoritma je matrica suprotnih primera B:
Bᵢⱼ = |{s ∈ S : rₛᵢ = 1 i rₛⱼ = 0}|
gde rₛᵢ označava tačnost odgovora studenta s na stavku i. Vrednost Bᵢⱼ broji suprotne primere za implikaciju i ⇒ j — studente koji su tačno odgovorili na stavku i, ali ne i na j. Implikacija se prihvata ako relativna učestalost suprotnih primera padne ispod praga θ:
Bᵢⱼ / |S| < θ
Tokom razvoja sistema, algoritam je najpre primenjen direktno na sirovim podacima. Eksperiment je pokazao da algoritam daje pouzdane rezultate dok god je udeo nedostajućih vrednosti ispod 20%. Kada taj udeo prelazi navedeni prag — što je u analiziranom skupu slučaj za oko 59% vrednosti — matrica suprotnih primera postaje nestabilna: parovi studenata sa oba nedostajuća odgovora sistematski potcenjuju broj suprotnih primera, što dovodi do lažno gustih grafova sa pogrešnim implikacijama. Ovaj empirijski nalaz bio je ključni motivator za uvođenje faze popunjavanja podataka kao obaveznog prvog koraka i za primenu algoritma na agregiranom nivou koncepta, a ne na nivou individualnih stavki.
2.3 Mreža za uklanjanje šuma
Mreža za uklanjanje šuma, poznata u literaturi i kao odšumljujući autoenkoder (DAE, eng. Denoising Autoencoder), opisana je u radu Vincenta i sar. (2008, 2010) kao neuronska mreža koja se uči da rekonstruiše čist ulaz x iz veštački oštećenog ulaza x̃, generisanog stohastičkim maskiranjem elemenata:
x̃ = x ⊙ m,  mᵢ ~ Bernoulli(1 − p)
Funkcija gubitka računa se isključivo nad opserviranim vrednostima:
L = (1/|Ω|) Σᵢ∈Ω (xᵢ − x̂ᵢ)²
gde Ω označava skup indeksa za koje je odgovor dostupan. Ovaj pristup obezbeđuje da mreža uči strukturu korelacija između stavki i studentskih postignuća, a ne puku distribuciju opservovanih vrednosti. Rekonstrukcija se binarizuje pragom 0,5, čime se dobija popunjena binarna matrica pogodna za dalju algoritamsku obradu.
2.4 Semantička klasifikacija stavki
Efikasna primena teorije prostora znanja na domene sa velikim brojem stavki zahteva njihovo prethodno grupisanje u semantički koherentne koncepte. Reimers i Gurevych (2019) predložili su arhitekturu koja, koristeći sijamske BERT mreže, generiše vektorske prikaze rečenica pogodne za poređenje kosinusnom merom sličnosti. Nad dobijenim vektorima primenjuje se hijerarhijsko grupisanje Ward-ovom metodom (Ward, 1963): jedinstven parametar — prag rastojanja — određuje broj grupa bez ručnog podešavanja, što sistem čini primenljivim na nove domene bez intervencije stručnjaka.
2.5 Semantički veb i obrazovne ontologije
Projekat Savremenih obrazovnih tehnologija i standarda (SOTIS) promoviše upotrebu ontologija zasnovanih na jeziku za opis veb-ontologija (OWL, eng. Web Ontology Language) za razmenu znanja između heterogenih obrazovnih sistema (Horvat et al., 2012). OWL i okvir za opis resursa (RDF, eng. Resource Description Framework) — standardi konzorcijuma W3C — omogućavaju mašinski čitljivo opisivanje obrazovnih sadržaja, relacija preduslova i nastavnih putanja, čineći ih interoperabilnim između različitih platformi. Sistem opisan u ovom radu generiše SOTIS-kompatibilnu ontologiju kao završni rezultat analitičkog toka obrade, čime model znanja postaje semantički dostupan izvan konteksta same platforme.
 
3. Arhitektura sistema
Sistem se sastoji od triju logički razdvojenih celina objedinjenih u višekontejnersku primenu zasnovanu na orkestratoru za upravljanje kontejnerima: korisničkog interfejsa, pozadinskog servera i analitičkog radnog procesa, uz bazu podataka i posrednički sloj za razmenu poruka. Ovakva arhitektura obezbeđuje jasnu razdvojenost odgovornosti — vremenski zahtevna analitička obrada odvija se nezavisno od korisničkih zahteva.


 
Slika 1. Visokorazredna arhitektura sistema: korisnički interfejs, pozadinski server, analitički radni proces, baza podataka i posrednički sloj za razmenu poruka.
Primarni tok obrade zasnovan je na asinhronom modelu. Korisnik učitava matricu odgovora i opciono dokument sa opisima stavki. Pozadinski server prima zahtev, kreira odgovarajuće zapise u bazi i delegira analitički zadatak radnom procesu. Korisnički interfejs periodično proverava status i prikazuje napredak u realnom vremenu. Po završetku, svi generisani rezultati dostupni su za pregled i preuzimanje.
 
4. Primenjene tehnologije
Odabir tehnološkog skupa zasnovan je na kriterijumima produkcione zrelosti, permisivnih licenci i mogućnosti kontejnerizacije. Tabele 1, 2 i 3 daju pregled ključnih tehnologija po podsistemima.
Tehnologija	Uloga u sistemu
Python 3.11+	Osnovno izvršno okruženje
FastAPI 0.109	REST API okvir sa automatskom dokumentacijom
SQLAlchemy 2.0	Objektno-relaciono preslikavanje
Celery 5.3	Asinhrono izvršavanje zadataka
Redis	Posrednički sloj za razmenu poruka
PostgreSQL 15	Relaciona baza podataka
Pydantic 2.x	Provera valjanosti i serijalizacija podataka
Tabela 1. Tehnologije pozadinskog servera.

Biblioteka	Namena
PyTorch 2.4 (CPU)	Mreža za uklanjanje šuma
sentence-transformers	Vektorski prikazi rečenica
scikit-learn	Hijerarhijsko grupisanje
networkx	Analiza i operacije nad grafovima
pandas / numpy	Manipulacija i numerička obrada podataka
rdflib 7.0	Izgradnja i serijalizacija OWL ontologije
Tabela 2. Biblioteke analitičkog toka obrade.

Tehnologija	Uloga
React 19 + TypeScript 5.9	Komponentni razvoj sa statičkom tipizacijom
Material-UI 5.14	Gotove komponente korisničkog interfejsa
React Flow 12.3	Interaktivna vizualizacija grafova
elkjs 0.11	Slojeviti raspored čvorova grafa
Nginx	Statički server i obrnuti posrednik
Tabela 3. Tehnologije korisničkog interfejsa.
5. Model podataka
Relaciona shema obuhvata tri međusobno povezana entiteta koji prate celokupan životni ciklus analize — od prvog učitavanja datoteke do čuvanja izlaznih rezultata.
Entitet	Ključni atributi	Namena
Učitavanja	id, naziv datoteke, veličina, broj redova i kolona, vreme učitavanja	Metapodaci o ulaznoj matrici odgovora
Zadatak	id, stanje (na čekanju / u toku / završeno / neuspešno), napredak (0–100%), poruka, parametri, vreme	Praćenje životnog ciklusa svake analize
Rezultat	id, broj stavki/koncepta/studenata/stanja/preduslova, prostor znanja (JSON)	Kvantitativni pokazatelji i sačuvani model znanja
Tabela 4. Relaciona shema sistema.
Entitet Zadatka prati stanje analize kroz četiri moguća statusa. Atributi napretka i tekuće poruke ažuriraju se tokom izvršavanja i prikazuju se u realnom vremenu unutar korisničkog interfejsa. Parametri se čuvaju u strukturiranom obliku, što garantuje ponovljivost svake analize.
 
6. Analitički tok obrade
Analitički tok obrade organizovan je kao sekvencijalni niz od devet uzastopnih faza u kojima svaka faza prima strukturirani izlaz prethodne i predaje rezultat sledećoj. Slika 2 prikazuje celokupan tok sa svim fazama, a u nastavku su opisane sve faze s naglaskom na obrazloženje metodoloških odluka.

 
Slika 2. Devet uzastopnih faza analitičkog toka obrade, od učitavanja sirovih podataka do generisanja OWL ontologije.
6.1 Popunjavanje podataka i uklanjanje šuma
Udeo nedostajućih vrednosti u ulaznoj matrici iznosi oko 59%, što znači da je samo oko 41% odgovora na nivou individualnih stavki poznato. Takva gustina podataka direktno onemogućava pouzdanu primenu algoritma na sirovim podacima (videti odeljak 2.2). Kao odgovor, prva faza obučava autoenkodersku mrežu za uklanjanje šuma na dostupnim podacima, s ciljem učenja latentnih veza između obrazovnih stavki i studentskih postignuća.
Zašto ovaj pristup? Nasuprot jednostavnijim metodama popunjavanja — poput zamene aritmetičkom sredinom — mreža za uklanjanje šuma uči strukturu podataka i popunjava nedostajuće vrednosti konzistentno sa individualnim profilom svakog studenta. Tokom učenja, deo opservovanih vrednosti namerno se prikriva, čime mreža biva primorana da rekonstruiše prikrivene informacije. Rekonstrukcija se binarizuje pragom 0,5.
Efekat kombinovanog delovanja popunjavanja i naknadnog sažimanja na nivo koncepta merljivo je poboljšao gustinu podataka: dok je na nivou individualnih stavki poznato oko 41% odgovora, nakon semantičkog grupisanja i agregacije na koncepte — a pre konačne binarizacije — udeo poznatih vrednosti raste na oko 83,75% (nepoznato ~16,25%). Ovaj skok direktno potvrđuje da kombinovani pristup znatno smanjuje uticaj nepotpunosti podataka na kvalitet ulaza za algoritam za ekstrakciju preduslova.
Ponovljivost se obezbeđuje fiksovanjem slučajnog semena na vrednost 42 i isključivom upotrebom procesorske varijante biblioteke za duboko učenje, čime se garantuju identični rezultati na svim platformama.
6.2 Semantička klasifikacija stavki
Svaka stavka prevodi se u visokorazredni vektorski prostor primenom unapred naučene mreže za semantičke prikaze rečenica. Semantička srodnost stavki meri se kosinusnom merom sličnosti između vektora, a hijerarhijsko grupisanje Ward-ovom metodom spaja ih u koherentne tematske celine. Jedinstven parametar — prag rastojanja — određuje broj grupa bez ručnog podešavanja.
6.3 Sažimanje na nivo koncepta
Binarna matrica odgovora sažima se sa nivoa individualnih stavki na nivo semantičkih koncepta. Student se smatra savladavaocem koncepta ako je tačno odgovorio na više od polovine stavki tog koncepta. Rezultat je matrica savladavanja |S| × |C|, gde S označava skup studenata, a C skup identifikovanih koncepta. Ovaj korak smanjuje dimenzionalnost problema i ublažava varijabilnost mernih grešaka.
6.4 Analiza zahtevnosti stavki
Zahtevnost svake stavke definiše se kao proporcija netačnih odgovora. Unutar svakog koncepta, stavke se poredaju od najzahtevnijih prema najmanje zahtevnim, čime se dobija pedagoški redosled pogodan za postepeno uvođenje složenosti.
6.5 Ekstrakcija relacija preduslova
Primena algoritma IITA odvija se nad matricom savladavanja na nivou koncepta. Algoritam prihvata implikaciju i ⇒ j kada relativna učestalost suprotnih primera padne ispod praga θ = 0,05. Nad generisanim skupom implikacija primenjuje se tranzitivna redukcija, kojom se uklanjaju ivice izvedive kompozicijom postojećih relacija. Ciklusi se detektuju i uklanjaju iterativnim postupkom, čime se obezbeđuje struktura usmerenog acikličkog grafa.
6.6 Generisanje prostora stanja znanja
Na osnovu grafa preduslova, pretragom u širinu generiše se skup svih dostižnih stanja znanja, počevši od praznog stanja. Stanje K dostiže se dodavanjem koncepta c stanju K' samo ako su svi preduslovi koncepta c već sadržani u K'.
Kontrola kombinatorne eksplozije ostvaruje se kroz dva mehanizma: uvek se uključuju stanja direktno zabeležena u studentskim podacima, a stanja na putanjama između njih uključuju se samo ako im je kardinalnost ispod gornje granice. Ukupan broj stanja ograničen je gornjom granicom koja osigurava praktičnu primenljivost.
6.7 Vizualizacija, validacija i generisanje ontologije
Generisani graf preduslova vizualizuje se kao statički dijagram. Strukturna validacija proverava konzistentnost grafa: prisustvo korenskih koncepta, odsustvo ciklusa, broj slabo-povezanih komponenti i gustinu ivica. Poslednji korak generiše OWL ontologiju u RDF Turtle formatu, koja sadrži instance koncepta, relacije preduslova i instance stavki.
7. Pozadinski server i REST API
Pozadinski server organizovan je kao monolitna REST aplikacija sa automatski generisanom interaktivnom dokumentacijom. Tabela 5 daje pregled API tačaka koje pokrivaju celokupan životni ciklus analize.
Metoda	Tačka	Opis
POST	/run	Pokretanje analize (učitavanje podataka)
GET	/{id}/status	Praćenje stanja i napretka
GET	/{id}/statistics	Kvantitativni pokazatelji
GET	/{id}/knowledge-space	Prostor znanja u strukturiranom obliku
GET	/{id}/goals	Lista ciljeva učenja (semantički upit)
GET	/{id}/goal-path	Preporučena putanja učenja ka cilju
GET	/{id}/files	Lista generisanih rezultata
GET	/{id}/download/{naziv}	Preuzimanje rezultata
GET	/tasks	Istorija svih analiza
DELETE	/{id}	Brisanje analize i rezultata
Tabela 5. REST API tačke sistema.
Tačke za upravljanje ciljevima učenja i putanjama učenja izvršavaju semantičke upite nad generisanom OWL ontologijom, bez uvođenja zasebnog servera za trojke. Analitički tok izvršava se kao pozadinski zadatak koji direktno poziva analitičke servise, čime se omogućava transparentno prosleđivanje grešaka i ažuriranje napretka u realnom vremenu. Tabela 6 prikazuje mapiranje faza na procentualni napredak.
Faza	Opis	Napredak
1	Priprema podataka	10%
2	Popunjavanje i uklanjanje šuma	15–20%
3	Semantička klasifikacija	25–35%
4	Sažimanje na nivo koncepta	45–50%
5	Analiza zahtevnosti stavki	55–60%
6	Ekstrakcija relacija preduslova	65–70%
7	Generisanje prostora stanja	75–80%
8	Vizualizacija i validacija	85–88%
9	Generisanje ontologije i čuvanje	90–100%
Tabela 6. Mapiranje faza na procentualni napredak zadatka.

 
8. Korisnički interfejs
Korisnički interfejs realizovan je kao veb aplikacija sa linearnim tokom kroz četiri funkcionalne faze: unos podataka, praćenje napretka, pregled rezultata i istorija analiza. Identifikator aktivne analize čuva se lokalno u pregledaču, čime se korisniku omogućava nastavak pregleda i nakon osvežavanja stranice.
8.1 Unos podataka
Korisnik učitava matricu odgovora u CSV formatu i, opciono, dokument sa opisima stavki. Interfejs pruža trenutnu povratnu informaciju o formatu i dimenzijama priloženih podataka.
Slika 3. Ekran za unos podataka: polja za učitavanje matrice odgovora i dokumenta sa opisima stavki.
8.2 Praćenje napretka
Tokom izvršavanja analize, interfejs prikazuje vizuelni pokazatelj napretka sa opisom trenutno aktivne faze i procentom dovršenosti. Ažuriranje se vrši periodičnim upitima pozadinskom serveru.

Slika 4. Ekran za praćenje napretka sa opisom aktivne faze i procentom dovršenosti u realnom vremenu.
8.3 Pregled rezultata
Po završetku analize, korisniku se prikazuje kontrolna tabla sa statističkim pokazateljima, interaktivnim grafom prostora znanja, preporučenim putanjama učenja i listom generisanih rezultata. Slika 5 prikazuje pregled ključnih statističkih pokazatelja i slika 6 interaktivni graf prostora znanja.

Slika 5. Statistički pregled rezultata analize.
Slika 6. Graf prostora znanja sa vizualizacijom relacija preduslova između koncepta.
Graf prostora znanja vizualizuje se kao interaktivni dijagram u kome su čvorovi raspoređeni u slojevima prema dubini u hijerarhiji preduslova. Korisnik može da istražuje čvorove, razvija skupljene klastere i pretražuje koncepte. Slika 7 prikazuje ekran za planiranje putanje učenja dok slika 8 karticu koja prikazuje sve generisane rezultate sa opcijom preuzimanja svake datoteke.
Slika 7. Preporučena putanja učenja ka izabranom cilju sa redosledom koncepta.
Slika 8. Lista generisanih rezultata sa opcijom preuzimanja.
8.4 Istorija analiza
Interfejs pruža pregled svih prethodno pokrenutih analiza sa statusima, vremenima pokretanja, opcijom ponovnog otvaranja rezultata i opcijom brisanja.
Slika 9. Pregled istorije analiza sa statusima i opcijom ponovnog pregleda rezultata.
 
9. Evaluacija sistema
Evaluacija sistema sprovedena je na skupu podataka koji obuhvata 692 studenta i 121 obrazovnu stavku organizovanu u 7 semantičkih koncepta. Ispravnost i upotrebljivost sistema verifikovana je na tri nivoa: strukturnom, semantičko-pedagoškom i operativnom.
9.1 Strukturna validacija
Strukturna validacija proverava matematičku ispravnost generisanog prostora znanja i grafa preduslova. Ključni kvantitativni pokazatelji prikazani su u tabeli 7.
Pokazatelj	Vrednost
Broj studenata	692
Broj stavki	121
Gustina podataka (stavke, pre obrade)	~41%
Gustina podataka (koncepti, posle agregacije)	~83,75% (nepoznato ~16,25%)
Broj koncepta (finalni model)	7
Broj relacija preduslova	5
Broj stanja znanja	44
Broj korenskih koncepta	3
Gustina grafa	0,1190
Tip grafa	Usmereni aciklički graf
Broj slabo-povezanih komponenti	1
Validnih tranzicija (ukupno)	108
Tabela 7. Kvantitativni pokazatelji strukturne validacije.
Svih 108 tranzicija između stanja znanja dodaje tačno jedan koncept i poštuje sve utvrđene relacije preduslova, što potvrđuje punu matematičku konzistentnost prostora znanja. Graf preduslova ima strukturu usmerenog acikličkog grafa sa jednom slabo-povezanom komponentom, što znači da su svi koncepti dostižni iz bar jednog od tri korenskih koncepta.
9.2 Semantičko-pedagoška validacija
Semantička pokrivenost stavki iznosi 99,17%: od 121 stavke, 120 je uspešno grupisano u koncepte, dok jedna stavka ostaje nepovezana zbog razlika u označavanju između teksta stavki i opisa u priloženom dokumentu. Ova stavka ne ugrožava strukturnu ispravnost modela, ali ukazuje na potrebu za ujednačavanjem označavanja u ulaznim podacima.
Pedagoška koherentnost relacija preduslova potvrđena je kvalitativnom analizom generisanog grafa. Sledeći primeri ilustruju semantičku smislenost ekstrahovanih relacija:
– Geradengleichungen und Graphen → Steigung und Parallelität: Razumevanje nagiba i paralelnosti nadovezuje se na sposobnost čitanja i formiranja jednačina pravih i njihovih grafičkih prikaza.
– Geradengleichungen und Graphen → Gleichungen und Umformungen: Rad sa jednačinama pravih oslanja se na stabilne veštine algebarskog preuređivanja i rešavanja linearnih oblika.
– Steigung und Parallelität → Algebra und Terme: Formalizacija relacija nagiba i paralelnosti zahteva pouzdanu manipulaciju terminima i izrazima na apstraktnijem algebarskom nivou.
9.3 Operativna validacija
Operativna validacija proverava stabilan rad sistema od učitavanja ulaznih podataka do isporuke svih izlaznih rezultata. Proverena je prisutnost svih očekivanih izlaznih datoteka, ispravnost redosleda stavki po zahtevnosti unutar svakog koncepta, podudarnost generisanih relacija preduslova sa referentnim skupom koji je ručno definisao nastavnik, te sadržaj ontologije. Komparativna validacija pokazala je visok stepen podudarnosti korenskih koncepta i zadovoljavajuću pokrivenost referentnih relacija.
 
10. Diskusija
10.1 Prednosti predloženog rešenja
Trostepena arhitektura sa asinhronim izvršavanjem donosi nekoliko merljivih prednosti. Radni procesi mogu se horizontalno proširivati nezavisno od pozadinskog servera, a posrednički sloj za razmenu poruka omogućava distribuirano izvršavanje bez izmena u kodu aplikacije. Modularna organizacija podsistema omogućava nezavisno testiranje i zamenu svake celine. Garantovana ponovljivost rezultata naročito je bitna za naučno istraživanje i pedagošku evaluaciju. Ontološka reprezentacija znanja u SOTIS imenskom prostoru otvara mogućnost semantičkih upita i integracije sa sistemima koji podržavaju standarde semantičkog veba.
10.2 Ograničenja
Identifikovana su tri ograničenja relevantna za primenu u novim domenima. Detekcija stavki u ulaznoj matrici oslanja se na konvenciju označavanja kolona specifičnu za strukturu analiziranog nastavnog plana, što zahteva prilagođavanje pri prelasku na drugi domen. Upravljanje promenama relacione sheme realizovano je samo delimično: verzionisane migracione skripte nisu implementirane, što onemogućava bezrizično ažuriranje u produkcijskom okruženju. Konačno, generisanje prostora stanja znanja ima eksponencijalnu teorijsku složenost, a postavljene gornje granice dovoljne su za analizirani skup, ali mogu uzrokovati nepotpunu eksploraciju u domenima sa gušćim grafovima preduslova.
10.3 Pravci budućeg unapređenja
10.3.1 Pedagoška proširivost
Najneposredniji nastavak razvoja sistema je uvođenje prilagodljivog računarskog proveravanja znanja. Na osnovu aktuelno inferisanog stanja znanja studenta, ovakav modul bi birao sledeći zadatak koji pruža maksimalnu dijagnostičku informaciju — direktno transformišući platformu iz analitičkog alata u adaptivni tutorski sistem. Vredan pravac je i podrška za gradacijske odgovore — gde se beleži stepen tačnosti, a ne samo tačno/netačno — što bi omogućilo finiju granulaciju stanja znanja i primenu u domenima sa složenijim sistemima ocenjivanja.
10.3.2 Tehnička robustnost
Uvođenje verzionisanih migracionih skripti za relacionu shemu neophodni je korak pre produkcijske primene. Empirijski utvrđen prag od 20% nedostajućih vrednosti zasad nije formalno kvantifikovan u različitim domenima; sistematična eksperimentalna studija sa kontrolisanim nivoima nepotpunosti podataka pružila bi pouzdanije smernice za podešavanje parametara u novim kontekstima primene. 

Naročito obećavajući pravac bio bi istraživanje alternativnih metoda popunjavanja osim DAE modela. Varijacijski autoenkoderski modeli (VAE, eng. Variational Autoencoder) sa verovatnosnom interpretacijom mogućih vrednosti могли би da pruže fleksibilniju reprezentaciju nedostajućih podataka, posebno u domenama gde je pretpostavka Bernulijeve distribucije prekomplikovana. Još interesantnije, multidimenzionalni modeli teorije odgovora stavke (MIRT, eng. Multidimensional Item Response Theory) direktno modeliraju latentne dimenzije znanja studenata i mogućnost odgovora svake stavke u zavisnosti od te latentne strukture, što bi omogućilo sofisticiraniju obrada nekompletnih odgovora i ekstrakciju preduslova na osnovu neskladalnosti između predviđenog i opaženog performansa.

Za domene sa gustim grafovima preduslova, istraživanje aproksimativnih metoda generisanja prostora stanja moglo bi značajno poboljšati skalabilnost.
10.3.3 Interoperabilnost
Podrška za standardizovane formate razmene obrazovnih podataka — pre svega IMS QTI za uvoz zadataka i xAPI za praćenje napretka — omogućila bi integraciju sa platformama za upravljanje učenjem poput Moodle-a i Canvas-a. Generisana ontologija pruža semantičku osnovu za takvu integrabilnost; neophodni sledeći korak je njeno mapiranje na standardizovane metapodatkovne modele kao što su IEEE LOM ili schema.org rečnik.
 
11. Zaključak
Ovaj rad opisuje projektovanje, implementaciju i evaluaciju platforme za automatizovano generisanje prostora znanja iz empirijskih podataka o studentskim postignućima, zasnovane na teoriji prostora znanja. Predloženi sistem integriše tri komplementarne metode u jedinstven analitički tok: mrežu za uklanjanje šuma za robustno popunjavanje nepotpunih matrica odgovora, semantičku klasifikaciju stavki putem transformerskih modela i algoritam induktivne analize stabla stavki za ekstrakciju relacija preduslova bez ručne ekspertske intervencije.
Evaluacija sprovedena na skupu podataka sa 692 studenta, 121 stavkom i 7 semantičkih koncepta pokazala je da sistem generiše matematički konzistentan prostor znanja od 44 stanja, sa 5 relacija preduslova i punom strukturnom ispravnošću: svih 108 tranzicija poštuje relacije preduslova i dodaje tačno jedan koncept. Semantička pokrivenost stavki iznosi 99,17%, a pedagoška koherentnost relacija potvrđena je kvalitativnom analizom usklađenom sa referentnim nastavnim planom.
Sistem je pozicioniran u okviru projekta SOTIS i generiše OWL ontologiju kompatibilnu sa standardima semantičkog veba. Identifikovana ograničenja — konvencija označavanja kolona specifična za analizirani domen i odsustvo verzionisanih migracionih skripti — transparentno su dokumentovana kao polazišta za budući razvoj. Planirana proširenja — prilagodljivo proveravanje znanja, podrška za gradacijske odgovore i integracija sa standardizovanim formatima obrazovnih podataka — otvaraju jasne pravce evolutivnog razvoja od istraživačke platforme ka operativnoj komponenti savremenih obrazovnih tehnologija.
 
Literatura
Doignon, J. P., i Falmagne, J. C. (1985). Spaces for the assessment of knowledge. International Journal of Man-Machine Studies, 23(2), 175–196. https://doi.org/10.1016/S0020-7373(85)80031-6
Dowling, C. E. (1993). On the irredundant generation of knowledge spaces. Journal of Mathematical Psychology, 37(1), 49–62. https://doi.org/10.1006/jmps.1993.1004
Falmagne, J. C., Albert, D., Doble, C., Eppstein, D., i Hu, X. (2013). Knowledge spaces: Applications in education. Springer.
Horvat, D., Dobša, J., i Divjak, B. (2012). Application of knowledge space theory in an e-learning system. Proceedings of the Central European Conference on Information and Intelligent Systems, 11–18.
Reimers, N., i Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing, 3982–3992. https://doi.org/10.18653/v1/D19-4006
Schrepp, M. (2003). A method for the analysis of hierarchical dependencies between items of a questionnaire. Methods of Psychological Research Online, 19, 43–79.
Vincent, P., Larochelle, H., Bengio, Y., i Manzagol, P. A. (2008). Extracting and composing robust features with denoising autoencoders. Proceedings of the 25th International Conference on Machine Learning, 1096–1103. https://doi.org/10.1145/1390156.1390294
Vincent, P., Larochelle, H., Lajoie, I., Bengio, Y., i Manzagol, P. A. (2010). Stacked denoising autoencoders: Learning useful representations in a deep network with a local denoising criterion. Journal of Machine Learning Research, 11, 3371–3408.
Ward, J. H. (1963). Hierarchical grouping to optimize an objective function. Journal of the American Statistical Association, 58(301), 236–244. https://doi.org/10.1080/01621459.1963.10500845

Napomena: Svi kvantitativni rezultati navedeni u odeljku 9 dobijeni su primenom opisanog sistema na skupu podataka dostupnom u okviru analiziranog obrazovnog konteksta. Slike u odeljku 8 prikazuju stvarni korisnički interfejs implementirane platforme.
