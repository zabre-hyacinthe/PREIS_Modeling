import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tracker"))
import rules as R
g = R.geo("Modelling cholera in Niger and Nigeria", "")
assert g["countries_iso3"] == "NER|NGA", g
assert R.geo("Sudan and South Sudan", "")["countries_iso3"] == "SDN|SSD"
assert R.geo("Guinea-Bissau", "")["countries_iso3"] == "GNB"
assert R.geo("Papua New Guinea study", "")["countries_iso3"] == ""
assert R.geo("Global burden of gout 1990-2021", "")["africa_relevance"] == "Hors Afrique / non précisé"
assert R.geo("SEIR model of Ebola in DRC", "")["countries_iso3"] == "COD"
assert R.model_class("A SEIR model of measles", "")["model_class_v2"].startswith("Compartimental")
assert R.model_class("Forecasting cholera with ARIMA", "")["model_class_v2"].startswith("Séries")
assert R.model_class("Prevalence of anaemia", "cross-sectional survey")["model_class_v2"] == "Non classé"
assert R.pathogen("Global burden of colorectal cancer", "")["domain_v2"].startswith("Hors périmètre")
assert R.pathogen("Cancer in people with HIV", "")["pathogen_v2"] == "VIH/sida"
assert R.pathogen("Ebola vaccination model", "")["priority_pathogen"] is True
assert R.target_year("", "We project burden by 2050.", 2025)["target_year_v2"] == 2050
assert R.target_year("", "Emergence during 1470-1911", 2025)["target_year_v2"] == ""
print("tests rules OK")

# --- v3 : preuve
from rules import evidence_tier
assert evidence_tier("Forecasting cholera", "We forecast cases; external validation against observed data with prediction intervals; code on GitHub", True)["evidence_tier"] == "T4"
assert evidence_tier("SEIR model of mpox", "cross-validation was used", True)["evidence_tier"] == "T3"
assert evidence_tier("SEIR model of mpox", "We simulate scenarios", True)["evidence_tier"] == "T2"
assert evidence_tier("A systematic review of models", "x", False)["evidence_tier"] == "T1"
print("tests evidence_tier OK")
