from __future__ import annotations

import pytest

from shared.definitions.cloud_storage import (
    GUESSABLE_PROVIDERS,
    OPEN_ACCESS,
    OWNED_SOURCES,
    Access,
    Provider,
    Source,
)
from shared.services import cloud_storage
from shared.services.cloud_storage import Candidate
from stages.cloud_storage.config import CloudStorageConfig
from stages.registry import get_stage

pytestmark = pytest.mark.pipeline


def test_the_stage_is_off_by_default_and_applies_to_domains():
    cfg = CloudStorageConfig()
    assert cfg.enabled is False
    spec = get_stage("cloud_storage")
    assert spec is not None
    assert "domain" in spec.stage_cls.applies_to


def test_guessed_names_join_the_label_with_each_word():
    names = cloud_storage.guessed_names("example", ["backup"])
    assert "example" in names
    assert "example-backup" in names
    assert "backup-example" in names
    assert "example.backup" in names


def test_candidates_keep_a_name_once_at_its_strongest_source():
    referenced = [
        Candidate("example-assets", Source.REFERENCED.value, Provider.AWS_S3.value)
    ]
    found = cloud_storage.candidates(
        label="example",
        hostnames=["example-assets", "cdn"],
        referenced=referenced,
        words=["assets"],
        guess=True,
    )
    by_name = {(c.provider, c.name): c for c in found.items}
    # The referenced AWS bucket keeps its provider and its strong source.
    assert by_name[(Provider.AWS_S3.value, "example-assets")].source == (
        Source.REFERENCED.value
    )
    # A provider-less hostname is still offered to every guessable provider.
    assert (None, "cdn") in by_name
    assert by_name[(None, "cdn")].source == Source.HOSTNAME.value


def test_passive_guess_off_keeps_only_referenced():
    referenced = [
        Candidate("example-logs", Source.REFERENCED.value, Provider.GCS.value)
    ]
    found = cloud_storage.candidates(
        label="example",
        hostnames=[],
        referenced=referenced,
        words=["logs"],
        guess=False,
    )
    assert [c.source for c in found.items] == [Source.REFERENCED.value]


def test_referenced_reads_a_bucket_out_of_a_cname_and_a_path_url():
    found = cloud_storage.referenced_in(
        hosts=["assets.example.com"],
        cnames=["example-media.s3.amazonaws.com"],
        urls=[
            "https://storage.googleapis.com/example-public/logo.png",
            "https://pub-00112233445566778899aabbccddeeff.r2.dev/x.js",
        ],
    )
    pairs = {(c.provider, c.name) for c in found}
    assert (Provider.AWS_S3.value, "example-media") in pairs
    assert (Provider.GCS.value, "example-public") in pairs
    assert any(p == Provider.R2.value for p, _ in pairs)


def test_an_invalid_bucket_name_is_dropped():
    found = cloud_storage.candidates(
        label="x",
        hostnames=["UPPER_CASE_bad", "ok-name"],
        referenced=[],
        words=[],
        guess=False,
    )
    names = {c.name for c in found.items}
    assert "ok-name" in names
    assert "UPPER_CASE_bad" not in names


def test_open_and_owned_sets_are_coherent():
    assert {Access.LISTABLE.value, Access.READABLE.value} == OPEN_ACCESS
    assert {Source.REFERENCED.value, Source.HOSTNAME.value} == OWNED_SOURCES
    assert Provider.R2.value not in GUESSABLE_PROVIDERS
    assert cloud_storage.is_owned(Source.GUESSED.value) is False
    assert cloud_storage.is_owned(Source.HOSTNAME.value) is True
