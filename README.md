[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/N3kLi3ZO)
[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=23640558&assignment_repo_type=AssignmentRepo)
# Blockchain Dashboard Project

## Student Information

| Field | Value |
|---|---|
| Student Name | Eduardo Vallejo |
| GitHub Username | vallesdu |
| Project Title | Bitcoin Live Metrics & AI Insights |
| Chosen AI Approach | Anomaly Detector on inter-block arrival times (M4) + Difficulty Predictor (M7) |

## Module Tracking

| Module | What it should include | Status |
|---|---|---|
| M1 | Proof of Work Monitor | Done |
| M2 | Block Header Analyzer | Done |
| M3 | Difficulty History | Done |
| M4 | AI Component — Anomaly Detector | Done |
| M5 | Merkle Proof Verifier | Done |
| M6 | Security Score — 51% attack cost | Done |
| M7 | Second AI Approach — Difficulty Predictor | Done |

## Current Progress

- Implemented all 7 modules (M1–M7), including all 3 optional modules.
- M4: anomaly detector on inter-block arrival times using Z-score and exponential CDF p-value test, evaluated with Precision, Recall and F1.
- M5: full Merkle proof verification step by step using double SHA-256, showing each hash computation.
- M6: 51% attack cost estimation from live hash rate data and confirmation depth probability chart based on Nakamoto (2008) §11.
- M7: difficulty predictor using Linear Regression trained on historical adjustment data, evaluated with MAE, RMSE and R².
- Added API fallback to mempool.space and request caching to handle rate limits from blockstream.info.

## Next Step

- Write the final PDF report and add it to the repository before the deadline.

## Main Problem or Blocker

- Blockstream API rate limits (429 errors) when too many requests are made in a short time. Solved with caching and mempool.space fallback.

## How to Run

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

## Project Structure

```text
blockchain-dashboard-vallesdu/
|-- README.md
|-- requirements.txt
|-- app.py
|-- api/
|   `-- blockchain_client.py
`-- modules/
    |-- m1_pow_monitor.py
    |-- m2_block_header.py
    |-- m3_difficulty_history.py
    |-- m4_ai_component.py
    |-- m5_merkle_verifier.py
    |-- m6_security_score.py
    `-- m7_difficulty_predictor.py
```

<!-- student-repo-auditor:teacher-feedback:start -->
## Teacher Feedback

### Kick-off Review

Review time: 2026-04-29 20:31 CEST
Status: Green

Strength:
- I can see the dashboard structure integrating the checkpoint modules.

Improve now:
- The checkpoint evidence is strong: the dashboard and core modules are visibly progressing.

Next step:
- Keep building on this checkpoint and prepare the final AI integration.
<!-- student-repo-auditor:teacher-feedback:end -->