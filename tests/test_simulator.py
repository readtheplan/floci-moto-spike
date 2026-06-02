"""Tests for floci_cli.simulator."""
import pytest
from floci_cli.simulator import FakeAwsSimulator, RESOURCE_TYPES


def test_simulator_creates_s3_bucket():
    sim = FakeAwsSimulator(region="us-east-1")
    sim.start()
    resources = sim.provision([
        {"type": "aws_s3_bucket", "name": "my-logs-bucket"},
    ])
    sim.stop()

    assert len(resources) == 1
    assert resources[0]["type"] == "aws_s3_bucket"
    assert resources[0]["attributes"]["bucket"] == "my-logs-bucket"


def test_simulator_rejects_unsupported_type():
    sim = FakeAwsSimulator()
    sim.start()
    with pytest.raises(ValueError):
        sim.provision([{"type": "aws_lambda_function", "name": "test"}])
    sim.stop()
