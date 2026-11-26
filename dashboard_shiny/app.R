## ============================================================
## PREIS-Modeling — tableau de bord R/Shiny (calque de PREIS AI : shinydashboard, carte leaflet par CCR, 6 langues, filtres)
## Sections = objectifs du projet : 1 inventaire | 2 predictions+preuves | 3 convergence | 4 Afrique | 5 modelisateurs | 6 alertes par public | 7 validation historique (7a) et suivi (7b)
## Lancer : shiny::runApp("D:/PREIS_MODEL_TRACKER/dashboard_shiny")   Donnees : data/ (rafraichies par PUBLISH_DATA.bat)
## Statut : prototype de recherche ; etiquettes par regles et relecteurs IA, NON validees par des humains.
## ============================================================
suppressPackageStartupMessages({
  library(shiny); library(shinydashboard); library(dplyr); library(readr); library(tidyr); library(stringr)
  library(ggplot2); library(DT); library(leaflet); library(sf); library(htmltools); library(scales)
})
options(stringsAsFactors = FALSE); sf::sf_use_s2(FALSE)

app_dir <- if (dir.exists("data")) "." else "D:/PREIS_MODEL_TRACKER/dashboard_shiny"
rd <- function(f) {
  p <- file.path(app_dir, "data", f)
  if (!file.exists(p)) return(data.frame())
  suppressMessages(read_csv(p, col_types = cols(.default = col_character()), na = character(), progress = FALSE))
}
nz <- function(d, cols) { for (nm in cols) if (!nm %in% names(d)) d[[nm]] <- ""; d }

reg <- nz(rd("modeling_register.csv"), c("review_status","title","pathogen_v2","model_class_v2","countries_name","geo_scope_v2","evidence_tier","pub_year","url","realization_status","target_year_v2","first_author","last_author","africa_led","no_african_affiliation","author_countries_africa"))
reg$id <- seq_len(nrow(reg)); reg$year <- suppressWarnings(as.integer(as.numeric(reg$pub_year)))
reg$retained <- grepl("^retenu", reg$review_status)
ref <- nz(rd("country_ref.csv"), c("country","iso3","lat","lon","rcc")); ref$lat <- as.numeric(ref$lat); ref$lon <- as.numeric(ref$lon)
alerts <- nz(rd("alert_candidates.csv"), c("title","pathogen","countries","model_class","evidence_tier","priority_level","alert_tier","signal_detail","url","priority_score"))
alerts$score <- suppressWarnings(as.integer(alerts$priority_score))
bt <- nz(rd("backtest_scored.csv"), c("status","verdict","ratio","country","model_class","group_id","point","observed","horizon_days","record_id"))
bt$ratio <- suppressWarnings(as.numeric(bt$ratio)); bt$horizon_days <- suppressWarnings(as.numeric(bt$horizon_days))
btE <- bt %>% filter(status == "evalue")
cov <- rd("convergence_coverage.csv"); prisma <- rd("prisma_flow.csv")
geo <- tryCatch(sf::st_read(file.path(app_dir, "data", "africa.geojson"), quiet = TRUE), error = function(e) NULL)
data_stamp <- tryCatch(format(max(file.mtime(list.files(file.path(app_dir, "data"), full.names = TRUE))), "%Y-%m-%d %H:%M"), error = function(e) "?")

rcc_colors <- c(Northern = "#E3A008", Western = "#0F9D58", Central = "#8E44AD", Eastern = "#0072B2", Southern = "#B3261E")   # palette identique a PREIS Polio
VCOL <- c("confirmee" = "#1A5632", "partiellement confirmee" = "#F0B323", "infirmee" = "#C0392B")
LVLN <- c(high = 3, medium = 2, low = 1)
LVL_FR <- c(high = "Priorité haute", medium = "Priorité moyenne", low = "Priorité basse")
AUD <- list(africa_cdc = list(t = c("immediate","weekly","monthly"), l = "medium"), moh = list(t = c("immediate","weekly"), l = "medium"),
            rcc = list(t = c("immediate","weekly"), l = "medium"), partner = list(t = c("weekly","monthly"), l = "medium"), analyst = list(t = c("immediate","weekly","monthly"), l = "low"))
CAV  <- "Labels come from rules and AI reviewers and have NOT been validated by humans; one line is a publication, not an outbreak and not a recommendation."
NOTE_DATA <- "Disease and country names come from the data and are not translated."
cho <- function(x) c("All", sort(unique(x[nzchar(x) & !is.na(x)])))

expl <- function(d) {
  if (!nrow(d)) return(data.frame(id = integer(), country1 = character()))
  d %>% mutate(country1 = strsplit(countries_name, ";")) %>% unnest(country1) %>% mutate(country1 = trimws(country1)) %>% filter(country1 != "")
}
th <- theme_minimal(base_size = 13)

ui <- dashboardPage(title = "PREIS-Modeling", skin = "blue",
  dashboardHeader(title = tags$span(style = "font-weight:700;font-size:15px;", "PREIS-Modeling")),
  dashboardSidebar(
    sidebarMenu(
      menuItem("Overview", tabName = "ov", icon = icon("chart-line")),
      menuItem("Inventory", tabName = "inv", icon = icon("table")),
      menuItem("Africa map", tabName = "map", icon = icon("earth-africa")),
      menuItem("Predictions and evidence", tabName = "pred", icon = icon("bullseye")),
      menuItem("Convergence", tabName = "conv", icon = icon("layer-group")),
      menuItem("Africa focus", tabName = "afr", icon = icon("globe-africa")),
      menuItem("Modellers", tabName = "mod", icon = icon("users")),
      menuItem("Alerts by audience", tabName = "alr", icon = icon("bell")),
      menuItem("Search protocol (PRISMA)", tabName = "prot", icon = icon("filter")),
      menuItem("Historical validation", tabName = "bt", icon = icon("scale-balanced")),
      menuItem("Downloads", tabName = "dl", icon = icon("download")),
      menuItem("Methods and limits", tabName = "lim", icon = icon("circle-info"))),
    br(),
    tags$style(HTML(".main-header .logo,.main-header .navbar{background:#1A5632!important;} .main-header .logo:hover{background:#14442A!important;} .main-header .navbar .sidebar-toggle:hover{background:#14442A!important;} .skin-blue .sidebar-menu>li.active>a,.skin-blue .sidebar-menu>li:hover>a{border-left-color:#F0B323!important;} .box.box-primary{border-top-color:#1A5632!important;} .bg-green,.small-box.bg-green{background-color:#1A5632!important;} .bg-yellow,.small-box.bg-yellow{background-color:#F0B323!important;color:#0F2E1B!important;} .box.box-solid.box-primary>.box-header,.box.box-solid.box-success>.box-header{background:#1A5632!important;} .box.box-solid.box-info>.box-header{background:#0F2E1B!important;} .box.box-solid.box-warning>.box-header{background:#F0B323!important;color:#0F2E1B!important;} .content-wrapper a:not(.btn){color:#1A5632;} .btn-default{border-color:#1A5632;color:#1A5632;} .skin-blue .sidebar-menu>li.active>a{background:#0F2E1B!important;}  .nav-tabs-custom>.nav-tabs>li.active{border-top-color:#1A5632!important;} .no-tr label{color:#ddd;font-weight:600;} .no-tr .shiny-options-group{margin-left:10px;} #lang-draft{padding:0 2px 6px 2px;font-size:11px;color:#f0ad4e;} html[lang='ar'] .content-wrapper{direction:rtl;} #map_af{border-radius:8px;border:1px solid #cfd8d3;}")),
    tags$div(class = "no-tr", style = "padding:0 10px;",
      radioButtons("ui_lang", label = NULL, selected = "fr", choices = c("English" = "en", "Fran\u00e7ais" = "fr", "Portugu\u00eas" = "pt", "Espa\u00f1ol" = "es", "\u0627\u0644\u0639\u0631\u0628\u064a\u0629" = "ar", "Kiswahili" = "sw")),
      tags$div(id = "lang-draft")),
    tags$div(style = "padding:0 10px;font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;", "Filters"),
    sliderInput("f_year", "Year", min = min(reg$year, na.rm = TRUE), max = max(reg$year, na.rm = TRUE), value = c(max(min(reg$year, na.rm = TRUE), 2015L), max(reg$year, na.rm = TRUE)), sep = ""),
    selectInput("f_path", "Disease", cho(reg$pathogen_v2), "All"),
    selectInput("f_tier", "Evidence level", cho(reg$evidence_tier), "All"),
    selectInput("f_rcc", "RCC", cho(ref$rcc), "All"),
    selectInput("f_ctry", "Country", cho(ref$country), "All"),
    selectInput("f_scope", "Geographic scope", cho(reg$geo_scope_v2), "All"),
    checkboxInput("f_cand", "Include candidates to review", FALSE)),
  dashboardBody(
    tags$head(tags$script(src = "i18n.js")),
    tabItems(
      tabItem("ov",
        fluidRow(valueBoxOutput("k1", 3), valueBoxOutput("k2", 3), valueBoxOutput("k3", 3), valueBoxOutput("k4", 3)),
        fluidRow(box(width = 6, status = "success", solidHeader = TRUE, title = "Studies by disease", plotOutput("p_path", height = 380)),
                 box(width = 6, status = "primary", solidHeader = TRUE, title = "Evidence level (T0-T4)", plotOutput("p_tier", height = 380))),
        fluidRow(box(width = 6, status = "warning", solidHeader = TRUE, title = "Studies by year", plotOutput("p_year", height = 330)),
                 box(width = 6, status = "warning", solidHeader = TRUE, title = "Studies by model type", plotOutput("p_class", height = 330))),
        tags$p(style = "color:#555", CAV)),
      tabItem("inv", fluidRow(box(width = 12, status = "primary", solidHeader = TRUE, title = "Inventory of retained studies", DTOutput("t_inv"))), tags$p(style = "color:#555", NOTE_DATA)),
      tabItem("map",
        fluidRow(box(width = 12, status = "danger", solidHeader = TRUE, title = "Number of studies per country (African countries)",
          checkboxInput("show_names", "Show country names", TRUE), leafletOutput("map_af", height = "calc(100vh - 230px)"))),
        fluidRow(box(width = 6, status = "danger", solidHeader = TRUE, title = "Studies by RCC", plotOutput("p_rcc", height = 320)),
                 box(width = 6, status = "danger", solidHeader = TRUE, title = "Top countries", plotOutput("p_ctry", height = 320)))),
      tabItem("pred",
        fluidRow(box(width = 7, status = "primary", solidHeader = TRUE, title = "Evidence and verification map", plotOutput("p_evmap", height = 560)),
                 box(width = 5, status = "info", solidHeader = TRUE, title = "Evidence tiers", plotOutput("p_evtier", height = 300),
                     tags$ul(style = "font-size:12px", tags$li("T4: external or prospective validation, or multi-model"), tags$li("T3: internal validation or calibration"), tags$li("T2: model without described validation"), tags$li("T1: review, commentary or framework"), tags$li("T0: outside modelling")),
                     tags$p(style = "font-size:11px;color:#555", "Evidence is read from the abstract only (provisional)."))),
        fluidRow(box(width = 12, status = "info", solidHeader = TRUE, title = "Model type by disease (bubble size = studies, colour = share with evidence T3 or higher)", plotOutput("p_evbub", height = 460))),
        fluidRow(box(width = 12, status = "primary", solidHeader = TRUE, title = "What, where, when, with what evidence",
          tags$p("Predicted values (point, interval) are not yet extracted from the articles: only the study, place, year and evidence level are available."), DTOutput("t_pred"))),
        fluidRow(box(width = 6, status = "warning", solidHeader = TRUE, title = "Realization status of the studies", plotOutput("p_real", height = 300)),
                 box(width = 6, status = "warning", solidHeader = TRUE, title = "Target year", plotOutput("p_target", height = 300)))),
      tabItem("conv",
        fluidRow(box(width = 12, status = "info", solidHeader = TRUE, title = "Study coverage by disease and country", plotOutput("p_heat", height = 460))),
        fluidRow(box(width = 12, status = "primary", solidHeader = TRUE, title = "Coverage state", DTOutput("t_cov"))),
        tags$p(style = "color:#555", "Independent groups and divergence of values cannot yet be assessed: they require authors and predicted values (after the first real Europe PMC fetch).")),
      tabItem("afr",
        fluidRow(valueBoxOutput("a1", 4), valueBoxOutput("a2", 4), valueBoxOutput("a3", 4)),
        fluidRow(box(width = 6, status = "danger", solidHeader = TRUE, title = "Geographic scope of retained studies", plotOutput("p_scope", height = 340)),
                 box(width = 6, status = "danger", solidHeader = TRUE, title = "Who leads the modelling studies on Africa", plotOutput("p_led", height = 340))),
        fluidRow(box(width = 12, status = "warning", solidHeader = TRUE, title = "Leadership by year", plotOutput("p_led_year", height = 300))),
        tags$p(style = "color:#555", "Leadership is read from author affiliations in PubMed (first or last author with an African affiliation); it is descriptive and does not measure the quality of partnerships.")),
      tabItem("mod", fluidRow(box(width = 12, status = "warning", solidHeader = TRUE, title = "Map of modellers",
        tags$p("Countries of African affiliation of the authors of the retained studies (aggregated by country; no named researcher is shown pending a decision on visibility)."),
        leafletOutput("map_mod", height = 480)))),
      tabItem("alr",
        fluidRow(box(width = 12, status = "danger", solidHeader = TRUE, title = "Alerts by audience",
          fluidRow(column(3, selectInput("a_aud", "Audience", c("africa_cdc", "moh", "rcc", "partner", "analyst"), "africa_cdc")),
                   column(3, checkboxGroupInput("a_tier", "Alert tier", c("immediate", "weekly", "monthly"), c("immediate", "weekly", "monthly"), inline = TRUE)),
                   column(3, selectInput("a_lvl", "Minimum priority", c("low", "medium", "high"), "medium")),
                   column(3, selectInput("a_rcc", "RCC", cho(ref$rcc), "All"))),
          fluidRow(column(4, selectInput("a_ctry", "Country", cho(ref$country), "All")), column(4, selectInput("a_path", "Disease", cho(alerts$pathogen), "All"))))),
        fluidRow(box(width = 7, status = "primary", solidHeader = TRUE, title = "Alerts matching these criteria", DTOutput("t_alr")),
                 box(width = 5, status = "warning", solidHeader = TRUE, title = "Preview of the email this audience would receive", uiOutput("mail_prev")))),
      tabItem("prot",
        fluidRow(box(width = 6, status = "primary", solidHeader = TRUE, title = "PRISMA flow (recomputed at each run)", DTOutput("t_prisma")),
                 box(width = 6, status = "info", solidHeader = TRUE, title = "Eligibility criteria",
                     tags$b("Inclusion"), tags$ul(style = "font-size:12px", tags$li("I1: peer-reviewed final publication (PubMed), 2015 to date; preprints excluded"), tags$li("I2: human infectious disease (incl. zoonoses)"), tags$li("I3: African setting (global studies kept in a separate stratum)"), tags$li("I4: quantitative model giving a prediction, projection, forecast, scenario or risk map"), tags$li("I5: abstract in English, French or Portuguese")),
                     tags$b("Exclusion"), tags$ul(style = "font-size:12px", tags$li("E2 retracted; E3 non-infectious; E4 no African setting; E5 no predictive model"), tags$li("E6 commentary, editorial, letter; E7 review (kept apart); E8 duplicate; E9 abstract missing")))),
        tags$p(style = "color:#555", "Single database (Europe PMC / PubMed). Embase, Scopus, Web of Science, reference chasing and grey literature (WHO, Africa CDC, ECDC, hubs) remain to be done. Screening is by explicit rules and AI reviewers; no human validation yet.")),
      tabItem("bt",
        fluidRow(valueBoxOutput("b1", 4), valueBoxOutput("b2", 4), valueBoxOutput("b3", 4)),
        fluidRow(box(width = 12, status = "primary", solidHeader = TRUE, title = "Observed / predicted, Ebola West Africa 2014-15 (1 = exact; below 1 = overestimate)", plotOutput("p_bt", height = 380))),
        fluidRow(box(width = 12, status = "info", solidHeader = TRUE, title = "Details of the 22 forecasts", DTOutput("t_bt"))),
        tags$p("Part 7a - historical test (done once). Part 7b - continuous follow-up of new predictions against observations (starts after the first real fetch)."),
        tags$p(style = "color:#555", "Source: Chretien, Riley, George, eLife 2015;4:e09186, supplementary file 4 (WHO observed). Test case on published forecasts, not an indicator of current reliability.")),
      tabItem("dl", fluidRow(
        box(width = 4, status = "success", solidHeader = TRUE, title = "Filtered studies", downloadButton("dl_reg", "Download CSV")),
        box(width = 4, status = "danger", solidHeader = TRUE, title = "Alerts (current criteria)", downloadButton("dl_alr", "Download CSV")),
        box(width = 4, status = "info", solidHeader = TRUE, title = "Historical validation table", downloadButton("dl_bt", "Download CSV")))),
      tabItem("lim", fluidRow(box(width = 12, status = "warning", solidHeader = TRUE, title = "Methods and limits",
        tags$p(tags$b("Status: research prototype.")), tags$ul(
          tags$li(CAV),
          tags$li("Precision of retained studies about 0.67 and recall about 0.49: provisional estimates, AI labels, to be confirmed by a human panel."),
          tags$li("Historical validation: methods inspired by Funk et al. 2019 and Bracher et al. 2021; verdict thresholds not validated; the 22 forecasts come from a published review (possible selection)."),
          tags$li("Data source: the current 151 retained studies come from an existing corpus (V10 snapshot, 4,998 articles, mostly 2025-2026, collected up to 4 May 2026) filtered by rules. A new full search from 2015 with preprints (Europe PMC) has not been run yet and will widen coverage."),
          tags$li(NOTE_DATA)),
        tags$p(tags$span("Last data load"), tags$span(paste0(": ", data_stamp))))))
    )))

server <- function(input, output, session) {
  fd <- reactive({
    d <- reg
    if (!isTRUE(input$f_cand)) d <- d %>% filter(retained)
    d <- d %>% filter(is.na(year) | (year >= input$f_year[1] & year <= input$f_year[2]))
    if (input$f_path != "All") d <- d %>% filter(pathogen_v2 == input$f_path)
    if (input$f_tier != "All") d <- d %>% filter(evidence_tier == input$f_tier)
    if (input$f_scope != "All") d <- d %>% filter(geo_scope_v2 == input$f_scope)
    if (input$f_ctry != "All") d <- d %>% filter(grepl(input$f_ctry, countries_name, fixed = TRUE))
    if (input$f_rcc != "All") {
      ids <- expl(d) %>% left_join(ref, by = c("country1" = "country")) %>% filter(rcc == input$f_rcc) %>% pull(id)
      d <- d %>% filter(id %in% ids)
    }
    d
  })
  bar <- function(d, col, fill = "#1A5632", n = 12, flip = TRUE) {
    d <- d %>% filter(nzchar(.data[[col]])) %>% count(.data[[col]], sort = TRUE) %>% head(n)
    validate(need(nrow(d) > 0, "-"))
    p <- ggplot(d, aes(reorder(.data[[col]], n), n)) + geom_col(fill = fill) + labs(x = NULL, y = NULL) + th
    if (flip) p + coord_flip() else p
  }
  output$k1 <- renderValueBox(valueBox(nrow(fd()), "Studies retained", icon = icon("book"), color = "green"))
  output$k2 <- renderValueBox(valueBox(sum(fd()$evidence_tier %in% c("T3", "T4")), "Evidence T3 or higher", icon = icon("check"), color = "olive"))
  output$k3 <- renderValueBox(valueBox(n_distinct(expl(fd())$country1), "Countries covered", icon = icon("flag"), color = "yellow"))
  output$k4 <- renderValueBox(valueBox(n_distinct(fd()$pathogen_v2[nzchar(fd()$pathogen_v2)]), "Diseases covered", icon = icon("virus"), color = "orange"))
  output$p_path <- renderPlot(bar(fd(), "pathogen_v2"))
  output$p_tier <- renderPlot(bar(fd(), "evidence_tier", "#263238", flip = FALSE))
  output$p_year <- renderPlot({ d <- fd() %>% filter(!is.na(year)) %>% count(year); validate(need(nrow(d) > 0, "-")); ggplot(d, aes(factor(year), n)) + geom_col(fill = "#F0B323") + labs(x = NULL, y = NULL) + th })
  output$p_class <- renderPlot(bar(fd(), "model_class_v2", "#2980B9", 8))

  output$t_inv <- renderDT({
    d <- fd() %>% mutate(Link = ifelse(nzchar(url), sprintf("<a href='%s' target='_blank'>open</a>", url), "")) %>%
      transmute(Year = year, Disease = pathogen_v2, Countries = countries_name, Model = model_class_v2, Evidence = evidence_tier, Title = title, Link)
    datatable(d, escape = FALSE, rownames = FALSE, options = list(pageLength = 15, scrollX = TRUE))
  })

  cnt <- reactive({ expl(fd()) %>% count(country1, name = "n") })
  output$map_af <- renderLeaflet({
    m <- leaflet(options = leafletOptions(minZoom = 3, maxZoom = 6)) %>% addProviderTiles(providers$OpenStreetMap) %>%
      fitBounds(-25, -38, 60, 40) %>% setMaxBounds(-30, -40, 65, 42)
    if (is.null(geo)) return(m)
    p <- geo
    cn <- cnt(); rr <- ref %>% select(country, rcc_ref = rcc) %>% distinct(country, .keep_all = TRUE)
    df <- data.frame(tname = as.character(p$tname), rcc_geo = as.character(p$rcc), stringsAsFactors = FALSE) %>%
      left_join(rr, by = c("tname" = "country")) %>% left_join(cn, by = c("tname" = "country1"))
    df$rcc_f <- ifelse(!is.na(df$rcc_ref) & nzchar(df$rcc_ref), df$rcc_ref, ifelse(nzchar(df$rcc_geo), df$rcc_geo, "Unspecified"))
    df$n <- ifelse(is.na(df$n), 0L, as.integer(df$n))
    fill <- unname(rcc_colors[df$rcc_f]); fill[is.na(fill)] <- "#9AA0A6"
    pop <- paste0("<b>", df$tname, "</b><br/><b>RCC:</b> ", df$rcc_f, "<br/><b>Studies:</b> ", df$n)
    m <- m %>% addPolygons(data = p, fillColor = fill, fillOpacity = 0.72, color = "#34495E", weight = 1, smoothFactor = 0.2, popup = pop, group = "RCC") %>%
      addLegend(position = "bottomleft", colors = unname(rcc_colors), labels = names(rcc_colors), title = "Africa CDC RCC", opacity = 0.9)
    pts <- df %>% filter(n > 0) %>% left_join(ref %>% select(country, lat, lon) %>% distinct(country, .keep_all = TRUE), by = c("tname" = "country")) %>% filter(!is.na(lat), !is.na(lon))
    if (nrow(pts) > 0) {
      m <- m %>% addCircleMarkers(lng = pts$lon, lat = pts$lat, radius = pmin(26, pmax(8, 4 + 2.2 * sqrt(pts$n))), fillColor = "#263238", fillOpacity = 0.85, color = "#FFFFFF", weight = 1.5,
                                  popup = paste0("<b>", pts$tname, "</b><br/><b>Studies:</b> ", pts$n), label = paste0(pts$tname, ": ", pts$n), group = "Studies")
      m <- m %>% addLabelOnlyMarkers(lng = pts$lon, lat = pts$lat, label = as.character(pts$n), labelOptions = labelOptions(noHide = TRUE, textOnly = TRUE, direction = "center", style = list("color" = "#FFFFFF", "font-size" = "10px", "font-weight" = "700")))
      if (isTRUE(input$show_names)) m <- m %>% addLabelOnlyMarkers(lng = pts$lon, lat = pts$lat - 1.8, label = pts$tname, labelOptions = labelOptions(noHide = TRUE, textOnly = TRUE, direction = "center", style = list("color" = "#263238", "font-size" = "10px", "font-weight" = "600")))
    }
    m
  })
  output$p_rcc <- renderPlot({
    d <- expl(fd()) %>% left_join(ref, by = c("country1" = "country")) %>% filter(!is.na(rcc), nzchar(rcc)) %>% count(rcc)
    validate(need(nrow(d) > 0, "-")); ggplot(d, aes(reorder(rcc, n), n, fill = rcc)) + geom_col() + scale_fill_manual(values = rcc_colors, guide = "none") + coord_flip() + labs(x = NULL, y = NULL) + th
  })
  output$p_ctry <- renderPlot({ d <- cnt() %>% arrange(desc(n)) %>% head(12); validate(need(nrow(d) > 0, "-")); ggplot(d, aes(reorder(country1, n), n)) + geom_col(fill = "#8B1E2D") + coord_flip() + labs(x = NULL, y = NULL) + th })

  tiers <- c("T0", "T1", "T2", "T3", "T4")
  output$p_evmap <- renderPlot({
    d <- fd() %>% filter(nzchar(pathogen_v2), evidence_tier %in% tiers) %>%
      mutate(verif = case_when(grepl("^en attente", realization_status) ~ "1 Target in the future: to verify later",
                               grepl("^à vérifier", realization_status) ~ "2 Target year reached: verify now",
                               TRUE ~ "3 No target year: not time-bound")) %>% count(pathogen_v2, evidence_tier, verif)
    validate(need(nrow(d) > 0, "-"))
    ord <- d %>% group_by(pathogen_v2) %>% summarise(s = sum(n)) %>% arrange(desc(s)) %>% head(15)
    d <- d %>% filter(pathogen_v2 %in% ord$pathogen_v2); d$pathogen_v2 <- factor(d$pathogen_v2, levels = rev(ord$pathogen_v2)); d$evidence_tier <- factor(d$evidence_tier, levels = tiers)
    ggplot(d, aes(evidence_tier, pathogen_v2)) + geom_point(aes(size = n, fill = evidence_tier), shape = 21, color = "#263238", stroke = 0.5, alpha = 0.92) +
      geom_text(aes(label = n), size = 3, color = "#0F2E1B", fontface = "bold") + facet_wrap(~verif, nrow = 1) +
      scale_fill_manual(values = c(T0 = "#B8C0BE", T1 = "#95A5A6", T2 = "#F0B323", T3 = "#6BAA75", T4 = "#1A5632"), guide = "none") +
      scale_size_area(max_size = 15, guide = "none") + scale_x_discrete(drop = FALSE, position = "top") + labs(x = NULL, y = NULL) +
      th + theme(panel.grid.major = element_line(color = "#E6EAE8"), strip.text = element_text(face = "bold", size = 11), strip.background = element_rect(fill = "#EEF3F0", color = NA), axis.text.x = element_text(face = "bold"))
  })
  output$p_evtier <- renderPlot({
    d <- fd() %>% filter(evidence_tier %in% tiers) %>% count(evidence_tier); validate(need(nrow(d) > 0, "-"))
    d$evidence_tier <- factor(d$evidence_tier, levels = tiers)
    ggplot(d, aes(evidence_tier, n, fill = evidence_tier)) + geom_col() + geom_text(aes(label = n), vjust = -0.4, size = 4) +
      scale_fill_manual(values = c(T0 = "#B8C0BE", T1 = "#95A5A6", T2 = "#F0B323", T3 = "#2E8B57", T4 = "#1A5632"), guide = "none") + scale_y_continuous(expand = expansion(mult = c(0, 0.15))) + labs(x = NULL, y = NULL) + th
  })
  output$p_evbub <- renderPlot({
    d <- fd() %>% filter(nzchar(pathogen_v2), nzchar(model_class_v2)) %>% group_by(pathogen_v2, model_class_v2) %>% summarise(n = n(), hi = mean(evidence_tier %in% c("T3", "T4")), .groups = "drop")
    validate(need(nrow(d) > 0, "-"))
    tp <- d %>% group_by(pathogen_v2) %>% summarise(s = sum(n)) %>% arrange(desc(s)) %>% head(12) %>% pull(pathogen_v2)
    d <- d %>% filter(pathogen_v2 %in% tp); d$pathogen_v2 <- factor(d$pathogen_v2, levels = rev(tp))
    ggplot(d, aes(model_class_v2, pathogen_v2, size = n, fill = hi)) + geom_point(shape = 21, color = "#34495E", stroke = 0.6) +
      scale_size_area(max_size = 16, breaks = c(1, 5, 15, 30), name = "Studies") + scale_fill_gradient(low = "#F0B323", high = "#1A5632", limits = c(0, 1), labels = percent, name = "T3+") +
      labs(x = NULL, y = NULL) + th + theme(axis.text.x = element_text(angle = 30, hjust = 1), legend.position = "right")
  })

  output$t_pred <- renderDT({
    d <- fd() %>% transmute(Disease = pathogen_v2, Countries = countries_name, `Target year` = target_year_v2, Evidence = evidence_tier, Status = realization_status, Title = title)
    datatable(d, rownames = FALSE, options = list(pageLength = 10, scrollX = TRUE))
  })
  output$p_real <- renderPlot(bar(fd(), "realization_status", "#F0B323", 8))
  output$p_target <- renderPlot({ d <- fd() %>% filter(nzchar(target_year_v2)) %>% mutate(t = as.character(as.integer(as.numeric(target_year_v2)))) %>% count(t); validate(need(nrow(d) > 0, "-")); ggplot(d, aes(t, n)) + geom_col(fill = "#2980B9") + labs(x = NULL, y = NULL) + th })

  output$p_heat <- renderPlot({
    d <- expl(fd()) %>% filter(nzchar(pathogen_v2)) %>% count(pathogen_v2, country1)
    validate(need(nrow(d) > 0, "-"))
    tp <- d %>% group_by(pathogen_v2) %>% summarise(s = sum(n)) %>% arrange(desc(s)) %>% head(12) %>% pull(pathogen_v2)
    tc <- d %>% group_by(country1) %>% summarise(s = sum(n)) %>% arrange(desc(s)) %>% head(15) %>% pull(country1)
    d <- d %>% filter(pathogen_v2 %in% tp, country1 %in% tc)
    ggplot(d, aes(country1, pathogen_v2, fill = n)) + geom_tile(color = "white") + geom_text(aes(label = n), size = 3.4) + scale_fill_gradient(low = "#E8F3EC", high = "#1A5632", guide = "none") + labs(x = NULL, y = NULL) + th + theme(axis.text.x = element_text(angle = 50, hjust = 1))
  })
  output$t_cov <- renderDT(datatable(cov %>% rename(Disease = pathogene, Country = pays, Studies = etudes, `Coverage state` = etat_couverture), rownames = FALSE, options = list(pageLength = 12, scrollX = TRUE)))
  output$p_scope <- renderPlot(bar(fd(), "geo_scope_v2", "#8B1E2D", 6))
  lead <- reactive(fd() %>% mutate(lead = case_when(africa_led == "True" ~ "Led from Africa (first or last author)",
                                                 no_african_affiliation == "True" ~ "No African affiliation",
                                                 nzchar(first_author) | nzchar(last_author) ~ "African co-author only", TRUE ~ "Unknown")))
  output$a1 <- renderValueBox({ d <- lead(); valueBox(sprintf("%.0f %%", 100 * mean(d$lead == "Led from Africa (first or last author)")), "Led from Africa (first or last author)", icon = icon("user-check"), color = "green") })
  output$a2 <- renderValueBox({ d <- lead(); valueBox(sprintf("%.0f %%", 100 * mean(d$lead == "African co-author only")), "African co-author only", icon = icon("handshake"), color = "yellow") })
  output$a3 <- renderValueBox({ d <- lead(); valueBox(sprintf("%.0f %%", 100 * mean(d$lead == "No African affiliation")), "No African affiliation", icon = icon("triangle-exclamation"), color = "red") })
  LCOL <- c("Led from Africa (first or last author)" = "#1A5632", "African co-author only" = "#F6C85F", "No African affiliation" = "#B3261E", "Unknown" = "#B8C0BE")
  output$p_led <- renderPlot({
    d <- lead() %>% filter(nzchar(pathogen_v2)) %>% count(pathogen_v2, lead); validate(need(nrow(d) > 0, "-"))
    top <- d %>% group_by(pathogen_v2) %>% summarise(s = sum(n)) %>% arrange(desc(s)) %>% head(10) %>% pull(pathogen_v2)
    ggplot(d %>% filter(pathogen_v2 %in% top), aes(factor(pathogen_v2, levels = rev(top)), n, fill = lead)) + geom_col(position = "fill") + coord_flip() +
      scale_fill_manual(values = LCOL, name = NULL) + scale_y_continuous(labels = percent) + labs(x = NULL, y = NULL) + th + theme(legend.position = "bottom", legend.text = element_text(size = 8)) + guides(fill = guide_legend(nrow = 2))
  })
  output$p_led_year <- renderPlot({
    d <- lead() %>% filter(!is.na(year)) %>% count(year, lead); validate(need(nrow(d) > 0, "-"))
    ggplot(d, aes(factor(year), n, fill = lead)) + geom_col(position = "fill") + scale_fill_manual(values = LCOL, name = NULL) + scale_y_continuous(labels = percent) + labs(x = NULL, y = NULL) + th + theme(legend.position = "bottom")
  })
  output$map_mod <- renderLeaflet({
    m <- leaflet(options = leafletOptions(minZoom = 3, maxZoom = 6)) %>% addProviderTiles(providers$OpenStreetMap) %>% fitBounds(-25, -38, 60, 40) %>% setMaxBounds(-30, -40, 65, 42)
    iso <- fd()$author_countries_africa; iso <- unlist(strsplit(iso[nzchar(iso)], "[|;]")); iso <- trimws(iso); iso <- iso[nzchar(iso)]
    if (!length(iso)) return(m)
    cnt <- as.data.frame(table(iso), stringsAsFactors = FALSE); names(cnt) <- c("iso3", "n")
    pts <- cnt %>% left_join(ref %>% select(country, iso3, lat, lon, rcc) %>% distinct(iso3, .keep_all = TRUE), by = "iso3") %>% filter(!is.na(lat))
    if (!nrow(pts)) return(m)
    col <- unname(rcc_colors[pts$rcc]); col[is.na(col)] <- "#9AA0A6"
    m %>% addCircleMarkers(lng = pts$lon, lat = pts$lat, radius = pmin(30, pmax(7, 3 + 1.1 * sqrt(pts$n))), fillColor = col, fillOpacity = 0.85, color = "#263238", weight = 1,
                           popup = paste0("<b>", pts$country, "</b><br/>Studies with an author affiliated here: ", pts$n), label = paste0(pts$country, ": ", pts$n)) %>%
      addLegend(position = "bottomleft", colors = unname(rcc_colors), labels = names(rcc_colors), title = "Africa CDC RCC", opacity = 0.9)
  })
  output$t_prisma <- renderDT(datatable(prisma %>% rename(Step = etape, N = n), rownames = FALSE, options = list(dom = "t", pageLength = 20, ordering = FALSE)))

  observeEvent(input$a_aud, {
    a <- AUD[[input$a_aud]]; updateCheckboxGroupInput(session, "a_tier", selected = a$t); updateSelectInput(session, "a_lvl", selected = a$l)
  })
  al <- reactive({
    d <- alerts %>% filter(alert_tier %in% input$a_tier, LVLN[priority_level] >= LVLN[input$a_lvl])
    if (input$a_path != "All") d <- d %>% filter(pathogen == input$a_path)
    sel <- if (input$a_ctry != "All") input$a_ctry else if (input$a_rcc != "All") ref$country[ref$rcc == input$a_rcc] else NULL
    if (!is.null(sel) && nrow(d)) {
      keep <- vapply(strsplit(d$countries, ";"), function(x) { x <- trimws(x); x <- x[nzchar(x)]; length(x) == 0 || length(x) > 3 || any(x %in% sel) }, logical(1))
      d <- d[keep, ]
    }
    d %>% arrange(desc(score))
  })
  output$t_alr <- renderDT(datatable(al() %>% transmute(Priority = priority_level, Disease = pathogen, Countries = countries, Evidence = evidence_tier, Title = title), rownames = FALSE, options = list(pageLength = 8, scrollX = TRUE)))
  output$mail_prev <- renderUI({
    d <- head(al(), 3)
    if (!nrow(d)) return(tags$p("-"))
    cards <- lapply(seq_len(nrow(d)), function(i) {
      r <- d[i, ]; col <- if (r$priority_level == "high") "#b42318" else "#b54708"
      tags$div(style = paste0("border-left:4px solid ", col, ";padding:8px 12px;margin:8px 0;background:#fafafa"),
        tags$div(style = paste0("font-size:12px;font-weight:bold;color:", col), paste(LVL_FR[[r$priority_level]], "·", r$pathogen)),
        tags$div(style = "font-size:14px;margin:2px 0", tags$a(href = r$url, target = "_blank", r$title)),
        tags$div(style = "font-size:12px;color:#333", paste0(r$countries, " · ", r$model_class, " · ", r$evidence_tier)),
        tags$div(style = "font-size:11px;color:#555;font-style:italic", r$signal_detail))
    })
    tagList(tags$div(class = "no-tr", style = "font-size:12px;color:#555", paste0("[PREIS-Modeling] ", nrow(al()), " · ", input$a_aud)), cards,
            tags$p(style = "font-size:11px;color:#555", CAV), tags$p(style = "font-size:11px;color:#b54708", "Sending is disabled (simulation). This is a preview, nothing was sent."))
  })

  output$b1 <- renderValueBox(valueBox(nrow(btE), "Forecasts compared with observations", color = "green"))
  output$b2 <- renderValueBox(valueBox(if (nrow(btE)) sprintf("%.2f", median(btE$ratio, na.rm = TRUE)) else "NA", "Median observed / predicted", color = "yellow"))
  output$b3 <- renderValueBox(valueBox(sum(btE$ratio < 1, na.rm = TRUE), "Overestimates (ratio below 1)", color = "red"))
  output$p_bt <- renderPlot({
    validate(need(nrow(btE) > 0, "-"))
    d <- btE %>% arrange(ratio) %>% mutate(id = factor(record_id, levels = record_id))
    ggplot(d, aes(id, ratio, fill = verdict)) + geom_col() + geom_hline(yintercept = 1, linetype = 2) + scale_fill_manual(values = VCOL, drop = FALSE) + labs(x = NULL, y = NULL, fill = NULL) + th + theme(axis.text.x = element_text(angle = 60, hjust = 1))
  })
  output$t_bt <- renderDT(datatable(btE %>% transmute(ID = record_id, Country = country, Model = model_class, Group = group_id, Predicted = point, Observed = observed, Ratio = round(ratio, 2), Days = horizon_days, Verdict = verdict), rownames = FALSE, options = list(pageLength = 10, scrollX = TRUE)))

  output$dl_reg <- downloadHandler("preis_modeling_studies.csv", function(f) write_csv(fd(), f))
  output$dl_alr <- downloadHandler("preis_modeling_alerts.csv", function(f) write_csv(al(), f))
  output$dl_bt <- downloadHandler("preis_modeling_backtest.csv", function(f) write_csv(btE, f))
}
shinyApp(ui, server)
