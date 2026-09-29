# Structured scoring and explanation checks

## Hint-based fit vs annotator labels (hard conditions)

Gold = annotator status of the condition for that job. low = fit <= 0.15 (would be deferred), high = fit >= 0.85.

| condition | labelled | graded | gold satisfied/violated/unstated overall | low: sat/viol/unst | high: sat/viol/unst |
|---|---|---|---|---|---|
| work_region | 193 | 125 | 50/135/8 | 15/76/1 | 31/1/1 |
| salary | 74 | 35 | 26/7/41 | 1/1/1 | 23/2/6 |
| remote_mode | 83 | 83 | 49/22/12 | 0/15/0 | 47/2/0 |

## Rank-change explanation after the user relaxes one hard condition to a soft preference (weight 0.5)

| query | relaxed | verified | kept before -> after | rank moved | moved: reasons sum to true score change | moved: reason names the relaxed condition | entered | entered: reason names it |
|---|---|---|---|---|---|---|---|---|
| d01 | work_region | 20 | 4 -> 18 | 0 | 0/0 | 0/0 | 14 | 14/14 |
| d02 | remote_mode | 20 | 3 -> 6 | 0 | 0/0 | 0/0 | 3 | 3/3 |
| d03 | work_region | 20 | 8 -> 18 | 6 | 6/6 | 6/6 | 10 | 10/10 |
| d04 | seniority | 20 | 5 -> 5 | 0 | 0/0 | 0/0 | 0 | 0/0 |
| d05 | work_region | 20 | 1 -> 12 | 0 | 0/0 | 0/0 | 11 | 11/11 |
| d06 | employment_type | 20 | 1 -> 1 | 0 | 0/0 | 0/0 | 0 | 0/0 |
| d07 | remote_mode | 19 | 11 -> 18 | 8 | 8/8 | 8/8 | 7 | 7/7 |
| d08 | work_region | 20 | 4 -> 15 | 4 | 4/4 | 4/4 | 11 | 11/11 |
| h01 | remote_mode | 20 | 16 -> 18 | 16 | 16/16 | 16/16 | 2 | 2/2 |
| h02 | work_region | 20 | 7 -> 14 | 5 | 5/5 | 5/5 | 7 | 7/7 |
| h03 | work_region | 20 | 3 -> 12 | 0 | 0/0 | 0/0 | 9 | 9/9 |
| h04 | remote_mode | 20 | 1 -> 4 | 0 | 0/0 | 0/0 | 3 | 3/3 |
| h05 | remote_mode | 20 | 1 -> 5 | 0 | 0/0 | 0/0 | 4 | 4/4 |
| h06 | work_region | 20 | 5 -> 12 | 4 | 4/4 | 4/4 | 7 | 7/7 |
| h08 | seniority | 20 | 2 -> 2 | 0 | 0/0 | 0/0 | 0 | 0/0 |
| total | | | | 43 | 43/43 | 43/43 | 88 | 88/88 |
