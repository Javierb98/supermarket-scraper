"""
Every feed the weekly run calls, one per line: the file name in feeds/
without .py. A feed added here is run, recorded and health-checked like the
others (run_all.sh).

    python -m feeds.registry     prints the list
"""

FEEDS = [
    'statcan',      # CA — Statistics Canada
    'usda',         # US — USDA AMS retail reports
    'defra_wholesale',  # GB — Defra wholesale fruit & veg (wholesale)
    'ons_shopping',     # GB — ONS shopping prices comparison tool (retail)
    'cso_ie',           # IE — CSO table CPM12 (retail)
    'blw_consumer',     # CH + LI — BLW consumer prices (LINDAS)
    'blw_producer',     # CH + LI — BLW producer prices (farmgate)
    'insee',            # FR — INSEE average consumer prices (retail, monthly)
    'rnm',              # FR — FranceAgriMer RNM supermarket survey (retail, weekly)
    'rnm_wholesale',    # FR — FranceAgriMer RNM wholesale markets (wholesale)
    'statsnz',          # NZ — Stats NZ selected price indexes (retail, monthly)
    'bls',              # US — BLS CPI average prices (retail, monthly)
    'heisse_preise',    # AT — heisse-preise.io (Billa shelf prices, third party)
    'checkjebon',       # NL — checkjebon.nl daily JSON (9 chains, third party)
    'statec',           # LU — STATEC average prices of basic products (June, annual)
    'surs_si',          # SI — SURS annual retail and farmgate
    'csb_lv',           # LV — CSB PCC010m monthly retail
    'czso_cz',          # CZ — CZSO DataStat CEN0101N monthly retail
    'ksh_hu',           # HU — KSH ara0044 monthly retail
    'stat_lt',          # LT — Statistics Lithuania retail and farmers' markets
    'oda',              # NO — Oda shelf prices (shop JSON), retail
    'mathem',           # SE — Mathem shelf prices (Oda platform), retail
    'sjv_producer',     # SE — Jordbruksverket JO1001L2, farmgate
    'selver',           # EE — Selver catalogue API, retail
    'stat_ee_milk',     # EE — Statistics Estonia PM18 milk price, farmgate
    'ismea',            # IT + SM — ISMEA Mercati weekly origin (farmgate) and wholesale averages
    'sima',             # PT — GPP SIMA wholesale and production markets, by region
    'pt_observatorio',  # PT — GPP Observatório de Preços (retail + farmgate), 4-weekly
    'continente',       # PT — Continente shelf prices (first page per aisle), retail
    'cijene_hr',        # HR — chain price lists (law), cijene.dev daily archive
    'cenovnici_rs',     # RS — chain price lists (law), data.gov.rs
    'posokanei_gr',     # GR — PosoKanei observatory, GitHub daily snapshots
    'aldi_nord',        # DE — ALDI Nord assortment pages (retail, national)
    'mapa',             # ES — MAPA household consumption panel (retail, monthly, by community)
    # Last: it fills the gaps the national feeds leave and never overwrites them.
    'gus_pl',           # PL — GUS BDL: annual retail, half-yearly farmgate, monthly marketplace
    'eu_agrifood',      # EU — European Commission agri-food data portal (23 countries)
]

if __name__ == '__main__':
    print('\n'.join(FEEDS))
