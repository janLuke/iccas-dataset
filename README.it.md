# Casi Italiani di Coronavirus per fascia d'età e sesso

[![Update data](https://github.com/janLuke/iccas-dataset/workflows/Update%20data/badge.svg)](https://github.com/janLuke/iccas-dataset/actions)

_[Read it in English (Leggilo in Inglese)](README.md)_.

Questa repository contiene dataset sul numero di casi italiani di Coronavirus 
(e morti per/con Coronavirus) disaggregati per fascia d'età e sesso. 
ICCAS è l'acronimo del nome inglese del dataset (*"Italian Coronavirus Cases by 
Age group and Sex"*).

I dati sono estratti (automaticamente) dai "documenti estesi" in formato pdf 
(come [questo](https://www.epicentro.iss.it/coronavirus/bollettino/Bollettino-sorveglianza-integrata-COVID-19_30-marzo-2020.pdf)) 
pubblicati dall'Istituto Superiore di Sanità (ISS). Un link al report più recente 
può essere trovato a [questa pagina](https://www.epicentro.iss.it/coronavirus/sars-cov-2-sorveglianza-dati)
alla sezione "Documento esteso".

I documenti estesi erano originariamente pubblicati due volte a settimana e sono
adesso pubblicati una volta a settimana.

Questa repository è aggiornata automaticamente da un [workflow di GitHub](.github/workflows/update-data.yaml) 
che viene eseguito regolarmente (si veda il workflow stesso per maggiori dettagli).


## Aggiornamenti

- **2020/10/07:** 
    - la colonna `date` include adesso anche l'ora (formato ISO, `yyyy-mm-ddThh:mm`).
    - la colonna `date` è adesso presente anche nei dataset per data (`by-date`);
      ovviamente, in tali dataset, la colonna `date` contiene un unico valore replicato.


## Struttura della cartella `data`
```
data
├── by-date                     
│   └── iccas_{data}.csv   Dataset con dati aggiornati a giorno {data}
├── util       
│   ├── italian_population_by_age_2020.csv
│   │                      Numero di italiani per età (0, 1, ..., 99, >=100) [1]
│   └── italian_population_by_age_group_2020.csv
│                          Numero di italiani per fascia d'età (0-9, ..., 80-89, >=90) [1]
└── iccas_full.csv         Concatenazione di tutti i dataset iccas_{data}.csv
```

[1] Fonte: [ISTAT](https://www.istat.it/it/popolazione-e-famiglie?dati).


## Descrizione del dataset

Tutti i campi numerici sono relativi ai primi due campi in tabella:
la data e la fascia d'età.

Nella seguente tabella, `{sex}` (sesso) può essere `male` (maschio) o `female` 
(femmina). Per esempio, la voce `{sex}_cases` indica che nel dataset ci sono due
colonne: `male_cases` e `female_cases`.

| Colonna                   | Descrizione                                                                                  |
|---------------------------|----------------------------------------------------------------------------------------------|
| `date`                    | Data e ora locale italiana in formato ISO-8601 `yyyy-mm-ddThh:mm`                            |
| `age_group`               | Fascia d'età: `"0-9", "10-19", ..., "80-89", ">=90", "unknown"`                              |
| `cases`                   | Numero di casi confermati (inclusi quelli di sesso non noto) dall'inizio della pandemia      |
| `deaths`                  | Numero di morti (inclusi quelli di sesso non noto) dall'inizio della pandemia                |
| `{sex}_cases`             | Numero di casi di un certo sesso ({sex}) dall'inizio della pandemia                          |
| `{sex}_deaths`            | Numero di morti di un certo sesso ({sex}) dall'inizio della pandemia                         |
| `cases_percentage`        | Il campo `cases` in percentuale: `100 * casi_fascia_età / totale_casi`;                      |
| `deaths_percentage`       | Il campo `deaths` in percentuale`: 100 * morti_fascia_di_età / totale_morti`;                |
| `fatality_rate`           | `100 * morti / casi` (Letalità)                                                              |
| `{sex}_cases_percentage`  | `100 * casi_{sesso} / (casi_maschi + casi_femmine)`                                          |
| `{sex}_deaths_percentage` | `100 * morti_{sesso} / (morti_maschi + morti_femmine)`                                       | 
| `{sex}_fatality_rate`     | `100 * morti_{sesso} / casi_{sesso}` (Letalità per i pazienti di un dato sesso)              |

### Dettagli a cui prestare attenzione

- La somma di `male_cases` e `female_cases` **non** dà `cases`, dato che 
  quest'ultimo valore include anche i casi di sesso non noto.
   
- La somma di `male_deaths` e `female_deaths` **non** dà `deaths`, dato che 
  quest'ultimo valore include anche i morti di sesso non noto.

- Nel calcolo di `cases_percentage`, il denominatore (`totale_casi`) include
  i casi di età non nota; nel caso si fosse interessati a una stima della 
  distribuzione di età dei casi, tecnicamente è meglio non includere i casi di 
  età non nota nel denominatore.
  
- Il ragionamento al punto precedente si applica analogamente a `deaths_percentage`. 
