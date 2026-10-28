

from studio.validation import MAX_ATTEMPTS, route


def test_no_errors_routes_to_format_output():
    state = {"errors": [], "attempts": 1}
    assert route(state) == "format_output"


def test_errors_at_retry_boundary_route_to_extraction():
    state = {
        "errors": ["x"],
        "attempts": MAX_ATTEMPTS - 1,
    }
    assert route(state) == "extract_fields"

def test_errors_before_retry_boundary_route_to_extraction():
    state = {"errors": ["x"], "attempts": 1}
    assert route(state) == "extract_fields"

def test_errors_at_attempt_limit_route_to_human():
    state = {
        "errors": ["x"],
        "attempts": MAX_ATTEMPTS,
    }
    assert route(state) == "flag_for_human"
