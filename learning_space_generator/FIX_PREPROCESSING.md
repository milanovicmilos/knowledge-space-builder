# KRITIČNA GREŠKA U PREPROCESSING-u

## Problem

Trenutni kod tretira **missing data** (9999, 666) kao **netačne odgovore** (0):

```python
# preprocessing_service.py, linija 41
data.replace({9999: 0, 666: 0}, inplace=True)  # ❌ POGREŠNO!
```

## Posledice

- **57.5%** podataka je 9999 (učenik nije radio to pitanje)
- **1.5%** podataka je 666 (invalid response)
- **Ukupno 60% podataka je MISSING**
- Trenutno se tretiraju kao NETAČNI odgovori
- DAE uči lažne negativne šablone
- IITA gradi implikacije na korumpiranim podacima
- 11 od 23 koncepta nedostaje jer izgledaju kao "niko ih ne zna" (u stvari, niko ih nije ni radio)

## Statistika po studentu

```
Student 1: 55/121 pitanja (45% coverage)
Student 2: 32/121 pitanja (26% coverage)  
Student 3: 50/121 pitanja (41% coverage)
Prosek: ~42% pitanja po studentu
```

**Nijedan student nije radio sva pitanja!**

## Rešenje 1: DAE sa NaN vrednostima (komplikovano)

```python
# U load_data()
data.replace({9999: np.nan, 666: np.nan}, inplace=True)

# Modificiraj DAE da koristi mask za missing values
mask = ~data.isna()
loss = criterion(output * mask, target * mask)  # Samo observed values
```

**Problemi:**
- Komplikovanije
- DAE može imati probleme sa sparse data
- Nije jasno da li DAE pomaže KST konstrukciji

## Rešenje 2: Preskočiti DAE (preporučeno) ✅

**Zašto je ovo bolje:**
- IITA radi sa **binarnim implikacijama** (A → B)
- Ne treba mu kontinuirano denoise-ovanje
- Implikacije se računaju samo na **observovanim parovima odgovora**
- Missing data se prirodno ignoriše

**Implementacija:**

```python
def load_data_without_dae(filepath: str):
    """
    Load data and handle missing values properly for IITA.
    """
    df = pd.read_csv(filepath, sep=';', encoding='utf-8')
    item_cols = [col for col in df.columns 
                 if col.startswith('s') and col.lower() != 'standort']
    
    data = df[item_cols].copy()
    
    # Replace missing codes with NaN (NOT 0!)
    data.replace({9999: np.nan, 666: np.nan}, inplace=True)
    
    # For aggregation: treat NaN as "not answered" 
    # For IITA: only count pairs where BOTH items are observed
    
    return data, item_cols

def compute_iita_with_missing(data: pd.DataFrame):
    """
    Compute IITA implications handling missing data properly.
    
    For implication A → B:
    - Only count students who answered BOTH A and B
    - Counter-example: student has A but NOT B (NotA ∧ B)
    """
    n_items = data.shape[1]
    B_matrix = np.zeros((n_items, n_items))
    
    for i in range(n_items):
        for j in range(n_items):
            if i == j:
                continue
            
            # Get responses for both items
            item_i = data.iloc[:, i]
            item_j = data.iloc[:, j]
            
            # Only consider students who answered BOTH
            valid_mask = item_i.notna() & item_j.notna()
            
            if valid_mask.sum() < 10:  # Minimum sample size
                continue
            
            # Count: has i but NOT j (counter-example for i → j)
            has_i = item_i[valid_mask] == 1
            not_has_j = item_j[valid_mask] == 0
            counter_examples = (has_i & not_has_j).sum()
            
            # Total who could be counter-examples
            total_pairs = valid_mask.sum()
            
            B_matrix[i, j] = counter_examples / total_pairs if total_pairs > 0 else 0
    
    return B_matrix
```

## Šta uraditi

1. **Odmah:**
   - Ispravi preprocessing da tretira 9999/666 kao NaN
   - Reruna pipeline bez DAE-a ili sa pravilnim tretmanom missing data

2. **Očekivani rezultat:**
   - Više koncepata će biti prisutni u knowledge space
   - Implikacije će biti bazirane na stvarnim odgovorima
   - Knowledge space će imati validne putanje do punog znanja

3. **Testiranje:**
   - Proveri da li svih 23 koncepta dobija validnu frekv enciju
   - Proveri da li implications.json ima više veza
   - Proveri da li knowledge_space.json ima putanju do stanja sa svih 23 koncepta

## Pitanje za tebe

**Da li želiš:**
- **A)** Potpuno ukloniti DAE i raditi direktno sa original data (NaN za 9999/666)?
- **B)** Zadržati DAE ali ga ispraviti da pravilno rukuje sa missing values?

**Moja preporuka: Opcija A** jer IITA ne treba denoising za binarne implikacije.
