# COP16/31 Notes (GBF Monitoring Framework)

## Source
- Decision PDF: `cop-16-dec-31-en.pdf`
- URL: https://www.cbd.int/doc/decisions/cop-16/cop-16-dec-31-en.pdf

## Implementation-Relevant Extracts

Annex I indicator categories used for seeding and method scaffolding:

### Headline indicators
- A.1 Red list of ecosystems
- A.2 Extent of natural ecosystems
- A.3 Red list of species
- A.4 Genetic diversity within populations of wild species
- A.5 Species habitat index
- B.1 Services provided by ecosystems
- B.2 Sustainable management of wild species
- B.3 Green/blue spaces in urban areas
- B.4 Benefits from the use of genetic resources
- C.1 Monetary benefits from utilization of digital sequence information on genetic resources
- D.1 Public/private biodiversity finance and expenditure
- D.2 Domestic public budget on biodiversity
- D.3 International public funding and private funding in support of biodiversity

### Binary indicators
- 1 National environmental accounting
- 2 Integration of biodiversity into EIA/SEA
- 3 Integration of biodiversity values into policies/planning
- 4 Biodiversity-inclusive spatial planning
- 5 Biodiversity-relevant taxes
- 6 Positive biodiversity incentives
- 7 Sustainable consumption/production indicators
- 8 Biodiversity-friendly and sustainable product trends
- 9 Participatory integrated biodiversity-inclusive spatial planning and IWRM
- 10 Sustainable management in agriculture/aquaculture/fisheries/forestry
- 11 Restoration
- 12 Invasive alien species
- 13 Pollution
- 14 Climate change and ocean acidification
- 15 Access to green and blue spaces
- 16 Traditional medicines
- 17 Human-wildlife conflict
- 18 Species management and harvesting
- 19 Sustainable wild meat use
- 20 Urban planning
- 21 Biodiversity in diets
- 22 Mainstreaming gender in biodiversity policy

## NBMS Mapping Implemented
- Seed command for full catalog:
  - `src/nbms_app/management/commands/seed_gbf_indicators.py`
- Headline/binary scaffold creation:
  - `FrameworkIndicator` + `Indicator` + `IndicatorFrameworkIndicatorLink`
- Method profile scaffolding by indicator:
  - `IndicatorMethodProfile` with explicit method type and required/disaggregation inputs
