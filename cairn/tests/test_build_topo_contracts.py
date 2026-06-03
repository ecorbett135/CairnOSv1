# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from build_topo.scripts.build_topology import STAGES


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
