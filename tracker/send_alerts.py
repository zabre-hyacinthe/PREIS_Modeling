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
import csv, datetime as dt, hashlib, html, os, smtplib, ssl, sys
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
                continental=(row.get("include_continental") or "yes").strip().lower() != "no")


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


def build_message(N, p, today, contact):
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
            "La classification est faite par règles et relecteurs IA, <b>non validée par des humains</b> ; le degré de preuve est lu sur le résumé. "
            "Une prédiction isolée ne vaut pas une prédiction confirmée par plusieurs groupes ni par les observations.<br>%s<br>"
            "Pour modifier vos critères ou vous désabonner, répondez à ce message%s. Africa CDC · PREIS.</div></div>" % (
                html.escape(crit), (" ou écrivez à " + html.escape(contact)) if contact else ""))
    lines = ["PREIS-Modeling — %s" % today, ""] + ["- [%s] %s | %s | preuve %s | %s" % (LVL_FR.get(r.priority_level, ""), r.pathogen, r.title, r.evidence_tier, r.url) for r in N.itertuples()] + \
            ["", "Chaque ligne est une publication, pas un foyer ni une recommandation. Classification non validée par des humains.", crit]
    return subject, body, "\n".join(lines)


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
