@echo off
REM PREIS-Modeling : cycle complet (Windows). Prerequis : Python 3 ; aucun paquet a installer sauf pandas.
cd /d %~dp0
python tracker\fetch_europepmc.py --start 2015-01-01
python tracker\build_tracker.py
python tracker\export_hub.py
python tests\test_rules.py
echo Termine. Voir results\quality_report.json et hub_export\modeling_register.csv
pause
