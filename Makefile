.PHONY: help clean build test rebuild install dev bench bench-compare bench-baseline

help:
	@echo "Available targets:"
	@echo "  clean          - Remove all build artifacts and compiled modules"
	@echo "  build          - Build C extensions in-place"
	@echo "  rebuild        - Clean and rebuild everything"
	@echo "  test           - Run pytest"
	@echo "  install        - Install package in development mode"
	@echo "  dev            - Clean, rebuild, and run tests"
	@echo ""
	@echo "Benchmarks:"
	@echo "  bench          - Run benchmarks"
	@echo "  bench-compare  - Compare with baseline"
	@echo "  bench-baseline - Set current results as baseline"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/
	rm -f *.so *.dylib *.so.disabled
	rm -f tsrkit_types/*.so tsrkit_types/*.dylib tsrkit_types/*.so.disabled
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete."

build:
	@echo "Building C extensions..."
	python setup.py build_ext --inplace
	@echo "Build complete."

rebuild: clean build

test:
	@echo "Running tests..."
	uv run --frozen pytest

install:
	@echo "Installing in development mode..."
	uv pip install -e ".[dev]"

dev: rebuild test
	@echo "Development setup complete."

# Benchmarks
bench:
	@uv run python benchmarks/bench_types.py --no-profile $(ARGS)

bench-compare:
	@python benchmarks/compare.py benchmarks/out/bench_results.json benchmarks/out/bench_baseline.json

bench-baseline:
	@cp benchmarks/out/bench_results.json benchmarks/out/bench_baseline.json
	@echo "✅ Baseline updated from bench_results.json"
