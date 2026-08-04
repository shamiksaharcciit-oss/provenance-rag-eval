# RAG Semantic Formatter Evaluation Harness
# Windows note: use `make` from Git Bash, or run the underlying python commands directly.

PYTHON ?= python
TRACK  ?= A

.PHONY: setup test smoke run report clean

setup:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest -q

# Zero paid LLM calls: uses the rule-based formatter stub (llm.provider=none)
smoke:
	$(PYTHON) -m src.run --track A --provider none --smoke

# Full run for a track (respects config; may use paid LLM if provider configured)
# NOTE: this uses the config default embedder (BAAI/bge-base-en-v1.5). The PUBLISHED v1.1
# numbers used the speed fallback — to reproduce them, add:
#     --embedding-model all-MiniLM-L6-v2
# Absolute numbers differ between the two embedders; see config/default.yaml.
run:
	$(PYTHON) -m src.run --track $(TRACK)

report:
	$(PYTHON) -m src.run --report-only

clean:
	rm -rf results/runs/* cache/* data/generated/*
