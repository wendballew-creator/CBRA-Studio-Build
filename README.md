# Creative Becoming Reasoning Architecture (CBRA)

CBRA is a research instrument that asks whether a language-model system can form a response relationally, as something that changes with what arrives. It pairs a Python runtime, where a model's proposals enter as material checked against 16 structural constraints, with an evaluation record that includes documented failures and a written claim boundary for each build.

**Start here: [METHODOLOGY.md](METHODOLOGY.md)**, a one-page account of the evaluation design, the probe set, the measurement runs, and the findings.

## Where the work is

| Branch | Contents |
|---|---|
| [`enactment/first-slice`](https://github.com/wendballew-creator/CBRA-Studio-Build/tree/enactment/first-slice) | Current runtime (`cbra/enactment/`), measurement harness and reports, behavioral evaluation records, build history (February to November 2026) |
| `main` (this branch) | This overview and the February 2026 prototype it started from |

## Running it

On `enactment/first-slice`, with Python 3.9 or later and an OpenAI API key in the environment:

```
pip install -r requirements.txt
python -m unittest discover -s cbra -p 'test_*.py'
python -m cbra.enactment.serve --port 8765
```

The measurement harness runs with `python -m cbra.enactment.measure run`. Each live turn makes several provider calls.

## Author

Wend Ballew, PhD, evaluation methodologist · [linkedin.com/in/wendballew](https://www.linkedin.com/in/wendballew)
