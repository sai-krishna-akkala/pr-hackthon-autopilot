# Sample PR Target Repo

A minimal Python repository to demo Code Review Autopilot on pull requests.

## Structure

- `src/pricing.py` - discount and tax calculations
- `src/order_service.py` - order total orchestration
- `src/config.py` - runtime settings model
- `tests/test_pricing.py` - basic unit tests

## Run locally

```bash
pip install -r requirements.txt
pytest -q
```

## Suggested demo PR ideas

1. Change discount logic in `pricing.py`.
2. Add a new fee in `order_service.py`.
3. Update tests partially (leave one case missing).
4. Introduce a config change in `config.py`.

These changes give the bot good cross-file context to review.
