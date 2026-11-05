# Where the prices come from

Every figure the website shows says what kind of price it is (`price_stage`)
and who measured it (`source_name`). This file is the longer version: for each
source, what it is, what it covers, the terms we use it under, and how it is
labelled. A source goes on this list **before** its code goes in.

Price stages, never averaged together or shown as one another:

| stage            | what it is                                   | badges?  |
|------------------|----------------------------------------------|----------|
| `retail`         | a shop shelf price                           | yes      |
| `wholesale`      | a wholesale market or trade price            | no — shown to the farmer, labelled |
| `farmers_market` | an official survey of market-stall prices    | no — shown to the farmer, labelled |
| `farmgate`       | what the producer is paid                    | no — shown to the farmer, labelled |

Only a retail price is what a buyer would otherwise pay, so only a retail
price earns a farm a "good value" or "great deal" badge. Where a country has
no shop price for a product, the farmer is shown the trade price, labelled.

Kinds of source, in order of preference:

1. **Official statistics** (a national statistics office or ministry).
2. **Prices published by law** (Croatia, Serbia and Greece require chains to
   publish full price lists).
3. **A shop's own public API or pages**, read politely: one request at a
   time, pauses between them, nothing behind a login, no bot-protection
   workarounds, and `robots.txt` respected.
4. **Third-party price collections** (open projects that gather shop prices
   themselves). Allowed, documented here with their terms, and credited.

No paid sources. Every feed is in `feeds/` and listed in `feeds/registry.py`;
the weekly run (`run_all.sh`) runs each one, records the outcome
(`source_runs`), and reports any that have gone quiet.

## Live

### Shops (scraped by us)

| country | source | stage | covers | terms |
|---|---|---|---|---|
| ES | Mercadona (tienda.mercadona.es) | retail | ~25,000 shelf prices weekly, 17 communities × 2 postcodes | public catalogue, read politely |
| ES | Consum (tienda.consum.es) | retail | ~2,200 prices weekly, national; shop aisle and regular price included | public catalogue, read politely |
| ES | Eroski (supermercado.eroski.es) | retail | ~1,450 prices weekly, national; offers flagged | public pages, read politely |
| DE | ALDI Nord (aldi-nord.de `/sortiment/`) | retail | ~265 fresh shelf prices weekly, national | robots.txt allows `/sortiment/`; 13 requests, 2 s apart |
| NO | Oda (oda.com public search JSON) | retail | ~2,500 products searched weekly → ~107 catalogue products, national | robots.txt crawler policy kept (identified bot, backoff, no `filter_` params) |
| SE | Mathem (mathem.se, Oda platform) | retail | ~3,400 products searched weekly → ~99 catalogue products, national | as Oda |
| EE | Selver (selver.ee catalogue API) | retail | ~1,000 prices weekly from 16 fresh aisles → ~96 catalogue products; offers flagged | catalogue API allowed by robots.txt |
| PT | Continente (continente.pt) | retail | ~860 prices weekly, first page of 42 aisles → ~142 catalogue products | robots.txt allows aisle pages, forbids paging (so first page only) |

### Prices published by law

| country | source | stage | covers | terms |
|---|---|---|---|---|
| HR | chain price lists (NN 75/2025) via cijene.dev daily archive files, 25 chains (not Metro, dm) | retail | ~10,000 products, median over each chain's stores, national; ~180 catalogue products | public by law; cijene.dev terms allow free use; archive files only, not the rate-limited API |
| RS | chain price lists (Sl. glasnik RS 76/2026) on data.gov.rs: Maxi, Idea/Roda/Mercator, Lidl, Univerexport, Gomex, Aman, Super Vero | retail | ~3,200 fresh-category products, RSD, national; ~145 catalogue products | Serbian Open Data Licence: name the source and the date taken |
| GR | PosoKanei (posokanei.gov.gr) via the spyrosavl/posokanei GitHub daily snapshots, 11 chains | retail | packaged eggs, dairy, poultry, mushrooms only (no loose fruit/veg, no red meat); ~30 catalogue products | repository MIT; data © posokanei operators, no reuse licence stated — **credited, removed on request** (owner approved 2026-11-05) |

### Third-party price collections

| country | source | stage | covers | terms |
|---|---|---|---|---|
| NL | checkjebon.nl daily JSON (AH, Jumbo, PLUS, Dirk, Hoogvliet, SPAR, DekaMarkt, Poiesz, Vomar; Lidl left out as unreliable) | retail | ~1,600 fresh shelf prices, national; ~121 catalogue products | code MIT; README: "price data … may be reused in other projects"; credited "(via checkjebon.nl)" on every figure |
| AT | heisse-preise.io per-chain JSON (Billa live; Spar, Hofer, MPREIS, Unimarkt stale and picked up again if revived) | retail | ~1,250 fresh shelf prices → ~150 national figures | code MIT; prices scraped by the project, reuse not stated — **credited ("BILLA (heisse-preise.io)"), removed on request** (owner approved 2026-11-05) |

### Official statistics

| country | source | stage | covers | terms |
|---|---|---|---|---|
| CA | Statistics Canada, table 18-10-0245 | retail | ~28 products monthly, Canada + 10 provinces | Statistics Canada Open Licence |
| US | USDA AMS Market News retail reports | retail | fruit, veg, eggs, dairy; 8 USDA regions; weekly | public domain; free API key |
| US | BLS CPI average prices (AP series) | retail | 18 products monthly, US + 4 census regions | public domain |
| GB | ONS shopping prices comparison tool (avgprice.csv / metadata.csv, ONSdigital/cpi-items-actions) | retail | ~40 products monthly, national; pack sizes converted | Crown copyright, Open Government Licence v3 |
| GB | Defra wholesale fruit & vegetable prices | wholesale | ~40 home-grown fruit & veg, weekly (published fortnightly), national | Open Government Licence v3 |
| IE | CSO table CPM12 | retail | 18 products monthly, national, incl. mushrooms | CC BY 4.0 |
| CH | BLW market observation, consumer prices (LINDAS SPARQL) | retail | 79 products monthly, Switzerland + German/French/Italian-speaking regions | opendata.swiss "open use, must provide the source" (BLW, agrarmarktdaten.ch) |
| CH | BLW market observation, producer prices (LINDAS SPARQL) | farmgate | eggs and raw milk, monthly, national | as above |
| LI | Swiss BLW figures (German-speaking region, else national), labelled "(Swiss figures)" | retail / farmgate | as CH | as above |
| FR | INSEE average consumer prices (IPC-PM-2015), SDMX | retail | 27 products monthly, national | Licence Ouverte / Etalab 2.0 |
| FR | FranceAgriMer RNM supermarket survey ("DETAIL GMS") | retail | 29 fruit & veg weekly, national | Licence Ouverte, "FranceAgriMer – RNM" |
| FR | FranceAgriMer RNM wholesale markets (Rungis, Lyon-Corbas, Marseille, Avignon-Cavaillon, Nice, Bordeaux, Toulouse, Nantes, Strasbourg, Lille) | wholesale | 92 products, region = the market, plus a national median of the markets | as above |
| ES | MAPA household consumption panel | retail | 51 products monthly, Spain + 17 communities, ~2-month lag | Spanish public-sector reuse (Ley 37/2007), attribution to MAPA |
| NZ | Stats NZ selected price indexes (FPI weighted average prices) | retail | 35 products monthly, national | CC BY 4.0, "Stats NZ" |
| LU | STATEC average prices of basic products (LUSTAT DF_E5300) | retail | 7 products, June each year | STATEC open data, CC0 |
| SI | SURS tables 0411005S and 1505000S | retail / farmgate | 21 + 29 products, annual, national | SURS free reuse with attribution |
| LV | CSB table PCC010m | retail | 37 products monthly, national | CSB open data, attribution |
| CZ | CZSO DataStat CEN0101N | retail | 32 products monthly, national | CZSO open data, attribution |
| HU | KSH STADAT ara0044 | retail | 23 products monthly, national | KSH free reuse with attribution |
| LT | Statistics Lithuania S7R244 (retail) and S7R307 (markets, ŽŪDC) | retail / farmers_market | 20 + 17 products monthly, national | CC BY 4.0 |
| SE | Jordbruksverket JO1001L2 | farmgate | 10 products monthly | Swedish open data, attribution |
| EE | Statistics Estonia PM18 | farmgate | milk purchase price, monthly | Statistics Estonia open data, attribution |
| IT, SM | ISMEA Mercati weekly averages (all'origine / all'ingrosso); San Marino labelled "(Italian figures)" | farmgate / wholesale | 51 + 6 products weekly, national | ISMEA copyright; figures used as facts, credited to ISMEA Mercati (owner approved 2026-11-05) |
| PL | GUS Local Data Bank (BDL API): P1466 average retail prices, P3155 procurement prices of fruit & veg, P2968 marketplace prices received by farmers | retail / farmgate / farmers_market | 5 shop products (annual), 14 fruit & veg paid to growers (half-yearly), potatoes at farmers' markets (monthly); national, PLN | GUS free reuse with the source named; works without a key, uses `BDL_API_KEY` if set |
| PT | GPP SIMA (regsima.gpp.pt) | wholesale / farmgate | ~59 wholesale (MARL, MAP, MAC) + ~46 farmgate products weekly, by agrarian region | GPP public information, attribution |
| PT | GPP Observatório de Preços Agroalimentar | retail / farmgate | 16 + 6 products, 4-weekly, national | GPP public information, attribution |
| EU (23 countries) | European Commission agri-food data portal API | farmgate / wholesale / retail | fruit & veg along the supply chain, raw milk, dairy, eggs, poultry, pig and beef cuts; weekly/monthly, national; non-euro countries converted from EUR at the ECB reference rate; runs last and never overwrites a national feed | CC BY 4.0, "European Commission, Agri-food data portal" |

### Borrowed figures

| country | uses | how |
|---|---|---|
| LI | Switzerland | written by the BLW feeds, labelled |
| SM | Italy | written by the ISMEA feed, labelled |
| LU | its own 7 products, then France (Belgium has no shop prices) | the website falls back to the neighbour (`MarketPriceService::BORROWED`) |

## Waiting

| country | source | why waiting |
|---|---|---|
| DE | BLE "Markt- und Preisbericht Obst und Gemüse" (open-data.ble.de, weekly, wholesale by market; Datenlizenz Deutschland Zero 2.0) | the portal's robots.txt disallows all robots — permission requested from open-data@ble.de; build once BLE says yes |
| RO | INS TEMPO PPA101A (market-stall prices by county) | the data endpoint returned nothing on 2026-11-04; retry |
| DE | ALDI Süd (eggs, dairy, meat only online), Knuspr (4 cities) | viable, not built |

## No shop or official prices

The website shows the market comparison only for countries with prices in
`market_average`. Where only the EU portal's trade prices exist, farmers see
those, labelled, and no badge.

| country | what exists |
|---|---|
| BE | EU trade prices only. Statbel publishes only indices; no open project collects Colruyt/Delhaize prices |
| DK | EU milk and potato prices only. No official product prices; shops behind bot protection |
| FI | EU milk and egg prices only. No official product prices; shops behind bot protection |
| SK | EU trade prices only. Average consumer prices discontinued after 2023; the farmgate cube needs a STATdata account |
| AU | nothing: no official product prices since 2011; Coles and Woolworths block requests from outside Australia |
| RE, NC | nothing: PDF bulletins only |
| RU, BY | nothing: access and legal issues |
| BR | nothing (one farm) |

Also checked and ruled out: REWE (Cloudflare CAPTCHA), Kaufland, Edeka and
Netto (403), Carrefour.it and Conad (CAPTCHA), Willys (robots.txt allows
only 04:00–08:45 UTC — Mathem used instead), SSB, SCB and Statistics Estonia
consumer prices (none current), Istat and MIMIT (no average prices /
unreachable), INE Portugal (indices only).
