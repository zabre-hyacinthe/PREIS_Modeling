#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PREIS-Modeling : alertes CONDITIONNELLES par public (ministeres, Africa CDC, RCC, partenaires).
Simulation par defaut. Un envoi reel exige : PREIS_DRY_RUN=false ET des destinataires (secret ALERT_RECIPIENTS_CSV) ET un journal existant
(la premiere execution reelle cree un BASELINE : corpus historique marque 'vu', rien n'est envoye).
Destinataires (CSV, jamais committe, colonnes) : email ; name ; audience (africa_cdc|moh|rcc|partner|analyst) ;
  tiers (immediate;weekly;monthly - optionnel) ; min_level (high|medium|low - optionnel) ; countries (liste separee par ; - optionnel) ;
  pathogens (liste separee par ; - optionnel) ; include_continental (yes|no, defaut yes : etudes multi-pays ou 'Afrique').
Regles par defaut selon l'audience : voir DEFAULTS. Journal anti-doublons par (publication, destinataire hache) : aucune adresse n'est stockee.
Variables : PREIS_DRY_RUN, PREIS_TIERS, PREIS_RECIPIENTS_PATH, SMTP_USER, SMTP_PASS, ALERT_FROM, SMTP_HOST, SMTP_PORT, PREIS_CONTACT."""
import csv, datetime as dt, hashlib, html, os, re, smtplib, ssl, sys
from email.message import EmailMessage
import pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(root, "data", "outputs", "alerting", "alert_log.csv")
LVL = {"high": 3, "medium": 2, "low": 1}
LVL_FR = {"high": "Priorité haute", "medium": "Priorité moyenne", "low": "Priorité basse"}
DEFAULTS = {  # audience -> (paliers, niveau minimum)
    "africa_cdc": ("immediate;weekly;monthly", "medium"),
    "rcc": ("immediate;weekly", "medium"),
    "moh": ("immediate;weekly", "medium"),
    "partner": ("weekly;monthly", "medium"),
    "analyst": ("immediate;weekly;monthly", "low"),
}
TIER_FR = {"T4": "validation externe, prospective ou multi-modèles", "T3": "validation interne ou calibration",
           "T2": "modèle sans validation décrite", "T1": "revue, commentaire ou cadre", "T0": "hors modélisation"}
CONTINENTAL = ("afrique", "africa", "")


def _split(x):
    return [s.strip().lower() for s in str(x or "").replace(",", ";").split(";") if s.strip()]


def rcpt_hash(email):
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:10]


def profile(row):
    """Normalise une ligne de destinataires en profil de routage."""
    aud = (row.get("audience") or "analyst").strip().lower()
    d_tiers, d_lvl = DEFAULTS.get(aud, DEFAULTS["analyst"])
    return dict(email=(row.get("email") or "").strip(), name=(row.get("name") or "").strip(), audience=aud,
                tiers=_split(row.get("tiers") or d_tiers), min_level=(row.get("min_level") or d_lvl).strip().lower(),
                countries=_split(row.get("countries")), pathogens=_split(row.get("pathogens")),
                continental=(row.get("include_continental") or "yes").strip().lower() != "no",
                lang=(row.get("language") or "en").strip().lower()[:2])


def route(N, p, run_tiers):
    """Selectionne, pour un profil, les alertes qui le concernent : palier du jour, niveau minimum, maladie, pays."""
    if N.empty:
        return N
    m = N.alert_tier.isin([t for t in p["tiers"] if t in run_tiers]) & (N.priority_level.map(LVL).fillna(0) >= LVL.get(p["min_level"], 2))
    if p["pathogens"]:
        m &= N.pathogen.str.lower().apply(lambda x: any(k in x for k in p["pathogens"]))
    if p["countries"]:
        def hit(c):
            cs = _split(c)
            if not cs or all(x in CONTINENTAL for x in cs):
                return p["continental"]
            return any(x in p["countries"] for x in cs) or (p["continental"] and len(cs) > 3)
        m &= N.countries.apply(hit)
    return N[m].sort_values("priority_score", ascending=False)


def card(r):
    col = "#b42318" if r.priority_level == "high" else "#b54708"
    ctry = r.countries if r.countries else "Afrique (non précisé)"
    return ("<div style='border-left:4px solid %s;padding:8px 12px;margin:10px 0;background:#fafafa'>"
            "<div style='font-size:12px;color:%s;font-weight:bold'>%s &middot; %s</div>"
            "<div style='font-size:15px;margin:2px 0'><a href='%s'>%s</a></div>"
            "<div style='font-size:13px;color:#333'>Pays : %s<br>Modèle : %s &middot; Preuve %s (%s)</div>"
            "<div style='font-size:12px;color:#555;margin-top:4px'><i>Pourquoi cette alerte : %s</i></div></div>") % (
        col, col, LVL_FR.get(r.priority_level, ""), html.escape(r.pathogen), html.escape(r.url), html.escape(r.title), html.escape(ctry),
        html.escape(r.model_class), r.evidence_tier, TIER_FR.get(r.evidence_tier, ""), html.escape(r.signal_detail))


def build_message_fr(N, p, today, contact):
    n_hi = int((N.priority_level == "high").sum())
    paths = ", ".join(list(dict.fromkeys(N.pathogen))[:3])
    subject = "[PREIS-Modeling] %d nouvelle(s) publication(s)%s · %s" % (len(N), (" dont %d priorité haute" % n_hi) if n_hi else "", paths)
    who = ("Bonjour %s," % html.escape(p["name"])) if p["name"] else "Bonjour,"
    scope = []
    if p["countries"]: scope.append("pays : " + ", ".join(p["countries"]))
    if p["pathogens"]: scope.append("maladies : " + ", ".join(p["pathogens"]))
    crit = "Vos critères : audience %s, niveau minimum %s%s." % (p["audience"], LVL_FR.get(p["min_level"], p["min_level"]).lower(), (", " + "; ".join(scope)) if scope else "")
    body = ("<div style='font-family:Arial,sans-serif;max-width:680px'><h3 style='margin:0 0 6px'>PREIS-Modeling — nouvelles publications de modélisation (Afrique)</h3>"
            "<div style='font-size:12px;color:#555'>%s</div><p style='font-size:14px'>%s Voici ce que le suivi a repéré pour vous :</p>" % (today, who)
            + "".join(card(r) for r in N.itertuples()) +
            "<div style='border-top:1px solid #ddd;margin-top:14px;padding-top:8px;font-size:12px;color:#555;line-height:1.5'>"
            "<b>À lire avant d'agir.</b> Chaque ligne est une <b>publication</b>, pas un foyer épidémique ni une recommandation. "
            "La classification est faite par règles lisibles, <b>non validée par des humains</b> ; le degré de preuve est lu sur le résumé. "
            "Une prédiction isolée ne vaut pas une prédiction confirmée par plusieurs groupes ni par les observations.<br>%s<br>"
            "Pour modifier vos critères ou vous désabonner, répondez à ce message%s. Africa CDC · PREIS.</div></div>" % (
                html.escape(crit), (" ou écrivez à " + html.escape(contact)) if contact else ""))
    lines = ["PREIS-Modeling — %s" % today, ""] + ["- [%s] %s | %s | preuve %s | %s" % (LVL_FR.get(r.priority_level, ""), r.pathogen, r.title, r.evidence_tier, r.url) for r in N.itertuples()] + \
            ["", "Chaque ligne est une publication, pas un foyer ni une recommandation. Classification non validée par des humains.", crit]
    return subject, body, "\n".join(lines)

# ---------------------------------------------------------------- English (default) email ----------------------------------------------------------------
LVL_EN = {"high": "High priority", "medium": "Medium priority", "low": "Low priority"}
TIER_EN = {"T4": "external / prospective validation or multi-model", "T3": "internal validation or calibration",
           "T2": "model, no validation described", "T1": "review, commentary or framework", "T0": "not a modelling study"}
PATH_EN = {"VIH/sida": "HIV/AIDS", "Paludisme": "Malaria", "Tuberculose": "Tuberculosis", "Non précisé (infectieux générique)": "Infectious disease (unspecified)",
           "Ebola / filovirus": "Ebola / filovirus", "Hépatites": "Hepatitis", "Schistosomiase": "Schistosomiasis", "Trypanosomiase": "Trypanosomiasis",
           "Choléra": "Cholera", "Grippe": "Influenza", "Fièvre de la vallée du Rift": "Rift Valley fever", "Helminthiases": "Helminthiases", "Rougeole": "Measles",
           "Typhoïde": "Typhoid", "Méningite": "Meningitis", "Leishmaniose": "Leishmaniasis", "Fièvre jaune": "Yellow fever", "Rage": "Rabies", "Peste": "Plague",
           "Résistance antimicrobienne": "Antimicrobial resistance", "Filariose lymphatique": "Lymphatic filariasis", "Coqueluche": "Pertussis", "Fièvre CCHF": "CCHF",
           "VRS": "RSV", "Onchocercose": "Onchocerciasis", "Infections respiratoires": "Respiratory infections", "Diphtérie": "Diphtheria"}
MODEL_EN = {"Compartimental / mécaniste": "Compartmental / mechanistic", "Apprentissage automatique / IA": "Machine learning / AI", "Séries temporelles / prévision": "Time series / forecasting",
            "Simulation / scénarios": "Simulation / scenarios", "Agent / individu-centré": "Agent-based / individual-based", "Économique / décisionnel": "Economic / decision analysis",
            "Spatial / cartographie du risque": "Spatial / risk mapping", "Régression / prédiction statistique": "Regression / statistical prediction",
            "Phylodynamique / génomique": "Phylodynamics / genomics", "Projection de charge / tendances": "Burden / trend projection"}
SIG_EN = {"pathogène prioritaire": "priority pathogen", "épidémie active/surveillée": "active or monitored outbreak", "centré Afrique": "Africa-focused",
          "sortie prédictive": "predictive output", "dirigé depuis l'Afrique": "led from Africa", "aucun critère de transparence": "no transparency criterion reported",
          "mondial incl. Afrique": "global, incl. Africa", "horizon proche": "near-term horizon", "≤90 j": "target within 90 days", "≤30 j": "target within 30 days"}


def _en(d, k):
    return d.get(k, k)


def sig_en(s):
    out = []
    for part in str(s or "").split(";"):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(.*?)(\(\+?\d+\))?$", part)
        base, pts = (m.group(1).strip(), m.group(2) or "") if m else (part, "")
        label = SIG_EN.get(base) or ("evidence " + base.split()[-1] if base.startswith("preuve ") else base)
        out.append((label + " " + pts).strip())
    return "; ".join(out)


GREEN, GOLD, INK = "#1A5632", "#F0B323", "#0F2E1B"
PCOL = {"high": "#B42318", "medium": "#B54708", "low": "#5F6B66"}


def card_en(r):
    col = PCOL.get(r.priority_level, "#5F6B66")
    pth = _en(PATH_EN, r.pathogen)
    ctry = r.countries if r.countries else "Africa (not specified)"
    jr = getattr(r, "journal", "") or ""
    year = (" &middot; %s" % html.escape(jr)) if jr else ""
    led = " &middot; led from Africa" if str(getattr(r, "africa_led", "")).lower() == "true" else ""
    tier = "%s &ndash; %s" % (r.evidence_tier, TIER_EN.get(r.evidence_tier, ""))
    return ("<tr><td style='padding:0 0 12px 0'><table role='presentation' width='100%%' cellpadding='0' cellspacing='0' style='border:1px solid #E1E7E3;border-left:5px solid %s;border-radius:6px;background:#FFFFFF'><tr><td style='padding:12px 14px'>"
            "<div style='font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:%s;font-weight:bold'>%s &nbsp;&middot;&nbsp; %s</div>"
            "<div style='font-size:16px;line-height:1.35;margin:5px 0 8px'><a href='%s' style='color:%s;text-decoration:none;font-weight:bold'>%s</a></div>"
            "<table role='presentation' cellpadding='0' cellspacing='0' style='font-size:13px;color:#33413A;line-height:1.5'>"
            "<tr><td style='padding-right:10px;color:#6B7A72'>Countries</td><td>%s</td></tr>"
            "<tr><td style='padding-right:10px;color:#6B7A72'>Model</td><td>%s</td></tr>"
            "<tr><td style='padding-right:10px;color:#6B7A72'>Evidence</td><td>%s</td></tr>"
            "<tr><td style='padding-right:10px;color:#6B7A72'>Published</td><td>%s%s%s</td></tr></table>"
            "<div style='font-size:12px;color:#5F6B66;margin-top:8px'><i>Why flagged: %s</i></div></td></tr></table></td></tr>") % (
        col, col, LVL_EN.get(r.priority_level, ""), html.escape(pth), html.escape(r.url), GREEN, html.escape(r.title), html.escape(ctry),
        html.escape(_en(MODEL_EN, r.model_class)), tier, html.escape(str(getattr(r, "pub_year", "") or "")), year, led, html.escape(sig_en(r.signal_detail)))


def build_message_en(N, p, today, contact):
    n_hi = int((N.priority_level == "high").sum())
    paths = ", ".join(list(dict.fromkeys(_en(PATH_EN, x) for x in N.pathogen))[:3])
    subject = "[PREIS-Modeling] %d new modelling publication%s%s · %s" % (len(N), "" if len(N) == 1 else "s", (" (%d high priority)" % n_hi) if n_hi else "", paths)
    who = ("Dear %s," % html.escape(p["name"])) if p["name"] else "Hello,"
    scope = []
    if p["countries"]: scope.append("countries: " + ", ".join(p["countries"]))
    if p["pathogens"]: scope.append("diseases: " + ", ".join(p["pathogens"]))
    crit = "Your settings: audience %s, minimum level %s%s." % (p["audience"], LVL_EN.get(p["min_level"], p["min_level"]).lower(), (", " + "; ".join(scope)) if scope else "")
    dash = os.environ.get("PREIS_DASHBOARD_URL", "").strip()
    btn = ("<p style='margin:16px 0 4px'><a href='%s' style='background:%s;color:#FFFFFF;text-decoration:none;padding:10px 18px;border-radius:5px;font-weight:bold;font-size:14px;display:inline-block'>Open the PREIS-Modeling dashboard</a></p>" % (html.escape(dash), GREEN)) if dash.startswith("http") else ""
    body = ("<div style='background:#F3F6F4;padding:16px 0;font-family:Arial,Helvetica,sans-serif'><table role='presentation' width='100%%' cellpadding='0' cellspacing='0'><tr><td align='center'>"
            "<table role='presentation' width='640' cellpadding='0' cellspacing='0' style='max-width:640px;width:100%%'>"
            "<tr><td style='background:%s;padding:16px 18px;border-bottom:4px solid %s;border-radius:6px 6px 0 0'>"
            "<div style='color:#FFFFFF;font-size:19px;font-weight:bold'>PREIS-Modeling</div>"
            "<div style='color:#DCEBE1;font-size:12px;margin-top:2px'>Pan-African Real-time Epidemiological Intelligence System &middot; Africa CDC</div></td></tr>"
            "<tr><td style='background:#FFFFFF;padding:16px 18px'>"
            "<div style='font-size:12px;color:#6B7A72'>%s</div>"
            "<p style='font-size:14px;color:%s;margin:8px 0 4px'>%s here is what the tracker flagged for you: <b>%d new publication%s</b>%s.</p>%s"
            "<table role='presentation' width='100%%' cellpadding='0' cellspacing='0' style='margin-top:12px'>%s</table>"
            "<div style='border-top:1px solid #E1E7E3;margin-top:6px;padding-top:10px;font-size:12px;color:#5F6B66;line-height:1.55'>"
            "<b>Read before acting.</b> Each item is a <b>publication</b>, not an outbreak and not a recommendation. Classification is rule-based and "
            "<b>not yet validated by humans</b>; the evidence level is read from the abstract. A single prediction is not worth a prediction confirmed by several independent groups or by observed data.<br>%s<br>"
            "To change your settings or unsubscribe, reply to this message%s. Africa CDC &middot; PREIS.</div></td></tr></table></td></tr></table></div>") % (
        GREEN, GOLD, today, INK, who, len(N), "" if len(N) == 1 else "s", (", of which <b>%d high priority</b>" % n_hi) if n_hi else "", btn,
        "".join(card_en(r) for r in N.itertuples()), html.escape(crit), (" or write to " + html.escape(contact)) if contact else "")
    lines = ["PREIS-Modeling - %s" % today, ""] + ["- [%s] %s | %s | evidence %s | %s" % (LVL_EN.get(r.priority_level, ""), _en(PATH_EN, r.pathogen), r.title, r.evidence_tier, r.url) for r in N.itertuples()] + \
            ["", "Each item is a publication, not an outbreak or a recommendation. Rule-based classification, not validated by humans.", crit] + (["Dashboard: " + dash] if dash.startswith("http") else [])
    return subject, body, "\n".join(lines)


def build_message(N, p, today, contact):
    """Anglais par defaut ; francais si la colonne optionnelle `language` vaut fr."""
    return (build_message_fr if p.get("lang") == "fr" else build_message_en)(N, p, today, contact)


def main():
    dry = os.environ.get("PREIS_DRY_RUN", "true").lower() != "false"
    run_tiers = [t for t in os.environ.get("PREIS_TIERS", "immediate").split(",") if t]
    contact = os.environ.get("PREIS_CONTACT", "")
    test = os.environ.get("PREIS_TEST_SEND", "false").lower() == "true"   # envoi d'essai : 5 alertes max/destinataire, sans journal ni baseline
    if test: run_tiers = ["immediate", "weekly", "monthly"]
    C = pd.read_csv(os.path.join(root, "data", "alerting", "alert_candidates.csv"), dtype=str, keep_default_na=False)
    C["priority_score"] = C.priority_score.astype(int)
    L = pd.read_csv(LOG, dtype=str, keep_default_na=False) if os.path.exists(LOG) else pd.DataFrame(columns=["record_id", "sent_on", "tier", "rcpt"])
    if "rcpt" not in L.columns: L["rcpt"] = "all"
    first_run = (not os.path.exists(LOG)) and not test
    today = dt.date.today().isoformat()
    outdir = os.path.join(root, "data", "outputs", "alerting", "preview_" + today); os.makedirs(outdir, exist_ok=True)
    if first_run and not dry:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        pd.DataFrame(dict(record_id=C.record_id, sent_on=today, tier="baseline", rcpt="all")).to_csv(LOG, index=False)
        print("BASELINE : %d publications marquees comme deja vues, aucun envoi." % len(C)); return
    base = set(L[L.rcpt == "all"].record_id)
    N = C if test else C[~C.record_id.isin(base)]
    if test:   # essai : uniquement des publications des 12 derniers mois, pour un apercu representatif
        N = N[N.first_pub_date >= (dt.date.today() - dt.timedelta(days=365)).isoformat()]
    rp = os.environ.get("PREIS_RECIPIENTS_PATH", "")
    profs = [profile(r) for r in csv.DictReader(open(rp, encoding="utf-8-sig"))] if rp and os.path.exists(rp) else []
    profs = [p for p in profs if p["email"]]
    print("simulation" if dry else "ENVOI REEL", "| paliers du jour", run_tiers, "| publications non vues :", len(N), "| destinataires :", len(profs), "(adresses jamais affichees)")
    # apercus : un par audience par defaut (sans adresse), pour verifier le routage en simulation
    previews = profs if profs else [profile(dict(email="apercu", audience=a)) for a in DEFAULTS]
    for i, p in enumerate(previews):
        seen = set() if test else set(L[L.rcpt == rcpt_hash(p["email"])].record_id)
        M = route(N[~N.record_id.isin(seen)], p, run_tiers)
        print("  audience %-10s -> %d alerte(s)" % (p["audience"], len(M)))
        if len(M):
            subj, body, _ = build_message(M, p, today, contact)
            open(os.path.join(outdir, "digest_%s_%d.html" % (p["audience"], i)), "w", encoding="utf-8").write("<!-- sujet : %s -->\n%s" % (html.escape(subj), body))
    if dry or not profs:
        print("aucun email envoye (simulation ou pas de destinataires). Apercus :", outdir); return
    sent = []; ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", "465")), context=ctx) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        for p in profs:
            h = rcpt_hash(p["email"]); seen = set() if test else set(L[L.rcpt == h].record_id)
            M = route(N[~N.record_id.isin(seen)], p, run_tiers)
            if test: M = M.sort_values("priority_score", ascending=False).head(5)
            if M.empty: continue
            subj, body, text = build_message(M, p, today, contact)
            if test: subj = "[TEST] " + subj
            m = EmailMessage(); m["Subject"] = subj; m["From"] = os.environ.get("ALERT_FROM", os.environ["SMTP_USER"]); m["To"] = p["email"]
            m.set_content(text); m.add_alternative(body, subtype="html"); s.send_message(m)
            sent.append(pd.DataFrame(dict(record_id=M.record_id, sent_on=today, tier=M.alert_tier, rcpt=h)))
            if test: sent.pop()   # essai : rien dans le journal anti-doublons
    if test:
        print("ENVOI D'ESSAI termine : journal et baseline non modifies"); return
    if sent:
        pd.concat([L] + sent).to_csv(LOG, index=False)
    print("envoi termine : %d destinataire(s) servis, journal mis a jour" % len(sent))


if __name__ == "__main__":
    main()
