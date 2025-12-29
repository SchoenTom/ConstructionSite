# German Real Estate Investment Analyzer

Ein professionelles Python-basiertes Analysesystem für deutsche Wohnimmobilien-Investments mit institutioneller Qualität.

## Features

### 1. Crash-Wahrscheinlichkeitsmodell
- Multi-Faktor-Scoring (0-100 Skala)
- Bewertungsmetriken (Preis-zu-Einkommen, Preis-zu-Miete)
- Kreditmarkt-Indikatoren
- Angebot/Nachfrage-Analyse
- Makro/Geldpolitik-Bewertung
- Wirtschaftliche Fundamentaldaten

### 2. Regionale Analyse
- Stadtspezifische Marktdaten
- PLZ-basierte Preisschätzungen
- Interaktive Karten
- Städtevergleich

### 3. Finanzmodell (DCF)
- Vollständige Cash-Flow-Modellierung
- NPV, IRR, Equity Multiple
- Deutsche Steuerberechnung (AfA, Spekulationssteuer)
- Szenario-Analyse (Bear/Base/Bull)
- Sensitivitätsanalyse

### 4. Zinsprognose
- Markt-implizite Forward-Rates
- Taylor-Regel-Modell
- Machine Learning Prognose
- Hypothekenzins-Projektion

### 5. Risiko-Analyse
- Monte Carlo Simulation
- Value at Risk (VaR)
- Verlustwahrscheinlichkeit
- Sharpe Ratio

## Installation

```bash
# Repository klonen
git clone <repository-url>
cd ConstructionSite

# Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt
```

## Verwendung

### Dashboard starten
```bash
python main.py
```
Öffnet automatisch das Streamlit-Dashboard im Browser.

### CLI-Modus
```bash
python main.py --cli
```

### Demo ausführen
```bash
python main.py --demo
```

## Projektstruktur

```
ConstructionSite/
├── data/                    # Datenverzeichnisse
│   ├── raw/                 # Rohdaten
│   └── processed/           # Verarbeitete Daten
│
├── src/
│   ├── data_fetchers/       # Datenquellen
│   │   ├── bundesbank.py    # Bundesbank API
│   │   ├── destatis.py      # Statistisches Bundesamt
│   │   ├── ecb.py           # Europäische Zentralbank
│   │   └── market_data.py   # Marktdaten-Aggregator
│   │
│   ├── analytics/           # Analyse-Module
│   │   ├── crash_model.py   # Crash-Wahrscheinlichkeit
│   │   ├── dcf_model.py     # DCF-Finanzmodell
│   │   ├── monte_carlo.py   # Monte Carlo Simulation
│   │   └── rate_forecast.py # Zinsprognose
│   │
│   ├── visualization/       # Visualisierung
│   │   ├── dashboard.py     # Streamlit Dashboard
│   │   ├── charts.py        # Plotly Charts
│   │   └── maps.py          # Folium Karten
│   │
│   └── utils/               # Hilfsfunktionen
│       ├── config.py        # Konfiguration
│       ├── database.py      # Datenbankoperationen
│       └── helpers.py       # Utility-Funktionen
│
├── tests/                   # Unit Tests
├── docs/                    # Dokumentation
├── main.py                  # Einstiegspunkt
├── requirements.txt         # Dependencies
└── README.md               # Diese Datei
```

## Konfiguration

### Städte-Daten
Die wichtigsten deutschen Städte sind in `src/utils/config.py` konfiguriert:
- München, Berlin, Hamburg, Frankfurt
- Köln, Düsseldorf, Stuttgart
- Leipzig, Dortmund, Nürnberg

### PLZ-Mapping
PLZ-zu-Stadt-Zuordnungen ermöglichen standortbasierte Analysen.

### Schwellenwerte
Alle Schwellenwerte für das Crash-Modell sind in `config.py` dokumentiert:
- Preis-zu-Einkommen: Historischer Mittelwert 5.75, Warnung >7.5, Krise >9.0
- Preis-zu-Miete: Historischer Mittelwert 22.5, Warnung >30, Krise >35

## Datenquellen

| Quelle | Daten | Frequenz |
|--------|-------|----------|
| Bundesbank | Zinsen, Kredite | Täglich/Monatlich |
| Destatis | HPI, CPI, Baugenehmigungen | Quartärlich/Monatlich |
| EZB | Leitzinsen, Inflation | Täglich |
| Marktdaten | Preise, Mieten nach Stadt | Täglich (Cache) |

## Disclaimer

Dieses Tool dient ausschließlich zu Informations- und Analysezwecken. Es stellt keine Anlageberatung dar. Alle Investitionsentscheidungen erfolgen auf eigenes Risiko. Die verwendeten Daten können synthetisch oder approximiert sein.

## Lizenz

MIT License - Siehe LICENSE Datei

## Mitwirken

Pull Requests sind willkommen. Für größere Änderungen bitte zuerst ein Issue öffnen.
