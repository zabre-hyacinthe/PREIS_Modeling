import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tracker"))
import fetch_europepmc as F
rec = {"id": "123", "source": "PPR", "doi": "10.1/x", "title": "Forecasting cholera in Nigeria", "abstractText": "We forecast...", "pubYear": "2026", "firstPublicationDate": "2026-03-01",
 "authorList": {"author": [{"fullName": "Doe J", "authorAffiliationDetailsList": {"authorAffiliation": [{"affiliation": "University of Ibadan, Nigeria"}]}},
                          {"fullName": "Roe R", "authorAffiliationDetailsList": {"authorAffiliation": [{"affiliation": "LSHTM, London, UK"}]}}]},
 "pubTypeList": {"pubType": ["Preprint"]}, "citedByCount": 2, "isOpenAccess": "Y"}
d = F.parse_record(rec)
assert d["is_preprint"] and d["africa_first_author"] and not d["africa_last_author"] and d["africa_led"] and not d["no_african_affiliation"], d
d2 = F.parse_record({"id": "9", "source": "MED", "title": "x", "authorString": "A B, C D."}); assert d2["n_authors"] == 2 and d2["no_african_affiliation"] is False
rec3 = dict(rec, authorList={"author": [{"fullName": "A", "authorAffiliationDetailsList": {"authorAffiliation": [{"affiliation": "Oxford, UK"}]}}]}); assert F.parse_record(rec3)["no_african_affiliation"]
qs = F.build_queries("2015-01-01", None); assert all(len(q) < 6000 for q in qs), max(len(q) for q in qs)
print("test fetch/parse OK;", len(qs), "requetes, longueur max", max(len(q) for q in qs))

# regression 27/11/2026 : Europe PMC renvoie parfois null dans les listes (mots-cles, types, affiliations)
_r = {"id": "1", "source": "MED", "title": None, "abstractText": None, "keywordList": {"keyword": ["a", None, "b"]}, "pubTypeList": {"pubType": ["x", None]},
      "authorList": {"author": [{"fullName": "A B", "authorAffiliationDetailsList": {"authorAffiliation": [{"affiliation": None}]}}]}, "grantsList": {"grant": [{"agency": None}]}}
_d = F.parse_record(_r); assert _d["keywords"] == "a|b" and _d["pub_types"] == "x"; print("test valeurs null OK")
