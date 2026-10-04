# Historical College Model — Formula Specification

This specification documents the core scoring logic of the 2017 college-selection workbook so that the design can be evaluated before any modern rebuild.

The purpose is **not** to preserve the old coefficients unchanged. It is to make the model's assumptions inspectable.

## Reference layout

Historical data rows begin at row 17 in the analyzed workbook and extend through approximately row 150.

### Inputs

| Cell | Meaning |
| --- | --- |
| C2 | SAT Critical Reading |
| C3 | SAT Mathematics |
| C4 | ACT |
| C5 | Private/Public preference |
| C6 | National/Liberal Arts College preference |
| C7 | Urban/Rural preference |
| C8 | Number of Students preference |
| C9 | Ranking/Exclusivity importance |
| C10 | Academics importance |
| C11 | Social importance |
| C12 | Quality of Life importance |

### Primary institution fields used by scoring

| Column | Meaning |
| --- | --- |
| B | Original order / rank-like identifier |
| C | School |
| F | Location type |
| G | Private/Public |
| I | Undergraduates |
| Q | SAT Critical Reading midpoint / derived value |
| R | SAT Math midpoint / derived value |
| T:U | ACT range components |
| AD | Acceptance rate |
| AH | Academics rating |
| AI | Social rating |
| AJ | Quality-of-life rating |

## Formula pipeline

### 1. Test-score difference

**CN — SAT**

    =IF(OR(ISBLANK($C$2),ISBLANK($C$3))=FALSE,Q17+R17,"")

**CO — ACT**

    =IF(ISBLANK($C$4)=FALSE,(T17+U17)/2-$C$4,"")

### 2. Scale SAT and ACT to comparable values

**CP — SATscaled**

    =IF(ISNUMBER(CN17)=TRUE,CN17/1600,"")

**CQ — ACTscaled**

    =IF(ISNUMBER(CO17)=TRUE,CO17/27,"")

### 3. Select combined academic-fit value

**CR — Best**

    =IF(AND(ISNUMBER(CN17)=TRUE,ISNUMBER(CO17)=TRUE)=TRUE,SMALL(CP17:CQ17,1),SUM(IF(ISNUMBER(CN17),CN17/1600,0),IF(ISNUMBER(CO17),CO17/27,0)))

When both SAT and ACT are available, the model uses the smaller scaled value.

### 4. Acceptance-rate weighting

**CS — Accptrateweight**

    =(1-AD17)/20

Lower acceptance rates therefore produce larger positive weighting values.

### 5. Reach / Target / Safety admissions functions

**CT — Reach**

    =(((CR17+0.04)*10)^2)*(-0.5)+3*CS17

**CU — Target**

    =(((CR17+0.07)*10)^2)*(-0.6)+IF(CR17>-0.045,-1,0)+IF(AD17*1<0.1,-6,2)

**CV — Safety**

    =(((CR17+0.1)*10)^2)*(-0.75)-2*CS17+IF(CR17>-0.12,-1,0)+IF(AD17*1<0.2,-6,2)

These are nonlinear heuristic functions. They should be treated as design history rather than validated admissions probabilities.

## Institution feature encodings

**CW — Private/Public:** private = 1, other = 2.

**CX — National/LAC:** derived from the original-order label.

**CY — Urban/Rural:** maps location labels to a 1–4 scale: Rural 1; Small Town 2; Small City/Suburban/City Outskirts 3; City Center/Urban 4.

**CZ — Number of Students:** undergraduate enrollment.

**DA — Ranking/Exclusivity:** historical rank-like identifier.

**DB / DC / DD:** academics, social, and quality-of-life values derived from star-rating fields.

**DE — SAT/ACT:** carries forward the combined academic-fit value.

## Preference contributions

The user's preference controls in C5:C12 feed separate contributions.

**DF — Private/Public contribution**

    =IF(ISBLANK($C$5)=TRUE,0,(IF(CW17=1,1,-1))*((3-$C$5)*ABS(3-$C$5))/40)

**DG — National/LAC contribution**

    =IF(ISBLANK($C$6)=TRUE,0,(IF(CX17=1,-1,1))*((3-$C$6)*ABS(3-$C$6))/40+IF(CX17=1,-0.025,0))

**DH — Urban/Rural contribution**

    =IF(ISBLANK($C$7)=TRUE,0,(CY17/5-0.5)*(3-$C$7)*0.2)

**DI — Enrollment-size contribution**

    =IF(ISBLANK($C$8)=TRUE,0,(0.5-CZ17/LARGE($CZ$17:$CZ$150,1))*(3-$C$8)*ABS(3-$C$8)*0.1)

**DJ — Ranking/Exclusivity contribution**

    =IF(OR(ISBLANK($C$9)=TRUE,$C$9=5),0,((100-DA17)/200)*1.3^(5-$C$9)/4)

**DK — Academics contribution**

    =IF(ISBLANK($C$10)=TRUE,0,(DB17/5)*(5-$C$10)/10)

**DL — Social contribution**

    =IF(ISBLANK($C$11)=TRUE,0,(DC17/5)*(5-$C$11)/10)

**DM — Quality-of-life contribution**

    =IF(ISBLANK($C$12)=TRUE,0,(DD17/5)*(5-$C$12)/10)

## Aggregate fit scores

**DN — overall preference result**

    =SUM(DF17:DM17)

**DO — Reach result**

    =DN17+CT17

**DP — Target result**

    =DN17+CU17+IF(AND(OR(ISBLANK($C$2),ISBLANK($C$3)),ISBLANK($C$4),AD17*1<0.15)=TRUE,-10,0)

**DQ — Safety result**

    =DN17+CV17+IF(AND(OR(ISBLANK($C$2),ISBLANK($C$3)),ISBLANK($C$4),AD17*1<0.25)=TRUE,-10,0)

The last two include large penalties for highly selective institutions when no test-score inputs are provided.

## Ranking blocks

The workbook repeats a transparent ranking pattern for overall fit, Reach, Target, and Safety.

Each block uses result value, row number, rank, fractional tie-break, adjusted rank, LARGE/SMALL ordering, MATCH, and INDEX to return ordered school names.

- Overall: DR:DY
- Reach: DZ:EG
- Target: EH:EP
- Safety: EQ:EY

## Design strengths

- User controls are visible.
- Preference contributions are individually inspectable.
- Admissions and fit are separate dimensions.
- Multiple output lists avoid collapsing every decision into one score.
- Tie-breaking is explicit.
- Formula logic is auditable.

## Historical assumptions to challenge

The rebuild should explicitly test or replace:

- scaling ACT by 27;
- choosing the smaller SAT/ACT scaled value;
- squared penalty functions and hand-tuned offsets;
- acceptance-rate weighting as a proxy for selectivity;
- fixed acceptance-rate thresholds;
- rankings as quality/exclusivity;
- star-count ratings as numeric variables;
- binary institution-type encoding;
- four-level geography encoding;
- raw enrollment normalization against the largest school;
- lack of confidence intervals or missing-data uncertainty;
- lack of source recency at the field level;
- absence of affordability, completion outcomes, career pathways, and labor-market uncertainty in the scoring core.

## Modernization principle

The historical model should be treated as an **explainable prototype**, not as a current admissions predictor. The rebuild should preserve transparency and user control while replacing stale data and heuristic coefficients with current, source-traceable, uncertainty-aware logic.
