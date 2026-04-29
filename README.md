[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/N3kLi3ZO)
[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=23640558&assignment_repo_type=AssignmentRepo)
# Blockchain Dashboard Project

Use this repository to build your blockchain dashboard project.
Update this README every week.

## Student Information

| Field | Value |
|---|---|
| Student Name | Eduardo Vallejo |
| GitHub Username | vallesdu |
| Project Title | Bitcoin Live Metrics & AI Insights |
| Chosen AI Approach | Anomaly Detector on inter-block arrival times |

## Module Tracking

Use one of these values: `Not started`, `In progress`, `Done`

| Module | What it should include | Status |
|---|---|---|
| M1 | Proof of Work Monitor | Done|
| M2 | Block Header Analyzer | Done |
| M3 | Difficulty History | Done |
| M4 | AI Component | Done |

## Current Progress

Write 3 to 5 short lines about what you have already done.

- Implemented M1: live difficulty, estimated hash rate, hash vs target visualization, and inter-block time histogram.

- Implemented M2: full 80-byte header breakdown, bits→target conversion, and local Proof of Work verification using hashlib.

- Implemented M3: difficulty history chart over last adjustment periods, block time ratio per period, and summary table.

- Implemented M4: anomaly detector on inter-block arrival times using Z-score and exponential CDF p-value, with model evaluation metrics.

- Added API fallback to mempool.space and request caching to handle rate limits from blockstream.info.

## Next Step

Write the next small step you will do before the next class.

- Polish the dashboard visuals and test all four modules end to end

## Main Problem or Blocker

Write here if you are stuck with something.

- Blockstream API rate limits (429 errors) when too many requests are made in a short time. Solved with caching and mempool.space fallback.

## How to Run

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

## Project Structure

```text
template-blockchain-dashboard/
|-- README.md
|-- requirements.txt
|-- .gitignore
|-- app.py
|-- api/
|   `-- blockchain_client.py
`-- modules/
    |-- m1_pow_monitor.py
    |-- m2_block_header.py
    |-- m3_difficulty_history.py
    `-- m4_ai_component.py
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
