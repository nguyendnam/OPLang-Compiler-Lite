from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.compiler_service import get_compiler_service


VALID_PROGRAM = """
class Main {
    static void main() {
        io.writeIntLn(10);
    }
}
"""

SEMANTIC_ERROR_PROGRAM = """
class Main {
    static void main() {
        missing := 10;
    }
}
"""


def test_health_reports_real_compiler_status(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "compilerVersion": "0.1.0",
        "compilerCoreInstalled": True,
    }


def test_valid_compilation(client: TestClient) -> None:
    response = client.post("/api/v1/compile", json={"source": VALID_PROGRAM})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["stage"] == "codegen"
    assert "Main.j" in body["jasmin_files"]
    assert body["errors"] == []
    assert body["compilation_time_ms"] >= 0


def test_health_returns_503_when_compiler_is_missing(client: TestClient) -> None:
    class MissingCompilerService:
        def is_available(self) -> bool:
            return False

    app.dependency_overrides[get_compiler_service] = lambda: MissingCompilerService()
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["compilerCoreInstalled"] is False
    assert response.json()["status"] == "unavailable"


def test_parser_error_is_a_domain_result(client: TestClient) -> None:
    response = client.post("/api/v1/compile", json={"source": "class Main {"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["stage"] == "parser"
    assert body["errors"][0]["code"] == "SYNTAX_ERROR"


def test_semantic_error_is_a_domain_result(client: TestClient) -> None:
    response = client.post(
        "/api/v1/compile",
        json={"source": SEMANTIC_ERROR_PROGRAM},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["stage"] == "semantic"
    assert body["errors"][0]["code"] == "UNDECLARED_IDENTIFIER"


def test_empty_source_is_a_parser_result(client: TestClient) -> None:
    response = client.post("/api/v1/compile", json={"source": ""})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["stage"] == "parser"


def test_source_size_limit_is_checked_before_compilation(client: TestClient) -> None:
    response = client.post("/api/v1/compile", json={"source": "x" * 102401})

    assert response.status_code == 413


def test_ast_can_be_omitted(client: TestClient) -> None:
    response = client.post(
        "/api/v1/compile",
        json={
            "source": VALID_PROGRAM,
            "options": {"includeAst": False, "includeJasmin": True},
        },
    )

    assert response.status_code == 200
    assert response.json()["ast"] is None


def test_jasmin_can_be_omitted(client: TestClient) -> None:
    response = client.post(
        "/api/v1/compile",
        json={
            "source": VALID_PROGRAM,
            "options": {"includeAst": True, "includeJasmin": False},
        },
    )

    assert response.status_code == 200
    assert response.json()["jasmin_files"] == {}


def test_internal_error_has_stable_safe_response(client: TestClient) -> None:
    class FailingCompilerService:
        def compile(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError("sensitive internal traceback details")

    app.dependency_overrides[get_compiler_service] = lambda: FailingCompilerService()

    response = client.post("/api/v1/compile", json={"source": VALID_PROGRAM})

    assert response.status_code == 500
    assert response.json() == {
        "detail": {
            "code": "INTERNAL_COMPILER_ERROR",
            "message": "Compilation failed unexpectedly.",
        }
    }
    assert "sensitive" not in response.text
