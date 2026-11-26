"""Export du tracker de modelisation au contrat HUB (14 colonnes). Lecture seule de results/model_tracker_v3.csv."""
import pandas as pd, datetime as dt, sys
COLS=["module","source","report_id","report_date","geo_level","geo_name","geo_code","indicator","value","value_type","signal_level","provisional","source_url","extracted_at"]
T=pd.read_csv("results/model_tracker_v3.csv"); S=T[T.core_africa_scope].copy()
now=dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); rows=[]
for (y,c),g in S.groupby(["pub_year","model_class_v2"]):
    rows.append(["modeling","PREIS-Modeling (Europe PMC, V10)",f"{int(y)}-{c}",f"{int(y)}-12-31","continent","Afrique","AFR",f"n_modeles_{c}",len(g),"count","info",True,"",now])
for (iso,p),g in S[S.n_countries==1].groupby(["countries_iso3","pathogen_v2"]):
    rows.append(["modeling","PREIS-Modeling (Europe PMC, V10)",f"{iso}-{p}",now[:10],"country",g.countries_name.iloc[0],iso,f"n_modeles_{p}",len(g),"count","info",True,"",now])
for (y,t),g in S.groupby(["pub_year","evidence_tier"]):
    rows.append(["modeling","PREIS-Modeling (Europe PMC, V10)",f"{int(y)}-{t}",f"{int(y)}-12-31","continent","Afrique","AFR",f"n_modeles_preuve_{t}",len(g),"count","info",True,"",now])
pd.DataFrame(rows,columns=COLS).to_csv("hub_export/modeling_preis_series.csv",index=False)
print(len(rows),"lignes ->hub_export/modeling_preis_series.csv")

# Registre lisible (qui / ou / quand / quel modele / quel degre de preuve) pour EOC, revue humaine et publication
REG=["review_status","title","first_author","last_author","author_countries_africa","africa_led","no_african_affiliation","countries_name","geo_scope_v2","pathogen_v2","model_class_v2","method_terms","pub_year","first_pub_date","is_preprint","evidence_tier","transparency_score","evidence_basis","target_year_v2","realization_status","doi","url","journal","cited_by","is_retracted"]
R_=T[T.review_status!="hors périmètre"]
R_[[c for c in REG if c in R_.columns]].sort_values(["pub_year","evidence_tier"],ascending=[False,False]).to_csv("hub_export/modeling_register.csv",index=False,encoding="utf-8-sig")
print("registre ->hub_export/modeling_register.csv",len(R_))
