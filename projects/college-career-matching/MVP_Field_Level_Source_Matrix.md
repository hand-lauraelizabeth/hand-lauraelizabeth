# MVP Field-Level Source Matrix

This matrix translates the College + Career Matching Tool architecture into implementation fields. It keeps **source facts**, **user inputs**, and **derived scores** separate so users can see what came from an external dataset versus what reflects their own preferences or model logic.

## Implementation rules

- Admissions data provide **context**, not a probability of admission.
- CIP↔SOC relationships remain **many-to-many**.
- Missing or privacy-suppressed data remain unknown; they are not silently converted to zero.
- Every external record carries a source version/reference year and retrieval date.
- Current wages, long-term outlook, and current job-posting demand remain separate signals.
- Private Handshake/Symplicity/student records are not production sources for the public matcher.

| Layer | Matcher Field | Production Source | Source Variable / Table | Join Key | Geography / Grain | Refresh Cadence | Transformation | Missing-Data Rule | MVP Use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Institution | unit_id | College Scorecard / IPEDS | id / UNITID | UNITID | Institution | Scorecard/API + annual IPEDS | Integer key; canonical institution ID | Exclude records without a valid UNITID | Primary cross-dataset institution key |
| Institution | institution_name | College Scorecard | school.name | UNITID | Institution | Scorecard latest | Trim whitespace only | Required | Display + search |
| Institution | city | College Scorecard | school.city | UNITID | Institution | Scorecard latest | Normalize case only | Allow missing | Display/filter |
| Institution | state | College Scorecard | school.state | UNITID | State | Scorecard latest | USPS code | Required for U.S. institutions | Display/filter |
| Institution | zip | College Scorecard | school.zip | UNITID | Institution | Scorecard latest | Preserve leading zeros | Allow missing | Display/geocoding support |
| Institution | ownership | College Scorecard | school.ownership | UNITID | Institution | Scorecard latest | Map code to Public / Private nonprofit / Private for-profit | Unknown if missing | Preference/filter |
| Institution | predominant_degree | College Scorecard | school.degrees_awarded.predominant | UNITID | Institution | Scorecard latest | Map code to certificate/associate/bachelor/graduate/etc. | Unknown if missing | Eligibility/filter |
| Institution | locale | College Scorecard / IPEDS | school.locale / LOCALE | UNITID | Institution | Annual | Map locale codes into transparent urban/suburban/town/rural categories | Unknown if missing | Geographic preference |
| Institution | undergrad_size | College Scorecard | latest.student.size | UNITID | Institution | Scorecard latest | Numeric; preserve raw count | Unknown if missing | Size preference |
| Institution | student_faculty_ratio | College Scorecard | latest.student.faculty_ratio | UNITID | Institution | Scorecard latest | Numeric | Unknown if missing | Context only; not default weighted |
| Institution | offers_fully_online_program | IPEDS IC | DISTPGS | UNITID | Institution | Annual IPEDS | Boolean from IPEDS code | Unknown if missing | Delivery-mode filter |
| Admissions | admission_rate | College Scorecard | latest.admissions.admission_rate.overall | UNITID | Institution | Scorecard latest | 0–1 to percentage for display | Show unknown; never impute | Descriptive selectivity context, not admission probability |
| Admissions | sat_average | College Scorecard | latest.admissions.sat_scores.average.overall | UNITID | Institution | Scorecard latest | Numeric | Show unknown; do not penalize schools with no score data | Context |
| Admissions | sat_reading_25 | College Scorecard | latest.admissions.sat_scores.25th_percentile.critical_reading | UNITID | Institution | Scorecard latest | Numeric | Unknown if suppressed/missing | Profile context |
| Admissions | sat_reading_75 | College Scorecard | latest.admissions.sat_scores.75th_percentile.critical_reading | UNITID | Institution | Scorecard latest | Numeric | Unknown if suppressed/missing | Profile context |
| Admissions | sat_math_25 | College Scorecard | latest.admissions.sat_scores.25th_percentile.math | UNITID | Institution | Scorecard latest | Numeric | Unknown if suppressed/missing | Profile context |
| Admissions | sat_math_75 | College Scorecard | latest.admissions.sat_scores.75th_percentile.math | UNITID | Institution | Scorecard latest | Numeric | Unknown if suppressed/missing | Profile context |
| Admissions | act_composite_25 | College Scorecard | latest.admissions.act_scores.25th_percentile.cumulative | UNITID | Institution | Scorecard latest | Numeric | Unknown if suppressed/missing | Profile context |
| Admissions | act_composite_75 | College Scorecard | latest.admissions.act_scores.75th_percentile.cumulative | UNITID | Institution | Scorecard latest | Numeric | Unknown if suppressed/missing | Profile context |
| Affordability & Outcomes | tuition_in_state | College Scorecard | latest.cost.tuition.in_state | UNITID | Institution | Scorecard latest | USD | Unknown if missing | Cost context |
| Affordability & Outcomes | tuition_out_of_state | College Scorecard | latest.cost.tuition.out_of_state | UNITID | Institution | Scorecard latest | USD | Unknown if missing | Cost context |
| Affordability & Outcomes | avg_net_price | College Scorecard | latest.cost.avg_net_price.overall | UNITID | Institution | Scorecard latest | USD; retain source cohort/year metadata | Unknown/suppressed stays unknown | Affordability |
| Affordability & Outcomes | completion_rate | College Scorecard | latest.completion.consumer_rate | UNITID | Institution | Scorecard latest | 0–1 to percentage | Unknown/suppressed stays unknown | Outcome context |
| Affordability & Outcomes | retention_rate | College Scorecard | latest.student.retention_rate | UNITID | Institution | Scorecard latest | 0–1 to percentage | Unknown if missing | Outcome context |
| Affordability & Outcomes | median_debt_completers | College Scorecard | latest.aid.median_debt.completers.overall | UNITID | Institution | Scorecard latest | USD | PrivacySuppressed/missing stays unknown | Affordability/outcome |
| Affordability & Outcomes | median_earnings_6yr | College Scorecard | latest.earnings.6_yrs_after_entry.median | UNITID | Institution | Scorecard latest | USD; label cohort basis clearly | PrivacySuppressed/missing stays unknown | Outcome context |
| Affordability & Outcomes | median_earnings_10yr | College Scorecard | latest.earnings.10_yrs_after_entry.median | UNITID | Institution | Scorecard latest | USD; label cohort basis clearly | PrivacySuppressed/missing stays unknown | Outcome context |
| Programs | cip_6 | IPEDS Completions / CIP taxonomy | CIPCODE | UNITID + CIPCODE + award level | Program | Annual IPEDS / versioned CIP | Normalize to 6-digit 2020 CIP where possible | Do not infer unavailable codes | Program identity |
| Programs | program_title | NCES CIP 2020 | CIP title | CIPCODE | Program | Versioned taxonomy | Join title from CIP table | Required after valid CIP join | Display/search |
| Programs | credential_level | IPEDS Completions | AWLEVEL | UNITID + CIPCODE + AWLEVEL | Program | Annual IPEDS | Map award-level code to readable credential | Unknown if missing | Program filter |
| Programs | annual_completions | IPEDS Completions | CTOTALT (or current total-completions field in release dictionary) | UNITID + CIPCODE + AWLEVEL | Program | Annual IPEDS | Numeric; use release dictionary rather than hard-coding across years | Unknown if missing | Program scale/context |
| Programs | field_of_study_earnings | College Scorecard field-of-study data | current field-of-study median earnings metric | UNITID/OPEID6 + CIP4 + credential | Field of study | Scorecard release | Use Scorecard cohort definitions; do not mix years silently | PrivacySuppressed/missing stays unknown | Program outcome context |
| Programs | field_of_study_debt | College Scorecard field-of-study data | current field-of-study median debt metric | UNITID/OPEID6 + CIP4 + credential | Field of study | Scorecard release | Use Scorecard cohort definitions | PrivacySuppressed/missing stays unknown | Program affordability context |
| Education-to-Career | cip_soc_link | NCES/BLS CIP–SOC Crosswalk | CIP2020_SOC2018_Crosswalk | CIP 6 + SOC 6 | Program ↔ occupation | Versioned crosswalk | Preserve many-to-many links; no single 'correct job' | No link = no direct-preparation claim | Pathway generation |
| Occupation | soc_code | O*NET / BLS | onetsoc_code mapped to SOC | SOC/O*NET-SOC | Occupation | O*NET release | Preserve detailed O*NET-SOC; maintain SOC bridge | Required | Occupation key |
| Occupation | occupation_title | O*NET | occupation_data.title | O*NET-SOC | Occupation | O*NET release | Text | Required | Display/search |
| Occupation | occupation_description | O*NET | occupation_data.description | O*NET-SOC | Occupation | O*NET release | Text | Allow missing | Explanation |
| Occupation | essential_skills | O*NET 31.0 | essential_skills table: element_id, element_name, scale_id, data_value | O*NET-SOC | Occupation | Each O*NET production release | Retain element/scale/value; do not collapse scales | No imputation | Skill alignment |
| Occupation | transferable_skills | O*NET 31.0 | transferable_skills table: element_id, element_name, scale_id, data_value | O*NET-SOC | Occupation | Each O*NET production release | Retain element/scale/value; keep separate from essential skills | No imputation | Transferable-skill alignment |
| Occupation | knowledge | O*NET 31.0 | knowledge table | O*NET-SOC | Occupation | Each O*NET production release | Retain scale + value | No imputation | Knowledge alignment |
| Occupation | abilities | O*NET 31.0 | abilities table | O*NET-SOC | Occupation | Each O*NET production release | Retain scale + value | No imputation | Ability context |
| Occupation | career_interests | O*NET 31.0 | career_interest_types table | O*NET-SOC | Occupation | Each O*NET production release | Retain RIASEC profile data; normalize only for user-facing comparison | No imputation | Interest alignment |
| Occupation | work_activities | O*NET 31.0 | work_activities table | O*NET-SOC | Occupation | Each O*NET production release | Retain element + scale + value | No imputation | Work-content explanation |
| Occupation | work_context | O*NET 31.0 | work_context table | O*NET-SOC | Occupation | Each O*NET production release | Retain category/scale | No imputation | Environment preference |
| Occupation | education_training_experience | O*NET 31.0 | education + training_and_experience tables | O*NET-SOC | Occupation | Each O*NET production release | Keep categorical distributions; do not reduce to a single credential | No imputation | Preparation context |
| Occupation | related_occupations | O*NET 31.0 | related_occupations table | O*NET-SOC | Occupation | Each O*NET production release | Preserve relation/score if provided | Allow none | Adjacent pathways |
| Occupation | software_skills | O*NET 31.0 | software_skills table | O*NET-SOC | Occupation | Each O*NET production release | Normalize software/tool names; preserve source examples | Allow none | Skill/tool exploration |
| Career Outlook | employment_2025 | BLS Employment Projections | Table 1.2: Employment, 2025 | SOC/NEM code | National | Annual projections release | Numeric (thousands in source; convert to persons only if documented) | Unknown if not line-item occupation | Outlook |
| Career Outlook | employment_2035 | BLS Employment Projections | Table 1.2: Employment, 2035 | SOC/NEM code | National | Annual projections release | Same unit as source | Unknown if unavailable | Outlook |
| Career Outlook | growth_percent_2025_35 | BLS Employment Projections | Table 1.2: Employment change, percent, 2025–35 | SOC/NEM code | National | Annual projections release | Percentage | Unknown if unavailable | Outlook |
| Career Outlook | annual_openings_2025_35 | BLS Employment Projections | Table 1.2: Occupational openings, annual average | SOC/NEM code | National | Annual projections release | Numeric; preserve source unit | Unknown if unavailable | Opportunity context |
| Career Outlook | typical_entry_education | BLS Employment Projections | Table 1.2: Typical education needed for entry | SOC/NEM code | National | Annual projections release | Categorical | Unknown if unavailable | Preparation context |
| Career Outlook | related_work_experience | BLS Employment Projections | Table 1.2: Work experience in related occupation | SOC/NEM code | National | Annual projections release | Categorical | Unknown if unavailable | Preparation context |
| Career Outlook | on_job_training | BLS Employment Projections | Table 1.2: Typical on-the-job training | SOC/NEM code | National | Annual projections release | Categorical | Unknown if unavailable | Preparation context |
| Current Wages | area_code | BLS OEWS May 2025 | AREA | AREA + OCC_CODE | National/state/metro/nonmetro | Annual OEWS | Preserve BLS area code | Required for geographic wage rows | Geography key |
| Current Wages | area_title | BLS OEWS May 2025 | AREA_TITLE | AREA | National/state/metro/nonmetro | Annual OEWS | Text | Required after valid area | Display |
| Current Wages | employment_current | BLS OEWS May 2025 | TOT_EMP | AREA + OCC_CODE | National/state/metro/nonmetro | Annual OEWS | Numeric; respect suppression flags | Suppressed stays unknown | Current labor-market level |
| Current Wages | annual_median_wage | BLS OEWS May 2025 | A_MEDIAN | AREA + OCC_CODE | National/state/metro/nonmetro | Annual OEWS | USD | Suppressed stays unknown | Current wage |
| Current Wages | annual_wage_p25 | BLS OEWS May 2025 | A_PCT25 | AREA + OCC_CODE | National/state/metro/nonmetro | Annual OEWS | USD | Suppressed stays unknown | Wage range |
| Current Wages | annual_wage_p75 | BLS OEWS May 2025 | A_PCT75 | AREA + OCC_CODE | National/state/metro/nonmetro | Annual OEWS | USD | Suppressed stays unknown | Wage range |
| Current Demand | posting_id | Public job-posting feeds | source-native stable ID | source + posting_id | Posting | Frequent snapshot | String; never regenerate if stable ID exists | If no ID, derive conservative composite key and mark lower confidence | Deduplication |
| Current Demand | posting_date | Public job-posting feeds | source posting date | posting_id | Posting | Frequent snapshot | Date | Unknown allowed | Recency |
| Current Demand | capture_date | Ingestion metadata | pipeline capture timestamp | posting_id | Posting | Every ingestion | Date/time | Required | Reproducibility |
| Current Demand | employer_name | Public job-posting feeds | employer | posting_id | Posting | Frequent snapshot | Normalize obvious variants; retain raw | Unknown allowed | Demand/employer display |
| Current Demand | job_title | Public job-posting feeds | title | posting_id | Posting | Frequent snapshot | Retain raw + normalized title | Required | Demand/title analysis |
| Current Demand | job_location | Public job-posting feeds | location | posting_id | Posting | Frequent snapshot | Retain raw; geocode separately | Unknown allowed | Geographic demand |
| Current Demand | work_mode | Public job-posting feeds | onsite/hybrid/remote if explicit | posting_id | Posting | Frequent snapshot | Allowed: onsite/hybrid/remote/unknown | Unknown rather than inference | Preference/filter |
| Current Demand | salary_min | Public job-posting feeds | salary minimum | posting_id | Posting | Frequent snapshot | Normalize only when pay period explicit | Unknown if ambiguous | Demand compensation |
| Current Demand | salary_max | Public job-posting feeds | salary maximum | posting_id | Posting | Frequent snapshot | Normalize only when pay period explicit | Unknown if ambiguous | Demand compensation |
| Current Demand | posting_skills | Public posting text + documented skill dictionary | trigger text + normalized skill | posting_id + skill_id | Posting | Frequent snapshot | Store original trigger and normalized skill | No invented skill when trigger absent | Current skill demand |
| Current Demand | occupation_mapping | Derived from title/text → SOC/O*NET | mapping output + confidence | posting_id | Posting | Each ingestion/model version | Store method/version/confidence | Leave unmapped below confidence threshold | Connect postings to occupations |
| User Input | preferred_locations | User-entered | — | user/session | User | On change | List of acceptable locations/remote preferences | Optional | Constraint/preference |
| User Input | preferred_programs_or_fields | User-entered | — | user/session | User | On change | CIP-aligned only after transparent mapping | Optional | Academic interest |
| User Input | career_interests | User-entered | — | user/session | User | On change | Map to O*NET interests/occupations with visible choices | Optional | Career fit |
| User Input | skills_strengths | User-entered | — | user/session | User | On change | Map to O*NET skill/knowledge elements where possible | Optional | Career fit |
| User Input | budget_ceiling | User-entered | — | user/session | User | On change | USD; distinguish sticker vs net-price tolerance | Optional | Affordability constraint |
| User Input | institution_preferences | User-entered | — | user/session | User | On change | Separate weights for size, setting, ownership, delivery, etc. | Optional | College fit |
| User Input | academic_profile | User-entered | — | user/session | User | On change | Self-entered GPA/test context; never treated as verified admissions probability | Optional | Admissions context |
| Derived | college_fit_score | Derived | weighted preference model | user + UNITID | Institution | On user/data change | Normalize components; expose weights and component contributions | Do not compute if too many required components missing | Explainable preference fit |
| Derived | affordability_score | Derived | net price/debt + user budget | user + UNITID | Institution | On user/data change | Use explicit user budget and source metrics; expose missingness | Return insufficient-data state when necessary | Affordability fit |
| Derived | career_pathway_score | Derived | CIP↔SOC + interests/skills + outlook | user + CIP/SOC | Program/occupation | On user/data change | Separate structural pathway, interest/skill fit, and labor-market signals | Do not collapse missing labor data into zero | Career alignment |
| Derived | current_demand_score | Derived | recent public postings | SOC/geography/time window | Occupation/geography | On refresh | Recency-weighted count/share with denominator shown | Insufficient-data state where coverage is weak | Fast-changing demand signal |
| Derived | admissions_context | Derived | Scorecard admissions + user profile | user + UNITID | Institution | On user/data change | Describe relative profile/selectivity; no probability claim | Unknown when source/profile inadequate | Context, not prediction |
| Derived | data_confidence | Derived | source recency + completeness + suppression + mapping confidence | entity | All | On refresh | Transparent rule set | Required for scored outputs | Explanation/QA |

## Official source references

- College Scorecard API/documentation: https://collegescorecard.ed.gov/data/
- College Scorecard API field syntax: https://collegescorecard.ed.gov/data/api-documentation/
- College Scorecard institution technical documentation: https://collegescorecard.ed.gov/files/InstitutionDataDocumentation.pdf
- College Scorecard field-of-study technical documentation: https://collegescorecard.ed.gov/assets/FieldOfStudyDataDocumentation.pdf
- IPEDS Use the Data: https://nces.ed.gov/ipeds/use-the-data
- IPEDS complete data files: https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx
- CIP 2020 resources / CIP↔SOC crosswalk: https://nces.ed.gov/ipeds/cipcode/resources.aspx?y=56
- O*NET 31.0 database: https://www.onetcenter.org/database.html
- BLS 2025–2035 occupational projections: https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm
- BLS Employment Projections data: https://www.bls.gov/emp/data.htm
- BLS May 2025 OEWS tables: https://www.bls.gov/oes/tables.htm

## Version snapshot used for this specification

- O*NET: **31.0**
- BLS Employment Projections: **2025–2035**
- BLS OEWS: **May 2025**
- IPEDS: use latest appropriate provisional/final component release, recording release type
- CIP↔SOC: **CIP 2020 ↔ SOC 2018** official crosswalk
- College Scorecard: use the latest API/data release, preserving the reporting year attached to each metric

## Next build step

Implement the ingestion contract and source manifest for the first four production datasets: College Scorecard, IPEDS/CIP, O*NET, and BLS. Recommendation scoring should wait until these normalized tables can be joined and QA-tested.