from __future__ import annotations

from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.services.secret_mining import mine_scan
from shared.services.secret_mining.run import BUSY
from shared.utils.text import counted
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.secret_mining.config import SecretMiningConfig
from tools.runner.abort import StageAbortedError

logger = get_logger(__name__)


class SecretMiningStage(Stage):
    name = "secret_mining"
    title = "Response secret mining"
    description = (
        "Credentials, tokens, keys and contacts read from stored responses. "
        "No request is sent."
    )
    phase = Phase.DEPTH.value
    depends_on = frozenset({"http_probe"})
    group = StageGroup.ANALYSIS.value
    role = StageRole.CAPABILITY.value
    consumes = frozenset({AssetKind.HTTP_ASSETS.value})
    produces = frozenset({AssetKind.SECRETS.value})
    applies_to = ALL_TARGETS
    touches_target = False
    config_model = SecretMiningConfig

    def _aborted(self) -> bool:
        return self.ctx.is_aborted is not None and self.ctx.is_aborted()

    def run(self) -> StageResult:
        self._check_abort()
        outcome = mine_scan(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            aborted=self._aborted,
            on_progress=self.emit_progress,
            announce=lambda: self.publish_results(SurfaceDimension.SECRETS.value),
        )
        self.publish_results(SurfaceDimension.SECRETS.value)
        if outcome.aborted:
            raise StageAbortedError
        if outcome.busy:
            return StageResult(counts={}, warnings=[BUSY], partial=True)
        warnings: list[str] = []
        if outcome.truncated:
            warnings.append(
                f"{counted(outcome.truncated, 'response')} truncated at the body cap."
            )
        self.emit_progress(
            f"{outcome.secrets:,} secrets from {outcome.documents_read:,} responses"
        )
        return StageResult(
            counts={"secrets": outcome.secrets, "documents": outcome.documents_read},
            warnings=warnings,
        )
