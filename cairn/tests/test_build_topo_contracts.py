# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from build_topo.scripts.build_topology import STAGES
from build_topo.compiler.contracts import (
    ArtifactContract,
    StageContract,
    get_expected_artifacts,
    get_stage_contracts,
)


def test_build_topology_exposes_stage_order():
    assert STAGES == (
        ("Spine Import", "build_topo.compiler.spine"),
        ("Terrain Segmentation", "build_topo.compiler.segments"),
        ("Logistics Nodes", "build_topo.compiler.logistics"),
        ("Crossing Refinement", "build_topo.compiler.crossings"),
        ("Route Overlay", "build_topo.compiler.route_overlay"),
        (
            "Overnight Reference Overlay",
            "build_topo.compiler.overnight_reference",
        ),
        ("Approach Trails", "build_topo.compiler.approach_trails"),
        ("Operational Graph", "build_topo.compiler.graph"),
        ("Schema Registry", "build_topo.compiler.schema_registry"),
        ("Validation", "build_topo.compiler.validation"),
    )


def test_stage_contracts_match_build_topology_order():
    contract_pairs = tuple(
        (contract.stage_name, contract.module)
        for contract in get_stage_contracts()
    )

    assert contract_pairs == STAGES


def test_stage_contracts_are_local_and_deterministic():
    for contract in get_stage_contracts():
        assert isinstance(contract, StageContract)
        assert contract.deterministic is True
        assert contract.network_access is False
        assert contract.generated_outputs is not None
        assert contract.validation_rules


def test_expected_artifacts_include_current_promoted_outputs():
    artifact_paths = {
        artifact.relative_path
        for artifact in get_expected_artifacts()
    }

    assert "compiled/spine.geojson" in artifact_paths
    assert "compiled/segments.geojson" in artifact_paths
    assert "compiled/crossings.geojson" in artifact_paths
    assert "compiled/crossings_refined.geojson" in artifact_paths
    assert "compiled/logistics_nodes.json" in artifact_paths
    assert "compiled/route_overlay.json" in artifact_paths
    assert "compiled/approach_trails.json" in artifact_paths
    assert "compiled/operational_graph.json" in artifact_paths
    assert "compiled/cairn_schema_registry.json" in artifact_paths


def test_expected_artifacts_are_deduplicated_by_relative_path():
    artifacts = get_expected_artifacts()
    assert all(isinstance(artifact, ArtifactContract) for artifact in artifacts)

    paths = [
        artifact.relative_path
        for artifact in artifacts
    ]

    assert len(paths) == len(set(paths))
