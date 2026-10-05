## Causal extension

- **Question:** did state minimum wage increases from 2011 to 2022 raise low-end wages, and did they reduce food-service employment?
- **Methods:** state x year OEWS panel (2005-2022) joined to Vaghul and Zipperer minimum wages; continuous two-way fixed effects, TWFE and Callaway-Sant'Anna event studies with pre-trend tests, a synthetic control case study with placebo inference, and a simulation power analysis.
- **Results:** [RESULTS.md](RESULTS.md) (every number generated from `results/*.json`); design in [docs/METHODS.md](docs/METHODS.md), judgment calls in [docs/DECISIONS.md](docs/DECISIONS.md); interactive page `pages/2_Causal_Analysis.py`.
- **Live page:** https://nividpathak.github.io/wage_analysis/ (static results page, rebuilt from `results/` on every push)
- **Reproduce:** `make all`. This extension is solo work by Nivid Pathak on top of the Group 7 team project; see [CREDITS.md](CREDITS.md).

---

# Labor Market Structure & Wage Prediction

Exploring the drivers of economic compensation in the United States using occupational employment and wage data from the Bureau of Labor Statistics (BLS).

Live website: https://wageanalysis.streamlit.app

---

## Mission Statement

To provide clarity in the labor market through transparent, data-driven analysis of wage structures.

---

## Project Overview

This project investigates why wages vary across occupations, industries, and locations in the US. Using official government statistics from the BLS Occupational Employment and Wage Statistics (OEWS) program, we analyze wage patterns across ~800 occupations and all 50 states over a 20-year period (2005–2024).

The core idea is that a paycheck is one of the most important factors in economic mobility. Yet the same skill set can command very different pay depending on where you work and what sector you're in. This project aims to make that link clear through data — helping students, job seekers, and policy analysts make better-informed decisions.

We use techniques including exploratory data analysis, statistical modeling, regression, and clustering to predict and explain wage variation across the dataset.

---

## Research Questions

1. Does the total number of people working in a field have a correlation with the mean annual wage occupation-wise?
2. If we look at the data right now, which five industries are paying the best median wage for people in entry level roles?
3. Do we see a massive swing in pay for the exact same job title just by looking at different state data?
4. Is there a statistically significant wage gap between 'Management' and 'Technical' roles within the same industry?
5. Can we accurately predict the 90th percentile wage of an occupation based on its 10th percentile and industry code?
6. Which geographic regions exhibit the highest 'wage-to-cost-of-living' ratio?
7. Can clustering identify groups of occupations that are underpaid relative to their required education levels?
8. How has the wage gap between the 10th and 90th percentiles changed across the top 10 industries?
9. To what extent does 'Industry Aggregation' obscure wage differences in specialized sub-roles?
10. Can we predict if an occupation belongs to a 'High Growth' category based solely on its current wage percentiles?

---

## Repository Structure

```
wage_analysis/
├── cleaned_data/      # Cleaned and combined CSV datasets by year
├── data/              # Raw BLS data files (XLS format, by year)
├── files/             # Project proposal and supporting documents
├── images/            # Team and project images
├── notebooks/         # Jupyter notebooks for analysis and preprocessing
├── app.py             # Main Streamlit web application
└── requirements.txt   # Python dependencies
```

---

## Dataset

- **Source:** BLS Occupational Employment and Wage Statistics (OEWS)
- **Coverage:** ~800 occupations across all US states and territories, 2005–2024
- **Size:** ~739,000 rows × 24 columns
- **Key variables:** Occupation title, state, total employment, mean/median annual wage, wage percentiles (10th–90th)

The BLS was chosen as the data source because it is an authoritative, reliable, and regularly updated government source — ensuring data integrity and real-world relevance.

---

## Team — Group 7

- **Soorej S Nair** — Modeling Lead, focused on regression analysis and predictive accuracy.
- **Anjana Anand** — Visualization Lead, expert in creating intuitive and interactive dashboards.
- **Nivid Pathak** — Data Lead, specializes in data cleaning and ETL processes.
- **Karan Cheemalapati** — Project Manager, ensures milestone alignment and documentation quality.
