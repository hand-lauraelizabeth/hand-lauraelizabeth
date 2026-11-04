# Role Evidence Studio career workbench

The workbench adds résumé-first occupation leads, U.S. regional wage context, and an editable résumé draft to the WordPress analysis workspace. The existing posting analysis, audit, reviewed evidence, profile transfer, and export code remains in the integrated HTML. Career Discovery & Tracking remains a separate workspace on the same public page.

## Data and interpretation

| Input | Release | Use |
| --- | --- | --- |
| [O*NET database](https://www.onetcenter.org/database.html) | 31.0 | Official occupation titles, selected alternate titles, and a derived index of titles, descriptions and core tasks |
| [BLS OEWS area estimates and definitions](https://www.bls.gov/oes/tables.htm) | May 2025 | Detailed cross-industry occupations, 25th percentile, median and 75th percentile annual wages for published labor-market areas |
| [Census ZCTA-to-county relationships](https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.2020.html) and [Connecticut 2022 special files](https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.2022.html) | 2020 ZCTAs, 2022 Connecticut county equivalents | County and county-equivalent overlaps with positive land area |

The data cover 1,016 occupations, 33,774 mapped ZCTAs, 528 wage areas, and 183,810 detailed occupation–area records with numeric annual percentiles. If a ZCTA maps to multiple areas, the visitor chooses one. The tool does not present wage values at ZIP-level precision, infer job eligibility, replace suppressed percentiles with guesses, or average across areas. The ranking measures lexical evidence and a target-role preference. It is not a calibrated probability.

O*NET content is adapted from the U.S. Department of Labor, Employment and Training Administration, O*NET 31.0 Database, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The workbench selects titles and converts source wording into a weighted term index. It is independent of O*NET and BLS.

The workbench does not transmit the résumé, posting, or ZIP. It retrieves public catalog and geography files. A wage data request retrieves a fixed bundle covering multiple labor markets, which may indicate a broad area to the file host. The résumé draft preserves the supplied role order and factual claims while organizing headings and prioritizing relevant bullets within a role. Reviewed restricted statements are excluded from the automated draft and matching. Treat the generated text and any downloads as private until reviewed.

## Reproduce the data and integration

Save the following files in this directory and run `python3 build_data.py` with `openpyxl` installed:

- `onet31.zip` from [O*NET 31.0 text files](https://www.onetcenter.org/dl_files/database/db_31_0_text.zip)
- `wages.zip` from [May 2025 metro and nonmetro OEWS tables](https://www.bls.gov/oes/special-requests/oesm25ma.zip)
- `definitions.xlsx` from [May 2025 OEWS area definitions](https://www.bls.gov/oes/area_definitions_m2025.xlsx)
- `zcta.txt` from [2020 Census ZCTA-to-county](https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt)
- `zcta-ct.txt` from [2022 Connecticut subdivision-to-ZCTA](https://www2.census.gov/geo/docs/maps-data/data/rel2022/acs22_cousub22_zcta520_st09.txt)

The `.b64` files are gzip-compressed JSON represented as Base64 for text-only hosting. The release HTML embeds `career-workbench.js`, `workbench.html`, and `workbench.css`. Run `python3 assemble.py --source path/to/current-analysis.html --data-base https://host/path/to/data/` to generate the integration. The WordPress page uses the committed public data snapshot, and the tool only loads the wage file needed for the chosen region.
