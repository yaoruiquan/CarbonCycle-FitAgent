from app.agent.router import should_adjust, should_continue_to_reflect, should_skip_after_planner


def test_actor_error_routes_to_verifier():
    assert should_continue_to_reflect({"error": "failed"}) == "verify"


def test_no_data_routes_to_verifier():
    assert should_continue_to_reflect({"actor_output": {"status": "no_data"}}) == "verify"


def test_reflector_error_routes_to_verifier():
    assert should_adjust({"error": "failed"}) == "verify"


def test_planner_error_skips_downstream_nodes():
    assert should_skip_after_planner({"error": "planner failed", "trigger": "harness_case"}) == "skip"
