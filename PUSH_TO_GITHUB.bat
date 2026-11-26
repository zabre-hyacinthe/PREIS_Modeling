@echo off
REM 1) Creez d'abord un depot VIDE sur github.com : zabre-hyacinthe/PREIS_Modeling (sans README). 2) Double-cliquez ce fichier.
cd /d D:\PREIS_MODEL_TRACKER
git init
git add -A
git commit -m "PREIS-Modeling: tracker, alertes conditionnelles, validation historique Ebola 2014-15"
git branch -M main
git remote add origin https://github.com/zabre-hyacinthe/PREIS_Modeling.git
git push -u origin main
echo.
echo Ensuite sur GitHub : Settings ^> Secrets (SMTP_USER, SMTP_PASS, ALERT_FROM, ALERT_RECIPIENTS_CSV) ; NE PAS creer la variable PREIS_ALERTS_LIVE.
echo Actions ^> PREIS Modeling ^> Run workflow : dry_run=true, full_refresh=true.
pause
