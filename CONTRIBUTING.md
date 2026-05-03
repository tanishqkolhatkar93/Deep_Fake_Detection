# Contributing

## Setup

```powershell
python -m pip install -r requirements.txt
```

Run the API locally:

```powershell
python -m uvicorn api:app --reload
```

Run the local admin UI:

```powershell
python -m streamlit run app.py
```

## Before opening a pull request

Run:

```powershell
python -m compileall src app.py api.py detect.py tests
python -m pytest
```

## Contribution standards

- Keep changes scoped and reviewable.
- Preserve upload validation and public deployment safety.
- Do not commit secrets, local checkpoints, or `.env`.
- If you change the website, verify the GitHub Pages output still works with the live API.
- If you change the API contract, update the website client and docs in the same pull request.
