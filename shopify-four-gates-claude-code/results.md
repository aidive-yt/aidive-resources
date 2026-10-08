# gate-bench results

50 runs scored (matrix runs only).

## Per config

| cfg | runs | hidden reqs | fully passing | suite green | mean $ total (worker + g1 writer + g3 reviewers) | mean wall s | blocks/run | g1 right/false | g3 right/false | give-ups | ended blocked | model ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bare | 10 | 35/50 (70%) | 3 | 10 | 0.085 (0.085 + 0.000 + 0.000) | 33 | 0.00 | 0/0 | 0/0 | 0 | 0 | True |
| g1 | 10 | 42/50 (84%) | 6 | 10 | 0.201 (0.130 + 0.071 + 0.000) | 60 | 0.60 | 3/3 | 0/0 | 0 | 0 | True |
| g3 | 10 | 34/50 (68%) | 3 | 10 | 0.151 (0.094 + 0.000 + 0.058) | 54 | 0.10 | 0/0 | 1/0 | 0 | 0 | True |
| g13 | 10 | 41/50 (82%) | 5 | 10 | 0.282 (0.153 + 0.071 + 0.057) | 86 | 1.70 | 14/1 | 2/0 | 2 | 0 | True |
| g13adv | 10 | 39/50 (78%) | 6 | 10 | 0.276 (0.157 + 0.072 + 0.048) | 86 | 1.20 | 11/1 | 0/0 | 1 | 0 | True |

## Per task (hidden reqs passed / total, per config)

| task | bare | g1 | g3 | g13 | g13adv | missed reqs (all configs) |
|---|---|---|---|---|---|---|
| T1 | 4/10, $0.08, 0.0 blk | 4/10, $0.22, 0.5 blk | 3/10, $0.16, 0.5 blk | 4/10, $0.36, 3.0 blk | 5/10, $0.31, 1.0 blk | T1:test_req2, T1:test_req3, T1:test_req4, T1:test_req5 |
| T2 | 8/10, $0.10, 0.0 blk | 8/10, $0.17, 0.0 blk | 8/10, $0.17, 0.0 blk | 8/10, $0.27, 3.0 blk | 9/10, $0.30, 3.5 blk | T2:test_req4 |
| T3 | 10/10, $0.09, 0.0 blk | 10/10, $0.21, 1.0 blk | 10/10, $0.14, 0.0 blk | 10/10, $0.26, 0.5 blk | 10/10, $0.31, 0.5 blk |  |
| T4 | 5/10, $0.07, 0.0 blk | 10/10, $0.23, 0.5 blk | 5/10, $0.15, 0.0 blk | 10/10, $0.30, 1.0 blk | 5/10, $0.21, 0.0 blk | T4:test_req1, T4:test_req2, T4:test_req3, T4:test_req4, T4:test_req5 |
| T5 | 8/10, $0.08, 0.0 blk | 10/10, $0.18, 1.0 blk | 8/10, $0.12, 0.0 blk | 9/10, $0.23, 1.0 blk | 10/10, $0.25, 1.0 blk | T5:test_req4 |

## The video's questions

- **q1_gate1_vs_bare**: `{"bare": 0.7, "g1": 0.84, "delta": 0.14}`
- **q2_gate3_over_g1**: `{"g1": 0.84, "g13": 0.82, "delta": -0.02, "g3_alone": 0.68, "g3_vs_bare": -0.02}`
- **q3_adv_vs_indep**: `{"g13": 0.82, "g13adv": 0.78, "delta": -0.04, "false_blocks_g3": {"g13": 0, "g13adv": 0}}`
- **q4_false_block_rate**: `{"bare": {"g1": null, "g3": null}, "g1": {"g1": 0.5, "g3": null}, "g3": {"g1": null, "g3": 0.0}, "g13": {"g1": 0.067, "g3": 0.0}, "g13adv": {"g1": 0.083, "g3": null}}`
- **q4_gate1_false_blocks**: `{"g1": {"false": 3, "right": 3}, "g13": {"false": 1, "right": 14}, "g13adv": {"false": 1, "right": 11}}`
- **q5_cost**: `{"bare": {"mean_cost_total_usd": 0.0849, "mean_cost_worker_usd": 0.0849, "mean_cost_gate1_usd": 0.0, "mean_cost_gate3_usd": 0.0, "mean_wall_s": 32.7}, "g1": {"mean_cost_total_usd": 0.201, "mean_cost_worker_usd": 0.1302, "mean_cost_gate1_usd": 0.0709, "mean_cost_gate3_usd": 0.0, "mean_wall_s": 59.5}, "g3": {"mean_cost_total_usd": 0.1513, "mean_cost_worker_usd": 0.0938, "mean_cost_gate1_usd": 0.0, "mean_cost_gate3_usd": 0.0575, "mean_wall_s": 54.1}, "g13": {"mean_cost_total_usd": 0.2818, "mean_cost_worker_usd": 0.1534, "mean_cost_gate1_usd": 0.0712, "mean_cost_gate3_usd": 0.0573, "mean_wall_s": 86.4}, "g13adv": {"mean_cost_total_usd": 0.2763, "mean_cost_worker_usd": 0.1568, "mean_cost_gate1_usd": 0.0718, "mean_cost_gate3_usd": 0.0478, "mean_wall_s": 85.9}}`

Gate 1 false blocks (gate 1 blocked while the hidden oracle was fully green): g1 3/6, g13 1/15, g13adv 1/12 (false / all g1 blocks).

Right block = the hidden oracle had at least one failing requirement at that stop; false block = the oracle was fully green at that stop (the gate sent the agent back for nothing the user asked for).
