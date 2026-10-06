from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from .exceptions import CompilerCoreNotInstalled
from .result import CompilationResult, CompilerError
from .serializer import serialize_ast


class OPLangCompiler:
    def __init__(
        self,
        project_root: Path | None = None
    ) -> None:
        self.project_root = (
            project_root
            or Path(__file__).resolve().parents[1]
        )

    def is_installed(self) -> bool:
        required = [
            self.project_root
            / "src"
            / "grammar"
            / "OPLang.g4",

            self.project_root
            / "src"
            / "astgen"
            / "ast_generation.py",

            self.project_root
            / "src"
            / "semantics"
            / "static_checker.py",

            self.project_root
            / "src"
            / "codegen"
            / "codegen.py",

            self.project_root
            / "build"
            / "OPLangLexer.py",

            self.project_root
            / "build"
            / "OPLangParser.py",

            self.project_root
            / "build"
            / "OPLangVisitor.py",

            self.project_root
            / "build"
            / "lexererr.py",
        ]

        return all(path.exists() for path in required)

    def _prepare_import_paths(self) -> None:
        paths = [
            self.project_root,
            self.project_root / "build",
        ]

        for path in paths:
            value = str(path)

            if value not in sys.path:
                sys.path.insert(0, value)

    def _elapsed_ms(self, started: float) -> float:
        return (
            time.perf_counter() - started
        ) * 1000

    def _error_result(
        self,
        started: float,
        *,
        stage: str,
        code: str,
        message: str,
        line: int | None = None,
        column: int | None = None,
    ) -> CompilationResult:

        return CompilationResult(
            success=False,
            stage=stage,
            errors=[
                CompilerError(
                    stage=stage,
                    code=code,
                    message=message,
                    line=line,
                    column=column,
                )
            ],
            compilation_time_ms=self._elapsed_ms(started),
        )

    def _semantic_error_code(
        self,
        exc: Exception
    ) -> str:

        name = exc.__class__.__name__

        return re.sub(
            r"(?<!^)(?=[A-Z])",
            "_",
            name,
        ).upper()

    def compile(
        self,
        source: str,
        *,
        include_ast: bool = True,
        include_jasmin: bool = True,
    ) -> CompilationResult:

        started = time.perf_counter()

        if not self.is_installed():
            raise CompilerCoreNotInstalled(
                "Compiler implementation is not installed "
                "or ANTLR has not been generated."
            )

        self._prepare_import_paths()

        from antlr4 import (
            InputStream,
            CommonTokenStream,
        )

        # Must match the module imported by generated lexer.
        from lexererr import (
            ErrorToken,
            UncloseString,
            IllegalEscape,
        )

        from build.OPLangLexer import OPLangLexer
        from build.OPLangParser import OPLangParser

        from src.utils.error_listener import (
            NewErrorListener,
            SyntaxException,
        )

        from src.astgen.ast_generation import ASTGeneration

        from src.semantics.static_checker import (
            StaticChecker,
        )

        from src.semantics.static_error import (
            StaticError,
        )

        from src.codegen.codegen import CodeGenerator

        # --------------------------------
        # Lexer + Parser
        # --------------------------------

        try:
            input_stream = InputStream(source)

            lexer = OPLangLexer(
                input_stream
            )

            token_stream = CommonTokenStream(
                lexer
            )

            parser = OPLangParser(
                token_stream
            )

            parser.removeErrorListeners()

            parser.addErrorListener(
                NewErrorListener.INSTANCE
            )

            parse_tree = parser.program()

        except ErrorToken as exc:
            return self._error_result(
                started,
                stage="lexer",
                code="ERROR_TOKEN",
                message=str(exc),
            )

        except UncloseString as exc:
            return self._error_result(
                started,
                stage="lexer",
                code="UNCLOSED_STRING",
                message=str(exc),
            )

        except IllegalEscape as exc:
            return self._error_result(
                started,
                stage="lexer",
                code="ILLEGAL_ESCAPE",
                message=str(exc),
            )

        except SyntaxException as exc:
            message = str(exc)

            line = None
            column = None

            match = re.search(
                r"line\s+(\d+)\s+col\s+(\d+)",
                message,
            )

            if match:
                line = int(match.group(1))
                column = int(match.group(2))

            return self._error_result(
                started,
                stage="parser",
                code="SYNTAX_ERROR",
                message=message,
                line=line,
                column=column,
            )

        # --------------------------------
        # AST
        # --------------------------------

        try:
            ast = ASTGeneration().visit(
                parse_tree
            )

        except Exception as exc:
            return self._error_result(
                started,
                stage="ast",
                code="AST_GENERATION_ERROR",
                message=str(exc),
            )

        # --------------------------------
        # Semantic checking
        # --------------------------------

        try:
            checker = StaticChecker()

            checker.check_program(
                ast
            )

        except StaticError as exc:
            return self._error_result(
                started,
                stage="semantic",
                code=self._semantic_error_code(exc),
                message=str(exc),
            )

        except Exception as exc:
            return self._error_result(
                started,
                stage="semantic",
                code="SEMANTIC_INTERNAL_ERROR",
                message=str(exc),
            )

        # --------------------------------
        # Code generation
        # --------------------------------

        try:
            with TemporaryDirectory(
                prefix="oplang-"
            ) as workdir:

                generator = CodeGenerator(
                    output_dir=workdir
                )

                generator.visit(ast)

                jasmin_files = {
                    path.name: path.read_text(
                        encoding="utf-8"
                    )
                    for path
                    in Path(workdir).glob("*.j")
                }

        except Exception as exc:
            return self._error_result(
                started,
                stage="codegen",
                code="CODE_GENERATION_ERROR",
                message=str(exc),
            )

        return CompilationResult(
            success=True,
            stage="codegen",
            ast=(
                serialize_ast(ast)
                if include_ast
                else None
            ),
            jasmin_files=(
                jasmin_files
                if include_jasmin
                else {}
            ),
            errors=[],
            compilation_time_ms=
                self._elapsed_ms(started),
        )
