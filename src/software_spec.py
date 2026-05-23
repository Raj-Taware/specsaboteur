"""Software specification loader — reads YAML spec files for Layer 2."""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SoftwareSpec:
    """A software specification (non-Dafny)."""
    domain: str
    language: str
    intent: str
    spec_text: str
    test_cases: list[dict] = field(default_factory=list)
    known_gap: str = ""
    filepath: str = ""

    @property
    def name(self) -> str:
        return Path(self.filepath).stem if self.filepath else f"{self.domain}_{self.language}"


def load_software_spec(filepath: str) -> SoftwareSpec:
    """Load a single software spec from YAML."""
    with open(filepath) as f:
        data = yaml.safe_load(f)

    return SoftwareSpec(
        domain=data.get("domain", "unknown"),
        language=data.get("language", "python"),
        intent=data.get("intent", ""),
        spec_text=data.get("spec", ""),
        test_cases=data.get("test_cases", []),
        known_gap=data.get("known_gap", ""),
        filepath=filepath
    )


def load_all_software_specs(directory: str = "specs/software") -> list[SoftwareSpec]:
    """Load all software specs from directory."""
    specs = []
    if not os.path.isdir(directory):
        print(f"[SoftwareSpec] Directory not found: {directory}")
        return specs

    for f in sorted(os.listdir(directory)):
        if f.endswith((".yaml", ".yml")):
            try:
                spec = load_software_spec(os.path.join(directory, f))
                specs.append(spec)
                print(f"[SoftwareSpec] Loaded: {f} ({spec.domain}/{spec.language})")
            except Exception as e:
                print(f"[SoftwareSpec] Failed to load {f}: {e}")
    return specs
