# CryptoBot — Makefile
# ============================================================

PUML_DIR  := docs/diagrams
SVG_DIR   := $(PUML_DIR)/svg
PNG_DIR   := $(PUML_DIR)/png
PUML_SRC  := $(filter-out $(PUML_DIR)/_common.puml, $(wildcard $(PUML_DIR)/*.puml))

.PHONY: diagrams diagrams-clean diagrams-list

# Triple render: .puml → .svg + .png
diagrams:
	@mkdir -p $(SVG_DIR) $(PNG_DIR)
	plantuml -tsvg -o svg $(PUML_SRC)
	plantuml -tpng -o png $(PUML_SRC)
	@echo "✓ $(words $(PUML_SRC)) diagrams rendered (SVG + PNG)"

# Clean generated output
diagrams-clean:
	rm -rf $(SVG_DIR) $(PNG_DIR)
	@echo "✓ Cleaned generated diagrams"

# List all diagrams
diagrams-list:
	@echo "PlantUML sources ($(words $(PUML_SRC))):"
	@for f in $(PUML_SRC); do echo "  $$f"; done
