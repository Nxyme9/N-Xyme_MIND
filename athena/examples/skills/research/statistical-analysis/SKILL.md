---
name: statistical-analysis
description: Structured pipeline for statistical analysis deliverables — SPSS, R, Python. Covers reliability, chi-square, correlation, regression, assumption checking, and client-ready reporting.
version: 1.0.0
created: 2026-03-06
cluster: 13 (Build Lifecycle)
triggers:
  - SPSS
  - statistics
  - regression
  - chi-square
  - correlation
  - reliability
  - Cronbach
  - hypothesis test
  - p-value
  - survey analysis
---

# Statistical Analysis Skill

> **Purpose**: Structured pipeline for statistical analysis deliverables. Prevents assumption violations, missed effect sizes, and uninterpretable output.
> **Origin**: Created ahead of Assignment 19 (SPSS, Siva, $250, deadline Mar 8). No protocol coverage existed for this domain.

## The 5-Step Pipeline

### Step 1: DATA AUDIT

- Load dataset (CSV, SPSS .sav, Excel)
- Profile: N, variable types (nominal/ordinal/interval/ratio), missing data %, outliers
- Check for:
  - Missing data pattern (MCAR/MAR/MNAR) — Little's MCAR test if available
  - Outliers (z-score > 3 or IQR method)
  - Variable coding (reverse-coded items, string-to-numeric conversion)
  - Sample size adequacy per planned test (rule of thumb: 10–15 observations per predictor for regression)

### Step 2: ASSUMPTION MATRIX

> [!IMPORTANT]
> Every statistical test has assumptions. Violating them invalidates results. Check BEFORE running.

| Test Family | Assumptions | Check Method |
|---|---|---|
| **Reliability (Cronbach's α)** | Unidimensionality, interval/ratio data, ≥3 items per scale | Factor analysis / item-total correlations |
| **Chi-Square (χ²)** | Independence, expected frequency ≥ 5 in 80%+ cells, categorical variables | Expected frequency table |
| **Pearson Correlation** | Linearity, normality (both vars), no significant outliers, interval/ratio | Scatter plot, Shapiro-Wilk |
| **Spearman Correlation** | Monotonic relationship, ordinal or non-normal interval | Scatter plot (monotonic check) |
| **Multiple Regression** | Linearity, independence (Durbin-Watson), homoscedasticity, normality of residuals, no multicollinearity (VIF < 10) | Residual plots, VIF table, Durbin-Watson |
| **Independent t-test** | Normality, homogeneity of variance (Levene's), interval/ratio DV | Shapiro-Wilk, Levene's |
| **One-way ANOVA** | Normality, homogeneity (Levene's), independence, interval/ratio DV | Same as t-test + post-hoc if significant |

### Step 3: TEST EXECUTION

For each test in the scope:

1. **State the hypothesis** (H₀ and H₁) explicitly
2. **Run the test** — output test statistic, df, p-value, effect size
3. **Effect size** (mandatory — p-value alone is insufficient):
   - Cohen's d (t-test)
   - η² or partial η² (ANOVA)
   - r or R² (correlation/regression)
   - Cramér's V (chi-square)
   - Cronbach's α (reliability — this IS the effect)
4. **Decision**: Reject/Fail to reject H₀ at α = 0.05 (unless specified otherwise)

### Step 4: INTERPRETATION

For each test result, produce a **3-part interpretation**:

1. **Statistical statement**: "A Pearson correlation revealed a significant positive relationship between X and Y, r(183) = .42, p < .001."
2. **Effect size interpretation**: "This represents a medium effect (Cohen, 1988)."
3. **Practical meaning**: "Workers who received more safety training hours reported higher safety compliance scores, explaining approximately 18% of the variance."

| Effect Size | Small | Medium | Large |
|---|---|---|---|
| Cohen's d | 0.2 | 0.5 | 0.8 |
| r | 0.1 | 0.3 | 0.5 |
| R² | 0.01 | 0.09 | 0.25 |
| η² | 0.01 | 0.06 | 0.14 |
| Cramér's V (df=1) | 0.1 | 0.3 | 0.5 |
| Cronbach's α | < 0.6 poor | 0.7–0.8 acceptable | > 0.9 excellent |

### Step 5: CLIENT-READY REPORT

Structure the output document:

```
1. Introduction (research context, variables, hypotheses)
2. Methodology (sample, measures, statistical tests used)
3. Results
   3.1 Reliability Analysis
   3.2 Chi-Square Tests
   3.3 Correlation Analysis
   3.4 Regression Analysis
4. Discussion (interpret findings, connect to research questions)
5. Limitations
6. References
Appendix: SPSS Output Tables (screenshots or formatted tables)
```

- Use APA 7th edition reporting standards for statistical notation
- Include assumption check results in methodology or as footnotes
- Tables formatted per APA: no vertical lines, horizontal rules at top/bottom/below header only

## Assignment 19 Quick Reference

| Component | Count | Details |
|---|---|---|
| Reliability (Cronbach's α) | 5 | One per scale/construct |
| Chi-Square (χ²) | 4 | Independence tests (demographic × outcome) |
| Correlation | 4 | Bivariate (IV-DV pairs) |
| Regression | 1 | Multiple regression (4 IVs → 1 DV) |
| **Total tests** | **14** | |
| Topic | Safety Training in SG Construction | |
| N | 185 survey responses | |
| IVs | 4 (to be identified from data) | |
| DV | 1 (to be identified from data) | |

## Exit Gate

- [x] All assumption checks documented
- [x] Every test has: hypothesis, test statistic, df, p-value, effect size
- [x] APA-compliant statistical notation
- [x] Practical interpretation (not just "significant/not significant")
- [x] Client-ready formatted output document
