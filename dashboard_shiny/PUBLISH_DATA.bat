@echo off
REM Rafraichit les donnees du tableau de bord Shiny depuis le pipeline.
cd /d D:\PREIS_MODEL_TRACKER
copy /Y hub_export\modeling_register.csv dashboard_shiny\data\
copy /Y data\backtest\backtest_scored.csv dashboard_shiny\data\
copy /Y data\derived\convergence_coverage.csv dashboard_shiny\data\
copy /Y data\alerting\alert_candidates.csv dashboard_shiny\data\
copy /Y data\derived\prisma_flow.csv dashboard_shiny\data\
echo Tester : Rscript -e "shiny::runApp('dashboard_shiny')"
echo Deployer : voir PREIS_AI_CLOUD\deploy_config (rsconnect::deployApp, compte shinyapps.io). Paquets requis : shiny shinydashboard dplyr readr tidyr stringr ggplot2 DT leaflet sf htmltools scales
pause
