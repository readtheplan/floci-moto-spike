from floci_cli.plan_generator import generate_plan_json


def test_generates_valid_plan_structure():
    resources = [
        {"type": "aws_s3_bucket", "name": "logs", "attributes": {"bucket": "logs"}}
    ]
    plan = generate_plan_json(resources)

    assert plan["format_version"] == "1.2"
    assert len(plan["resource_changes"]) == 1
    assert plan["resource_changes"][0]["type"] == "aws_s3_bucket"
