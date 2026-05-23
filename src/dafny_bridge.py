"""Dafny CLI bridge — verify, compile, and run Dafny programs."""

import subprocess
import tempfile
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VerifyResult:
    success: bool
    output: str
    errors: list[str]
    file_path: str


@dataclass
class RunResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int


class DafnyBridge:
    DEFAULT_Z3_PATH = os.path.expanduser(
        "~/.dotnet/tools/z3/bin/z3-4.12.1.exe"
    )

    def __init__(
        self, dafny_path: str = "dafny", timeout: int = 30,
        solver_path: Optional[str] = None
    ):
        self.timeout = timeout

        # Auto-detect dafny on Windows
        dotnet_tools = os.path.expanduser("~/.dotnet/tools")
        if dafny_path == "dafny" and os.path.exists(os.path.join(dotnet_tools, "dafny.exe")):
            dafny_path = os.path.join(dotnet_tools, "dafny.exe")
            # Ensure dotnet is on PATH for dafny subprocess
            dotnet_dir = r"C:\Program Files\dotnet"
            if dotnet_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = dotnet_dir + os.pathsep + os.environ["PATH"]
        self.dafny_path = dafny_path

        # Auto-detect Z3 on Windows
        self.solver_path = solver_path
        if not self.solver_path and os.path.exists(self.DEFAULT_Z3_PATH):
            self.solver_path = self.DEFAULT_Z3_PATH
        self._verify_installation()

    def _verify_installation(self):
        """Check Dafny is accessible."""
        try:
            result = subprocess.run(
                [self.dafny_path, "--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"Dafny not working: {result.stderr}")
            self.version = result.stdout.strip()
            print(f"[DafnyBridge] Found Dafny: {self.version}")
        except FileNotFoundError:
            raise RuntimeError(
                "Dafny not found. Install: dotnet tool install -g dafny"
            )

    def verify(self, dafny_code: str, filename: str = "test.dfy") -> VerifyResult:
        """Verify a Dafny program. Returns VerifyResult."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w") as f:
                f.write(dafny_code)

            try:
                cmd = [self.dafny_path, "verify"]
                if self.solver_path:
                    cmd.extend(["--solver-path", self.solver_path])
                cmd.append(filepath)
                result = subprocess.run(
                    cmd,
                    capture_output=True, text=True, timeout=self.timeout
                )
                errors = self._parse_errors(result.stdout + result.stderr)
                return VerifyResult(
                    success=result.returncode == 0,
                    output=result.stdout + result.stderr,
                    errors=errors,
                    file_path=filepath
                )
            except subprocess.TimeoutExpired:
                return VerifyResult(
                    success=False,
                    output="TIMEOUT",
                    errors=["Verification timed out"],
                    file_path=filepath
                )

    def verify_file(self, filepath: str) -> VerifyResult:
        """Verify an existing Dafny file."""
        try:
            cmd = [self.dafny_path, "verify"]
            if self.solver_path:
                cmd.extend(["--solver-path", self.solver_path])
            cmd.append(filepath)
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=self.timeout
            )
            errors = self._parse_errors(result.stdout + result.stderr)
            return VerifyResult(
                success=result.returncode == 0,
                output=result.stdout + result.stderr,
                errors=errors,
                file_path=filepath
            )
        except subprocess.TimeoutExpired:
            return VerifyResult(
                success=False,
                output="TIMEOUT",
                errors=["Verification timed out"],
                file_path=filepath
            )

    def compile_and_run(
        self, dafny_code: str, target: str = "py",
        filename: str = "test.dfy"
    ) -> RunResult:
        """Compile Dafny to target language and run it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w") as f:
                f.write(dafny_code)

            # Build
            out_dir = os.path.join(tmpdir, "out")
            os.makedirs(out_dir, exist_ok=True)

            try:
                build_cmd = [self.dafny_path, "build", f"--target:{target}"]
                if self.solver_path:
                    build_cmd.extend(["--solver-path", self.solver_path])
                build_cmd.extend([filepath, f"--output:{os.path.join(out_dir, 'program')}"])
                build_result = subprocess.run(
                    build_cmd,
                    capture_output=True, text=True, timeout=self.timeout
                )
                if build_result.returncode != 0:
                    return RunResult(
                        success=False,
                        stdout=build_result.stdout,
                        stderr=f"Build failed: {build_result.stderr}",
                        exit_code=build_result.returncode
                    )

                # Run
                if target == "py":
                    run_cmd = ["python3", os.path.join(out_dir, "program.py")]
                elif target == "cs":
                    run_cmd = ["dotnet", "run", "--project", out_dir]
                else:
                    return RunResult(
                        success=False, stdout="",
                        stderr=f"Unsupported target: {target}", exit_code=1
                    )

                run_result = subprocess.run(
                    run_cmd, capture_output=True, text=True, timeout=self.timeout
                )
                return RunResult(
                    success=run_result.returncode == 0,
                    stdout=run_result.stdout,
                    stderr=run_result.stderr,
                    exit_code=run_result.returncode
                )
            except subprocess.TimeoutExpired:
                return RunResult(
                    success=False, stdout="",
                    stderr="Execution timed out", exit_code=-1
                )

    def _parse_errors(self, output: str) -> list[str]:
        """Extract error messages from Dafny output."""
        errors = []
        for line in output.split("\n"):
            if "Error" in line or "error" in line:
                errors.append(line.strip())
        return errors


def extract_spec_from_file(filepath: str) -> dict:
    """Parse a Dafny file and extract spec components."""
    with open(filepath) as f:
        content = f.read()

    # Extract intent from comment
    intent_match = re.search(r"// Intent: (.+)", content)
    intent = intent_match.group(1) if intent_match else ""

    # Extract method signature + spec (everything before the body)
    # Find method declaration up to opening brace
    method_match = re.search(
        r"(method\s+\w+.*?)\{", content, re.DOTALL
    )
    spec = method_match.group(1).strip() if method_match else content

    # Extract known gap from comment
    gap_match = re.search(r"// (?:Known gap|MISSING): (.+)", content)
    known_gap = gap_match.group(1) if gap_match else ""

    return {
        "intent": intent,
        "spec": spec,
        "known_gap": known_gap,
        "full_content": content,
        "filepath": filepath
    }
