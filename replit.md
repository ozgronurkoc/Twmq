# Spor Toto 14-Garanti Formül Üreticisi

A Python CLI tool that generates minimum-cost covering codes (14-guarantee) for Spor Toto lottery coupons.

## How to run

The `spor-toto` CLI is installed and ready. Use the **spor-toto** workflow to run it, or execute directly in the Shell:

```bash
spor-toto --picks "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"
```

### Picks format
15 matches separated by commas. Each match's selections are written together:
- `1` = home win only
- `0` = draw only
- `2` = away win only
- `10` = home or draw (double)
- `02` = draw or away (double)
- `12` = home or away (double)
- `102` = all three (triple)

### Modes

```bash
spor-toto --picks "..." --mode auto       # cheapest solution, variable rows
spor-toto --picks "..." --mode exact      # ILP-proven optimal (small spaces)
spor-toto --picks "..." --mode heuristic  # greedy + local search (large spaces)
spor-toto --picks "..." --mode butce --budget 32   # budget advisor
spor-toto --picks "..." --mode maxcov --budget 16  # max coverage, no guarantee
spor-toto --picks "..." --variant 3       # alternate set of 16 rows
```

## Stack

- Python 3.10
- numpy, scipy (for ILP exact solver)
- Entry point: `spor_toto/cli.py`
- Tests: `pytest` (434 tests, ~70s full run; `pytest -m "not slow"` for fast subset)

## User preferences
