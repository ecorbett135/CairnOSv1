# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactContract:
    relative_path: str
    artifact_type: str
    required: bool = True


@dataclass(frozen=True)
class StageContract:
    stage_name: str
    module: str
    required_inputs: tuple[str, ...]
    generated_outputs: tuple[ArtifactContract, ...]
    validation_rules: tuple[str, ...]
    deterministic: bool = True
    network_access: bool = False


STAGE_CONTRACTS = (
    StageContract(
        stage_name="Spine Import",
        module="build_topo.compiler.spine",
        required_inputs=(
            "raw/route.geojson",
        ),
        generated_outputs=(
            ArtifactContract("compiled/spine.geojson", "geojson"),
            ArtifactContract("compiled/metadata.json", "json"),
            ArtifactContract(
                "intermediate/canonical_spine.geojson",
                "geojson",
                required=False,
            ),
        ),
        validation_rules=(
            "spine geojson parses as GeoJSON",
            "spine has at least one feature",
            "metadata json parses",
        ),
    ),
    StageContract(
        stage_name="Terrain Segmentation",
        module="build_topo.compiler.segments",
        required_inputs=(
            "compiled/spine.geojson",
        ),
        generated_outputs=(
            ArtifactContract("compiled/segments.geojson", "geojson"),
            ArtifactContract(
                "compiled/segments.json",
                "json",
                required=False,
            ),
        ),
        validation_rules=(
            "segments geojson parses as GeoJSON",
            "segments artifact exists before operational graph generation",
        ),
    ),
    StageContract(
        stage_name="Logistics Nodes",
        module="build_topo.compiler.logistics",
        required_inputs=(
            "compiled/spine.geojson",
        ),
        generated_outputs=(
            ArtifactContract("compiled/crossings.geojson", "geojson"),
            ArtifactContract("compiled/logistics_nodes.json", "json"),
        ),
        validation_rules=(
            "crossings geojson parses as GeoJSON",
            "logistics nodes json parses",
        ),
    ),
    StageContract(
        stage_name="Crossing Refinement",
        module="build_topo.compiler.crossings",
        required_inputs=(
            "compiled/crossings.geojson",
        ),
        generated_outputs=(
            ArtifactContract("compiled/crossings_refined.geojson", "geojson"),
            ArtifactContract(
                "compiled/crossings_refined.json",
                "json",
                required=False,
            ),
        ),
        validation_rules=(
            "refined crossings geojson parses as GeoJSON",
            "refined crossings stay separate from raw crossings",
        ),
    ),
    StageContract(
        stage_name="Route Overlay",
        module="build_topo.compiler.route_overlay",
        required_inputs=(
            "compiled/spine.geojson",
            "compiled/segments.geojson",
        ),
        generated_outputs=(
            ArtifactContract("compiled/route_overlay.json", "json"),
        ),
        validation_rules=(
            "route overlay json parses",
            "route overlay contains operational stop data",
        ),
    ),
    StageContract(
        stage_name="Overnight Reference Overlay",
        module="build_topo.compiler.overnight_reference",
        required_inputs=(
            "compiled/route_overlay.json",
        ),
        generated_outputs=(
            ArtifactContract(
                "compiled/overnight_reference.json",
                "json",
                required=False,
            ),
        ),
        validation_rules=(
            "overnight reference json parses when present",
            "unmatched reference data remains non-operational",
        ),
    ),
    StageContract(
        stage_name="Approach Trails",
        module="build_topo.compiler.approach_trails",
        required_inputs=(
            "compiled/route_overlay.json",
        ),
        generated_outputs=(
            ArtifactContract("compiled/approach_trails.json", "json"),
        ),
        validation_rules=(
            "approach trails json parses",
            "approach metadata remains explicit",
        ),
    ),
    StageContract(
        stage_name="Operational Graph",
        module="build_topo.compiler.graph",
        required_inputs=(
            "compiled/route_overlay.json",
            "compiled/approach_trails.json",
        ),
        generated_outputs=(
            ArtifactContract("compiled/operational_graph.json", "json"),
        ),
        validation_rules=(
            "operational graph json parses",
            "operational graph contains nodes and edges",
        ),
    ),
    StageContract(
        stage_name="Schema Registry",
        module="build_topo.compiler.schema_registry",
        required_inputs=(
            "compiled/operational_graph.json",
        ),
        generated_outputs=(
            ArtifactContract("compiled/cairn_schema_registry.json", "json"),
        ),
        validation_rules=(
            "schema registry json parses",
            "schema registry names generated datasets",
        ),
    ),
    StageContract(
        stage_name="Validation",
        module="build_topo.compiler.validation",
        required_inputs=(
            "compiled/spine.geojson",
            "compiled/segments.geojson",
            "compiled/operational_graph.json",
            "compiled/cairn_schema_registry.json",
        ),
        generated_outputs=(),
        validation_rules=(
            "validation runs after all generation stages",
            "validation does not generate promoted artifacts",
        ),
    ),
)


def get_stage_contracts():
    return STAGE_CONTRACTS


def get_expected_artifacts(include_optional=False):
    artifacts_by_path = {}

    for contract in STAGE_CONTRACTS:
        for artifact in contract.generated_outputs:
            if artifact.required or include_optional:
                artifacts_by_path.setdefault(
                    artifact.relative_path,
                    artifact,
                )

    return tuple(
        artifacts_by_path[path]
        for path in sorted(artifacts_by_path)
    )


def contract_for_stage(stage_name):
    for contract in STAGE_CONTRACTS:
        if contract.stage_name == stage_name:
            return contract

    raise KeyError(
        f"Unknown build_topo stage: {stage_name}"
    )
