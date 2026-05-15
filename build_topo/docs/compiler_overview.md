# CairnOSv1 Build_Topo Compiler Overview

## Introduction

The Build_Topo compiler is a critical component of the CairnOSv1 system, responsible for transforming high-level topology descriptions into optimized, operational graph representations. This process enables efficient route planning, terrain analysis, and logistics management within the CairnOSv1 environment.

## Architecture

The compiler architecture is modular and layered, designed to separate concerns between topology construction and operational semantics. It consists of several stages, each focusing on a specific aspect of the compilation pipeline:

1. **Spine Import**  
   This initial stage imports the primary spine topology, which serves as the backbone for subsequent terrain and logistics processing.

2. **Terrain Segmentation**  
   Terrain data is segmented into manageable regions, facilitating localized analysis and route planning.

3. **Logistics Nodes**  
   Key logistics nodes such as supply points, depots, and transfer stations are identified and integrated into the topology.

4. **Crossing Refinement**  
   Intersections and crossings are refined to ensure accurate connectivity and traversal properties.

5. **Route Overlay**  
   Routes are overlaid on the refined topology, enabling pathfinding and navigation.

6. **Overnight Reference Overlay (optional)**
   Shelter and campsite GeoJSON reference exports may be parsed into
   `overnight_reference.json`. This layer preserves matched and unmatched
   overnight waypoint records and exposes near-spine unmatched sites as
   planner stop candidates after reconciliation against `route_overlay.json`.

7. **Approach Trails**
   Approach trails leading into significant nodes or regions are constructed to support ingress and egress operations.

8. **Gaia Reference Overlay (optional)**
   Gaia-exported waypoint data may be parsed into `waypoint_reference.json`
   for future enrichment of shelter, campsite, lodge, trailhead, and marker
   metadata. This layer is explicitly reference data, not operational truth,
   and is not currently wired into PlannerV2.

9. **Operational Graph**
   The operational graph is generated, representing the executable routing and logistics network derived from the topology.

10. **Schema Registry**
   Throughout the compilation, a schema registry maintains structural definitions and constraints to ensure consistency.

11. **Validation**
   Final validation checks are performed to verify the integrity and correctness of the compiled graph.

## Core Architectural Principle

A fundamental architectural principle of Build_Topo is the strict separation between topology and operational semantics. Topology defines the static structural relationships—how nodes and edges connect—while operational semantics define dynamic behaviors such as routing rules, traversal costs, and logistics operations.

This separation allows for flexible adaptation of operational strategies without altering the underlying topology, enabling CairnOSv1 to support diverse scenarios and optimization goals.

## Conclusion

The Build_Topo compiler transforms complex topology data into actionable operational graphs through a well-defined, staged pipeline. Its modular design and clear separation of concerns contribute to the robustness and adaptability of the CairnOSv1 system.

This architectural distinction is foundational to CairnOSv1.
