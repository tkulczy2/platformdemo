"""Shared fixtures for VBC demo tests."""

import json
from pathlib import Path

import pandas as pd
import pytest

from engine.data_loader import LoadedData, load_demo_data
from generator.config import GenerationConfig


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
CONTRACTS_DIR = DATA_DIR / "contracts"


@pytest.fixture(scope="session")
def config():
    """Default generation config (seed=42)."""
    return GenerationConfig()


@pytest.fixture(scope="session")
def demo_data() -> LoadedData:
    """Load the pre-generated synthetic demo data."""
    return load_demo_data()


@pytest.fixture(scope="session")
def contract() -> dict:
    """Load the sample MSSP contract."""
    with open(CONTRACTS_DIR / "sample_mssp_contract.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def payer_report() -> dict:
    """Load the payer settlement report."""
    with open(SYNTHETIC_DIR / "payer_settlement_report.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def discrepancy_manifest() -> dict:
    """Load the discrepancy manifest (for validation only)."""
    with open(SYNTHETIC_DIR / "discrepancy_manifest.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def pipeline_result(demo_data, contract, payer_report):
    """Run the full pipeline once for the session."""
    from engine.pipeline import CalculationPipeline

    pipeline = CalculationPipeline()
    return pipeline.run(demo_data, contract, payer_report)
