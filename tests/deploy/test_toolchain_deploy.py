import re
from pathlib import Path

import pytest

from shared.definitions.toolchain import TOOLCHAIN, PinKind

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "worker" / "Dockerfile"

pytestmark = pytest.mark.skipif(
    not DOCKERFILE.is_file(), reason="deployment files are not mounted here"
)

GO_PIN = re.compile(r"go install -v (\S+)@(\S+)")
ARG_PIN = re.compile(r"^ARG (\w+_VERSION)=(\S+)$", re.MULTILINE)
PIP_PIN = re.compile(r"pip install [^\n]*?(\S+)==(\S+)")
NOT_TOOLS = {"RENGINE_VERSION"}


def _dockerfile_pins() -> dict[tuple[PinKind, str], str]:
    text = DOCKERFILE.read_text()
    pins = {(PinKind.GO, module): version for module, version in GO_PIN.findall(text)}
    pins |= {
        (PinKind.RELEASE, arg): version
        for arg, version in ARG_PIN.findall(text)
        if arg not in NOT_TOOLS
    }
    pins |= {(PinKind.PIP, pkg): version for pkg, version in PIP_PIN.findall(text)}
    return pins


def test_the_toolchain_matches_every_pin_in_the_worker_image():
    declared = {(tool.kind, tool.pin): tool.version for tool in TOOLCHAIN}
    assert declared == _dockerfile_pins()


def test_the_dockerfile_parse_finds_each_kind_of_pin():
    kinds = {kind for kind, _ in _dockerfile_pins()}
    assert kinds == set(PinKind)


def test_tool_names_are_unique():
    names = [tool.name for tool in TOOLCHAIN]
    assert len(names) == len(set(names))
