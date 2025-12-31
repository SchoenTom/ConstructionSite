"""
Configuration and Constants for German Real Estate Investment Analysis System.

Contains all thresholds, weights, and settings used throughout the application.
All values are based on historical German market analysis and institutional research.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from enum import Enum
import os


class InvestmentRecommendation(Enum):
    """Investment recommendation tiers based on crash probability score."""
    STRONG_BUY = "STRONG_BUY"      # Score 0-19: Blood in the streets moment
    BUY = "BUY"                     # Score 20-39: Early recovery signals
    HOLD = "HOLD"                   # Score 40-59: Fair value, mixed signals
    CAUTION = "CAUTION"             # Score 60-79: Overvaluation emerging
    AVOID = "AVOID"                 # Score 80-100: Severe overvaluation


class PropertyType(Enum):
    """Property types for analysis."""
    WOHNUNG = "Wohnung"             # Apartment
    HAUS = "Haus"                   # House
    MEHRFAMILIENHAUS = "Mehrfamilienhaus"  # Multi-family house
    GEWERBE = "Gewerbe"             # Commercial


class HeatingType(Enum):
    """Heating system types - affects energy efficiency and value."""
    GAS = "Gas"
    OEL = "Öl"
    FERNWAERME = "Fernwärme"
    WAERMEPUMPE = "Wärmepumpe"
    PELLET = "Pellet"
    ELEKTRO = "Elektro"


class EnergyClass(Enum):
    """Energy efficiency classes according to German EnEV."""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"


@dataclass
class CrashModelWeights:
    """
    Weights for the crash probability scoring model.

    Total must equal 100%. Based on empirical analysis of German real estate
    cycles and academic research on housing market indicators.
    """
    valuation_metrics: float = 30.0      # Price-to-income, price-to-rent
    credit_market: float = 25.0          # Mortgage rates, credit volumes
    supply_demand: float = 20.0          # Inventory, construction
    macro_monetary: float = 15.0         # ECB policy, yield curve
    economic_fundamentals: float = 10.0  # GDP, unemployment

    def validate(self) -> bool:
        total = (self.valuation_metrics + self.credit_market +
                 self.supply_demand + self.macro_monetary +
                 self.economic_fundamentals)
        return abs(total - 100.0) < 0.01


@dataclass
class ValuationThresholds:
    """
    Thresholds for valuation metrics.

    Based on historical German market data and Bundesbank analysis.
    """
    # Price-to-Income Ratio
    pir_historical_mean: float = 5.75
    pir_warning: float = 7.5
    pir_crisis: float = 9.0

    # Price-to-Rent Ratio
    prr_historical_mean: float = 22.5
    prr_warning: float = 30.0
    prr_crisis: float = 35.0

    # Real Price Growth (inflation-adjusted)
    real_growth_overheating: float = 8.0  # Percent
    real_growth_years_sustained: int = 3


@dataclass
class CreditMarketThresholds:
    """Thresholds for credit market indicators."""
    # Mortgage rate shock
    rate_shock_critical_bps: int = 200  # 200 basis points YoY increase

    # Credit volume growth
    credit_growth_bubble: float = 15.0  # Percent YoY
    credit_contraction_quarters: int = 2

    # Loan-to-Value
    ltv_risk_threshold: float = 85.0
    ltv_safe_threshold: float = 70.0

    # Debt Service Ratio
    dsr_warning: float = 40.0  # Percent of disposable income


@dataclass
class SupplyDemandThresholds:
    """Thresholds for supply/demand indicators."""
    # Months of supply
    inventory_healthy_min: float = 4.0
    inventory_healthy_max: float = 6.0
    inventory_oversupply: float = 8.0
    inventory_shortage: float = 3.0


@dataclass
class MacroThresholds:
    """Thresholds for macro/monetary indicators."""
    # Yield curve
    yield_curve_inversion: float = 0.0  # Spread in percent

    # ECB inflation target
    ecb_inflation_target: float = 2.0


@dataclass
class FinancialModelDefaults:
    """Default values for financial modeling."""
    # Depreciation
    residential_depreciation_rate: float = 2.0  # Linear depreciation

    # Risk premiums
    real_estate_risk_premium: float = 5.0  # Over risk-free rate

    # Operating expenses
    property_management_fee: float = 3.0  # Percent of rent
    maintenance_reserve: float = 1.0  # Percent of property value per year
    vacancy_rate: float = 3.0  # Percent

    # Capital gains tax
    speculation_period_years: int = 10  # Tax-free after 10 years
    capital_gains_tax_rate: float = 25.0  # Plus Soli

    # Mortgage defaults
    default_ltv: float = 80.0
    default_term_years: int = 20

    # Renovation cost estimates (EUR per sqm)
    renovation_minor: float = 300.0
    renovation_moderate: float = 800.0
    renovation_major: float = 1500.0


@dataclass
class CityData:
    """Data for major German cities."""
    name: str
    state: str
    population: int
    avg_price_sqm: float  # EUR per sqm (2024 estimates)
    avg_rent_sqm: float   # EUR per sqm monthly
    plz_ranges: List[Tuple[str, str]] = field(default_factory=list)


# Comprehensive German cities database with market data (2024 estimates)
GERMAN_CITIES: Dict[str, CityData] = {
    # Top 10 largest cities
    "muenchen": CityData(name="München", state="Bayern", population=1488000, avg_price_sqm=9200.0, avg_rent_sqm=21.0, plz_ranges=[("80331", "81929")]),
    "berlin": CityData(name="Berlin", state="Berlin", population=3645000, avg_price_sqm=5100.0, avg_rent_sqm=13.2, plz_ranges=[("10115", "14199")]),
    "hamburg": CityData(name="Hamburg", state="Hamburg", population=1841000, avg_price_sqm=6100.0, avg_rent_sqm=14.5, plz_ranges=[("20095", "22769")]),
    "frankfurt": CityData(name="Frankfurt am Main", state="Hessen", population=753000, avg_price_sqm=6600.0, avg_rent_sqm=15.8, plz_ranges=[("60306", "60599")]),
    "koeln": CityData(name="Köln", state="Nordrhein-Westfalen", population=1086000, avg_price_sqm=4400.0, avg_rent_sqm=12.8, plz_ranges=[("50667", "51149")]),
    "duesseldorf": CityData(name="Düsseldorf", state="Nordrhein-Westfalen", population=620000, avg_price_sqm=4900.0, avg_rent_sqm=13.2, plz_ranges=[("40210", "40629")]),
    "stuttgart": CityData(name="Stuttgart", state="Baden-Württemberg", population=635000, avg_price_sqm=5600.0, avg_rent_sqm=14.5, plz_ranges=[("70173", "70619")]),
    "leipzig": CityData(name="Leipzig", state="Sachsen", population=597000, avg_price_sqm=3100.0, avg_rent_sqm=9.2, plz_ranges=[("04103", "04357")]),
    "dortmund": CityData(name="Dortmund", state="Nordrhein-Westfalen", population=588000, avg_price_sqm=2700.0, avg_rent_sqm=8.8, plz_ranges=[("44135", "44388")]),
    "nuernberg": CityData(name="Nürnberg", state="Bayern", population=518000, avg_price_sqm=4100.0, avg_rent_sqm=12.0, plz_ranges=[("90402", "90491")]),

    # Additional major cities
    "essen": CityData(name="Essen", state="Nordrhein-Westfalen", population=583000, avg_price_sqm=2600.0, avg_rent_sqm=8.5, plz_ranges=[("45127", "45359")]),
    "bremen": CityData(name="Bremen", state="Bremen", population=567000, avg_price_sqm=3200.0, avg_rent_sqm=10.0, plz_ranges=[("28195", "28779")]),
    "dresden": CityData(name="Dresden", state="Sachsen", population=556000, avg_price_sqm=3400.0, avg_rent_sqm=9.8, plz_ranges=[("01067", "01328")]),
    "hannover": CityData(name="Hannover", state="Niedersachsen", population=536000, avg_price_sqm=3500.0, avg_rent_sqm=10.5, plz_ranges=[("30159", "30659")]),
    "duisburg": CityData(name="Duisburg", state="Nordrhein-Westfalen", population=498000, avg_price_sqm=2200.0, avg_rent_sqm=7.8, plz_ranges=[("47051", "47279")]),
    "bochum": CityData(name="Bochum", state="Nordrhein-Westfalen", population=365000, avg_price_sqm=2500.0, avg_rent_sqm=8.2, plz_ranges=[("44787", "44894")]),
    "wuppertal": CityData(name="Wuppertal", state="Nordrhein-Westfalen", population=355000, avg_price_sqm=2300.0, avg_rent_sqm=7.9, plz_ranges=[("42103", "42399")]),
    "bielefeld": CityData(name="Bielefeld", state="Nordrhein-Westfalen", population=334000, avg_price_sqm=2800.0, avg_rent_sqm=9.0, plz_ranges=[("33602", "33739")]),
    "bonn": CityData(name="Bonn", state="Nordrhein-Westfalen", population=331000, avg_price_sqm=4200.0, avg_rent_sqm=12.5, plz_ranges=[("53111", "53229")]),
    "muenster": CityData(name="Münster", state="Nordrhein-Westfalen", population=317000, avg_price_sqm=4500.0, avg_rent_sqm=13.0, plz_ranges=[("48143", "48167")]),

    # Baden-Württemberg cities
    "karlsruhe": CityData(name="Karlsruhe", state="Baden-Württemberg", population=308000, avg_price_sqm=4000.0, avg_rent_sqm=12.0, plz_ranges=[("76131", "76229")]),
    "mannheim": CityData(name="Mannheim", state="Baden-Württemberg", population=310000, avg_price_sqm=3800.0, avg_rent_sqm=11.5, plz_ranges=[("68159", "68309")]),
    "freiburg": CityData(name="Freiburg im Breisgau", state="Baden-Württemberg", population=230000, avg_price_sqm=5200.0, avg_rent_sqm=14.0, plz_ranges=[("79098", "79117")]),
    "heidelberg": CityData(name="Heidelberg", state="Baden-Württemberg", population=160000, avg_price_sqm=5500.0, avg_rent_sqm=14.5, plz_ranges=[("69115", "69126")]),
    "ulm": CityData(name="Ulm", state="Baden-Württemberg", population=128000, avg_price_sqm=4300.0, avg_rent_sqm=12.5, plz_ranges=[("89073", "89081")]),
    "heilbronn": CityData(name="Heilbronn", state="Baden-Württemberg", population=126000, avg_price_sqm=3600.0, avg_rent_sqm=11.0, plz_ranges=[("74072", "74081")]),
    "pforzheim": CityData(name="Pforzheim", state="Baden-Württemberg", population=125000, avg_price_sqm=3200.0, avg_rent_sqm=10.5, plz_ranges=[("75172", "75181")]),
    "reutlingen": CityData(name="Reutlingen", state="Baden-Württemberg", population=116000, avg_price_sqm=3800.0, avg_rent_sqm=11.5, plz_ranges=[("72760", "72770")]),
    "tuebingen": CityData(name="Tübingen", state="Baden-Württemberg", population=91000, avg_price_sqm=5000.0, avg_rent_sqm=14.0, plz_ranges=[("72070", "72076")]),
    "konstanz": CityData(name="Konstanz", state="Baden-Württemberg", population=85000, avg_price_sqm=5800.0, avg_rent_sqm=15.5, plz_ranges=[("78462", "78467")]),
    "ludwigsburg": CityData(name="Ludwigsburg", state="Baden-Württemberg", population=93000, avg_price_sqm=4500.0, avg_rent_sqm=13.0, plz_ranges=[("71634", "71642")]),
    "esslingen": CityData(name="Esslingen am Neckar", state="Baden-Württemberg", population=94000, avg_price_sqm=4200.0, avg_rent_sqm=12.5, plz_ranges=[("73728", "73734")]),
    "offenburg": CityData(name="Offenburg", state="Baden-Württemberg", population=62000, avg_price_sqm=3500.0, avg_rent_sqm=11.0, plz_ranges=[("77652", "77656")]),
    "friedrichshafen": CityData(name="Friedrichshafen", state="Baden-Württemberg", population=62000, avg_price_sqm=4800.0, avg_rent_sqm=13.5, plz_ranges=[("88045", "88048")]),
    "ravensburg": CityData(name="Ravensburg", state="Baden-Württemberg", population=51000, avg_price_sqm=4500.0, avg_rent_sqm=13.0, plz_ranges=[("88212", "88214")]),
    "villingen_schwenningen": CityData(name="Villingen-Schwenningen", state="Baden-Württemberg", population=86000, avg_price_sqm=3200.0, avg_rent_sqm=10.5, plz_ranges=[("78048", "78056")]),

    # Bayern cities
    "augsburg": CityData(name="Augsburg", state="Bayern", population=296000, avg_price_sqm=4200.0, avg_rent_sqm=12.0, plz_ranges=[("86150", "86199")]),
    "regensburg": CityData(name="Regensburg", state="Bayern", population=153000, avg_price_sqm=4800.0, avg_rent_sqm=13.5, plz_ranges=[("93047", "93059")]),
    "wuerzburg": CityData(name="Würzburg", state="Bayern", population=127000, avg_price_sqm=4500.0, avg_rent_sqm=12.5, plz_ranges=[("97070", "97084")]),
    "ingolstadt": CityData(name="Ingolstadt", state="Bayern", population=138000, avg_price_sqm=4600.0, avg_rent_sqm=13.0, plz_ranges=[("85049", "85057")]),
    "erlangen": CityData(name="Erlangen", state="Bayern", population=113000, avg_price_sqm=4700.0, avg_rent_sqm=13.5, plz_ranges=[("91052", "91058")]),
    "fuerth": CityData(name="Fürth", state="Bayern", population=130000, avg_price_sqm=3800.0, avg_rent_sqm=11.5, plz_ranges=[("90762", "90768")]),
    "passau": CityData(name="Passau", state="Bayern", population=53000, avg_price_sqm=3500.0, avg_rent_sqm=10.5, plz_ranges=[("94032", "94036")]),
    "landshut": CityData(name="Landshut", state="Bayern", population=74000, avg_price_sqm=4300.0, avg_rent_sqm=12.5, plz_ranges=[("84028", "84036")]),
    "rosenheim": CityData(name="Rosenheim", state="Bayern", population=65000, avg_price_sqm=5500.0, avg_rent_sqm=14.5, plz_ranges=[("83022", "83026")]),
    "bamberg": CityData(name="Bamberg", state="Bayern", population=78000, avg_price_sqm=4000.0, avg_rent_sqm=11.5, plz_ranges=[("96047", "96052")]),
    "bayreuth": CityData(name="Bayreuth", state="Bayern", population=75000, avg_price_sqm=3200.0, avg_rent_sqm=9.8, plz_ranges=[("95444", "95448")]),

    # Hessen cities
    "wiesbaden": CityData(name="Wiesbaden", state="Hessen", population=278000, avg_price_sqm=5000.0, avg_rent_sqm=13.5, plz_ranges=[("65183", "65207")]),
    "kassel": CityData(name="Kassel", state="Hessen", population=202000, avg_price_sqm=2800.0, avg_rent_sqm=9.0, plz_ranges=[("34117", "34134")]),
    "darmstadt": CityData(name="Darmstadt", state="Hessen", population=160000, avg_price_sqm=4500.0, avg_rent_sqm=13.0, plz_ranges=[("64283", "64297")]),
    "offenbach": CityData(name="Offenbach am Main", state="Hessen", population=130000, avg_price_sqm=4000.0, avg_rent_sqm=12.0, plz_ranges=[("63065", "63075")]),
    "marburg": CityData(name="Marburg", state="Hessen", population=77000, avg_price_sqm=3800.0, avg_rent_sqm=11.5, plz_ranges=[("35037", "35043")]),
    "giessen": CityData(name="Gießen", state="Hessen", population=90000, avg_price_sqm=3200.0, avg_rent_sqm=10.0, plz_ranges=[("35390", "35398")]),

    # Niedersachsen cities
    "braunschweig": CityData(name="Braunschweig", state="Niedersachsen", population=249000, avg_price_sqm=3200.0, avg_rent_sqm=10.0, plz_ranges=[("38100", "38126")]),
    "oldenburg": CityData(name="Oldenburg", state="Niedersachsen", population=170000, avg_price_sqm=3100.0, avg_rent_sqm=9.8, plz_ranges=[("26121", "26135")]),
    "osnabrueck": CityData(name="Osnabrück", state="Niedersachsen", population=165000, avg_price_sqm=3000.0, avg_rent_sqm=9.5, plz_ranges=[("49074", "49090")]),
    "wolfsburg": CityData(name="Wolfsburg", state="Niedersachsen", population=125000, avg_price_sqm=2800.0, avg_rent_sqm=9.0, plz_ranges=[("38440", "38448")]),
    "goettingen": CityData(name="Göttingen", state="Niedersachsen", population=120000, avg_price_sqm=3500.0, avg_rent_sqm=11.0, plz_ranges=[("37073", "37085")]),
    "lueneburg": CityData(name="Lüneburg", state="Niedersachsen", population=78000, avg_price_sqm=3800.0, avg_rent_sqm=11.5, plz_ranges=[("21335", "21339")]),

    # Rheinland-Pfalz cities
    "mainz": CityData(name="Mainz", state="Rheinland-Pfalz", population=218000, avg_price_sqm=4500.0, avg_rent_sqm=13.0, plz_ranges=[("55116", "55131")]),
    "koblenz": CityData(name="Koblenz", state="Rheinland-Pfalz", population=114000, avg_price_sqm=3200.0, avg_rent_sqm=10.0, plz_ranges=[("56068", "56077")]),
    "trier": CityData(name="Trier", state="Rheinland-Pfalz", population=111000, avg_price_sqm=3500.0, avg_rent_sqm=10.5, plz_ranges=[("54290", "54296")]),
    "kaiserslautern": CityData(name="Kaiserslautern", state="Rheinland-Pfalz", population=100000, avg_price_sqm=2600.0, avg_rent_sqm=8.5, plz_ranges=[("67655", "67663")]),
    "ludwigshafen": CityData(name="Ludwigshafen am Rhein", state="Rheinland-Pfalz", population=172000, avg_price_sqm=3000.0, avg_rent_sqm=9.5, plz_ranges=[("67059", "67071")]),

    # Sachsen cities
    "chemnitz": CityData(name="Chemnitz", state="Sachsen", population=247000, avg_price_sqm=1800.0, avg_rent_sqm=6.5, plz_ranges=[("09111", "09131")]),
    "zwickau": CityData(name="Zwickau", state="Sachsen", population=88000, avg_price_sqm=1500.0, avg_rent_sqm=5.8, plz_ranges=[("08056", "08066")]),

    # Thüringen cities
    "erfurt": CityData(name="Erfurt", state="Thüringen", population=214000, avg_price_sqm=2800.0, avg_rent_sqm=8.5, plz_ranges=[("99084", "99099")]),
    "jena": CityData(name="Jena", state="Thüringen", population=111000, avg_price_sqm=3200.0, avg_rent_sqm=9.5, plz_ranges=[("07743", "07751")]),
    "weimar": CityData(name="Weimar", state="Thüringen", population=65000, avg_price_sqm=2800.0, avg_rent_sqm=8.5, plz_ranges=[("99423", "99428")]),

    # Sachsen-Anhalt cities
    "magdeburg": CityData(name="Magdeburg", state="Sachsen-Anhalt", population=238000, avg_price_sqm=2200.0, avg_rent_sqm=7.5, plz_ranges=[("39104", "39130")]),
    "halle": CityData(name="Halle (Saale)", state="Sachsen-Anhalt", population=240000, avg_price_sqm=2000.0, avg_rent_sqm=7.0, plz_ranges=[("06108", "06132")]),

    # Brandenburg cities
    "potsdam": CityData(name="Potsdam", state="Brandenburg", population=183000, avg_price_sqm=4500.0, avg_rent_sqm=12.5, plz_ranges=[("14467", "14482")]),
    "cottbus": CityData(name="Cottbus", state="Brandenburg", population=100000, avg_price_sqm=1800.0, avg_rent_sqm=6.5, plz_ranges=[("03042", "03055")]),

    # Mecklenburg-Vorpommern cities
    "rostock": CityData(name="Rostock", state="Mecklenburg-Vorpommern", population=209000, avg_price_sqm=3200.0, avg_rent_sqm=9.5, plz_ranges=[("18055", "18147")]),
    "schwerin": CityData(name="Schwerin", state="Mecklenburg-Vorpommern", population=96000, avg_price_sqm=2500.0, avg_rent_sqm=8.0, plz_ranges=[("19053", "19063")]),

    # Schleswig-Holstein cities
    "kiel": CityData(name="Kiel", state="Schleswig-Holstein", population=247000, avg_price_sqm=3500.0, avg_rent_sqm=10.5, plz_ranges=[("24103", "24159")]),
    "luebeck": CityData(name="Lübeck", state="Schleswig-Holstein", population=217000, avg_price_sqm=3800.0, avg_rent_sqm=11.0, plz_ranges=[("23552", "23570")]),
    "flensburg": CityData(name="Flensburg", state="Schleswig-Holstein", population=91000, avg_price_sqm=2800.0, avg_rent_sqm=9.0, plz_ranges=[("24937", "24944")]),

    # Saarland
    "saarbruecken": CityData(name="Saarbrücken", state="Saarland", population=180000, avg_price_sqm=2500.0, avg_rent_sqm=8.5, plz_ranges=[("66111", "66133")]),
}


# PLZ to city mapping (sample - would be expanded with full dataset)
PLZ_CITY_MAPPING: Dict[str, str] = {
    # München
    "80331": "muenchen", "80333": "muenchen", "80335": "muenchen",
    "80336": "muenchen", "80337": "muenchen", "80469": "muenchen",
    "80538": "muenchen", "80539": "muenchen", "80634": "muenchen",
    "80636": "muenchen", "80637": "muenchen", "80638": "muenchen",
    "80639": "muenchen", "80686": "muenchen", "80687": "muenchen",
    "80689": "muenchen", "80796": "muenchen", "80797": "muenchen",
    "80798": "muenchen", "80799": "muenchen", "80801": "muenchen",
    "80802": "muenchen", "80803": "muenchen", "80804": "muenchen",
    "80805": "muenchen", "80807": "muenchen", "80809": "muenchen",
    "80933": "muenchen", "80935": "muenchen", "80937": "muenchen",
    "80939": "muenchen", "80992": "muenchen", "80993": "muenchen",
    "80995": "muenchen", "80997": "muenchen", "80999": "muenchen",
    "81241": "muenchen", "81243": "muenchen", "81245": "muenchen",
    "81247": "muenchen", "81249": "muenchen", "81369": "muenchen",
    "81371": "muenchen", "81373": "muenchen", "81375": "muenchen",
    "81377": "muenchen", "81379": "muenchen", "81475": "muenchen",
    "81476": "muenchen", "81477": "muenchen", "81479": "muenchen",
    "81539": "muenchen", "81541": "muenchen", "81543": "muenchen",
    "81545": "muenchen", "81547": "muenchen", "81549": "muenchen",
    "81667": "muenchen", "81669": "muenchen", "81671": "muenchen",
    "81673": "muenchen", "81675": "muenchen", "81677": "muenchen",
    "81679": "muenchen", "81735": "muenchen", "81737": "muenchen",
    "81739": "muenchen", "81825": "muenchen", "81827": "muenchen",
    "81829": "muenchen", "81925": "muenchen", "81927": "muenchen",
    "81929": "muenchen",

    # Berlin
    "10115": "berlin", "10117": "berlin", "10119": "berlin",
    "10178": "berlin", "10179": "berlin", "10243": "berlin",
    "10245": "berlin", "10247": "berlin", "10249": "berlin",
    "10315": "berlin", "10317": "berlin", "10318": "berlin",
    "10319": "berlin", "10365": "berlin", "10367": "berlin",
    "10369": "berlin", "10405": "berlin", "10407": "berlin",
    "10409": "berlin", "10435": "berlin", "10437": "berlin",
    "10439": "berlin", "10551": "berlin", "10553": "berlin",
    "10555": "berlin", "10557": "berlin", "10559": "berlin",
    "10585": "berlin", "10587": "berlin", "10589": "berlin",
    "10623": "berlin", "10625": "berlin", "10627": "berlin",
    "10629": "berlin", "10707": "berlin", "10709": "berlin",
    "10711": "berlin", "10713": "berlin", "10715": "berlin",
    "10717": "berlin", "10719": "berlin", "10777": "berlin",
    "10779": "berlin", "10781": "berlin", "10783": "berlin",
    "10785": "berlin", "10787": "berlin", "10789": "berlin",
    "10823": "berlin", "10825": "berlin", "10827": "berlin",
    "10829": "berlin", "10961": "berlin", "10963": "berlin",
    "10965": "berlin", "10967": "berlin", "10969": "berlin",
    "10997": "berlin", "10999": "berlin",

    # Hamburg
    "20095": "hamburg", "20097": "hamburg", "20099": "hamburg",
    "20144": "hamburg", "20146": "hamburg", "20148": "hamburg",
    "20149": "hamburg", "20249": "hamburg", "20251": "hamburg",
    "20253": "hamburg", "20255": "hamburg", "20257": "hamburg",
    "20259": "hamburg", "20354": "hamburg", "20355": "hamburg",
    "20357": "hamburg", "20359": "hamburg", "20457": "hamburg",
    "20459": "hamburg", "20535": "hamburg", "20537": "hamburg",
    "20539": "hamburg",

    # Frankfurt
    "60306": "frankfurt", "60308": "frankfurt", "60310": "frankfurt",
    "60311": "frankfurt", "60313": "frankfurt", "60314": "frankfurt",
    "60316": "frankfurt", "60318": "frankfurt", "60320": "frankfurt",
    "60322": "frankfurt", "60323": "frankfurt", "60325": "frankfurt",
    "60326": "frankfurt", "60327": "frankfurt", "60329": "frankfurt",
    "60385": "frankfurt", "60386": "frankfurt", "60388": "frankfurt",
    "60389": "frankfurt", "60431": "frankfurt", "60433": "frankfurt",
    "60435": "frankfurt", "60437": "frankfurt", "60438": "frankfurt",
    "60439": "frankfurt",

    # Köln
    "50667": "koeln", "50668": "koeln", "50670": "koeln",
    "50672": "koeln", "50674": "koeln", "50676": "koeln",
    "50677": "koeln", "50678": "koeln", "50679": "koeln",
    "50733": "koeln", "50735": "koeln", "50737": "koeln",
    "50739": "koeln", "50765": "koeln", "50767": "koeln",
    "50769": "koeln", "50823": "koeln", "50825": "koeln",
    "50827": "koeln", "50829": "koeln", "50858": "koeln",
    "50859": "koeln", "50931": "koeln", "50933": "koeln",
    "50935": "koeln", "50937": "koeln", "50939": "koeln",
    "50968": "koeln", "50969": "koeln",

    # Stuttgart
    "70173": "stuttgart", "70174": "stuttgart", "70176": "stuttgart",
    "70178": "stuttgart", "70180": "stuttgart", "70182": "stuttgart",
    "70184": "stuttgart", "70186": "stuttgart", "70188": "stuttgart",
    "70190": "stuttgart", "70191": "stuttgart", "70192": "stuttgart",
    "70193": "stuttgart", "70195": "stuttgart", "70197": "stuttgart",
    "70199": "stuttgart",

    # Leipzig
    "04103": "leipzig", "04105": "leipzig", "04107": "leipzig",
    "04109": "leipzig", "04129": "leipzig", "04155": "leipzig",
    "04157": "leipzig", "04158": "leipzig", "04159": "leipzig",
    "04177": "leipzig", "04178": "leipzig", "04179": "leipzig",
    "04205": "leipzig", "04207": "leipzig", "04209": "leipzig",
    "04229": "leipzig",
}


@dataclass
class Config:
    """Main configuration class aggregating all settings."""

    # Model weights
    crash_weights: CrashModelWeights = field(default_factory=CrashModelWeights)

    # Thresholds
    valuation: ValuationThresholds = field(default_factory=ValuationThresholds)
    credit: CreditMarketThresholds = field(default_factory=CreditMarketThresholds)
    supply_demand: SupplyDemandThresholds = field(default_factory=SupplyDemandThresholds)
    macro: MacroThresholds = field(default_factory=MacroThresholds)

    # Financial model defaults
    financial: FinancialModelDefaults = field(default_factory=FinancialModelDefaults)

    # API endpoints
    bundesbank_api: str = "https://api.statistiken.bundesbank.de/rest/data"
    destatis_api: str = "https://www-genesis.destatis.de/genesisWS/rest/2020"
    ecb_api: str = "https://data-api.ecb.europa.eu/service/data"

    # Database
    database_path: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data", "database.db"
    ))

    # Recommendation score thresholds
    recommendation_thresholds: Dict[str, Tuple[int, int]] = field(default_factory=lambda: {
        "STRONG_BUY": (0, 19),
        "BUY": (20, 39),
        "HOLD": (40, 59),
        "CAUTION": (60, 79),
        "AVOID": (80, 100),
    })

    def get_recommendation(self, score: float) -> InvestmentRecommendation:
        """Convert crash probability score to investment recommendation."""
        for rec, (low, high) in self.recommendation_thresholds.items():
            if low <= score <= high:
                return InvestmentRecommendation[rec]
        return InvestmentRecommendation.HOLD

    def get_city_by_plz(self, plz: str) -> str:
        """Get city key from postal code."""
        return PLZ_CITY_MAPPING.get(plz, "")

    def get_city_data(self, city_key: str) -> CityData:
        """Get city data by key."""
        return GERMAN_CITIES.get(city_key)

    @property
    def all_cities(self) -> Dict[str, CityData]:
        """Return all city data."""
        return GERMAN_CITIES


# Global config instance
config = Config()
