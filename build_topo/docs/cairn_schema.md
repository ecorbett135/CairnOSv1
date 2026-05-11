CairnOS Schema Specification

Version: 0.1-draft

⸻

Purpose

CairnOS is an operational trail traversal planning engine focused on:

* cadence feasibility
* terrain burden
* progression reasoning
* overnight planning
* long-distance hiking analytics

CairnOS is NOT intended to replace navigation platforms like FarOut or Gaia GPS.

Instead, CairnOS augments existing navigation tools by modeling:

* realistic daily progression
* terrain-aware effort
* overnight spacing
* cadence consistency
* multi-day traversal feasibility

⸻

Architectural Principles

Separation of Concerns

Layer	Responsibility
GPX Spine	authoritative trail geometry
DEM Terrain	authoritative elevation + terrain analytics
OSM POIs	operational nodes + access points
Segment Engine	progression intervals
Cadence Engine	feasibility reasoning
Planner	itinerary generation

⸻

Canonical Data Products

1. LT Spine

Authoritative traversal geometry.

Generated From:

* GPX export

Outputs:

* lt_spine.geojson

Authority:

* canonical traversal reference
* mile indexing substrate
* projection substrate

⸻

2. Terrain Profile

Sampled terrain state along the spine.

Generated From:

* DEM rasters
* terrain sampling engine

Outputs:

* terrain_profile.geojson
* terrain_summary.json

Current Metrics:

* trail miles: 249.1
* DEM ascent: 64,283 ft
* DEM descent: 64,538 ft
* sample interval: 0.1 miles
* sample points: 2491

⸻

3. Operational Nodes

Canonical overnight + access nodes projected onto the spine.

Generated From:

* OSM POIs
* corridor filtering
* canonical reconciliation

Outputs:

* canonical_nodes.geojson

Examples:

* shelters
* campsites
* trailheads
* road crossings
* resupply access points

⸻

Core Entities

⸻

Entity: Spine

Meaning

Authoritative traversal geometry.

Defines:

* ordered progression
* mile indexing
* traversal continuity

Fields

Field	Type	Notes
spine_id	string	immutable identifier
geometry	LineString	canonical geometry
total_miles	float	authoritative mileage
source	string	GPX source
directionality	enum	NOBO / SOBO / bidirectional

Invariants

* spine geometry must be continuous
* mile progression must be monotonic
* topology revisions must be versioned

⸻

Entity: TerrainSample

Meaning

Terrain state sampled along the spine.

Fields

Field	Type	Notes
sample_id	string	immutable identifier
mile	float	progression mile
elevation_ft	float	DEM-derived elevation
slope_pct	float	derived
terrain_class	enum	optional
geometry	Point	sampled location

Invariants

* samples must project to spine
* mile ordering must increase monotonically
* terrain analytics derive ONLY from DEM sources

⸻

Entity: OperationalNode

Meaning

Operationally meaningful traversal anchor.

Not every GIS point qualifies as a node.

Nodes represent locations meaningful to traversal planning.

Node Types

* shelter
* campsite
* trailhead
* road_crossing
* resupply
* bailout
* junction

Fields

Field	Type	Notes
node_id	string	immutable identifier
canonical_name	string	normalized name
node_type	enum	operational category
mile	float	projected spine mile
elevation_ft	float	optional
geometry	Point	projected location
road_access	bool	optional
resupply_access	bool	optional
overnight_capacity	optional	future
water_reliability	optional	future

Invariants

* nodes must project to spine
* node ids are immutable
* trail ordering must be stable
* mile positions must be reproducible

⸻

Entity: Segment

Meaning

Traversable interval between two operational nodes.

Segments become the primary operational unit of planning.

Fields

Field	Type	Notes
segment_id	string	immutable identifier
start_node	ref	OperationalNode
end_node	ref	OperationalNode
distance_miles	float	derived
ascent_ft	float	DEM-derived
descent_ft	float	DEM-derived
effort_score	float	derived
terrain_class	enum	optional
bailout_access	bool	optional

Invariants

* distance must be > 0
* segments cannot improperly overlap
* start/end nodes must exist
* segment metrics must be reproducible

⸻

Entity: CadenceWindow

Meaning

Feasible daily traversal envelope.

Represents operational movement possibilities rather than fixed itineraries.

Fields

Field	Type	Notes
window_id	string	immutable identifier
start_node	ref	OperationalNode
candidate_end_nodes	list	feasible destinations
min_effort	float	derived
max_effort	float	derived
feasibility_score	float	derived
terrain_class	enum	optional

⸻

Entity: TraversePlan

Meaning

Generated itinerary hypothesis.

Not authoritative truth.

Traverse plans represent plausible operational traversals.

Fields

Field	Type	Notes
plan_id	string	immutable identifier
daily_segments	list	Segment refs
total_days	int	derived
total_effort	float	derived
cadence_consistency	float	derived
recovery_balance	float	derived

⸻

Derived Metrics

⸻

Effort Score

Composite terrain burden metric.

Potential Inputs:

* ascent
* descent
* distance
* grade
* terrain oscillation
* cumulative fatigue

Status:

* experimental

⸻

Climb Density

Definition:

* ascent per mile

Potential Use:

* cadence penalty
* terrain classification

⸻

Terrain Class

Potential Categories:

* gentle
* moderate
* rugged
* severe

Derived From:

* grade
* climb density
* oscillation frequency

⸻

Operational Assumptions

Current assumptions are preliminary and subject to revision.

⸻

Cadence Assumptions

Beginner

Typical sustainable range:

* 8–12 miles/day

⸻

Intermediate

Typical sustainable range:

* 12–18 miles/day

⸻

Advanced

Typical sustainable range:

* 18–25+ miles/day

⸻

Terrain Assumptions

* steep terrain compounds fatigue nonlinearly
* repeated rollers create hidden effort burden
* climb density matters more than raw mileage
* recovery consistency affects multi-day sustainability

⸻

Non-Goals

CairnOS currently does NOT attempt to replace:

* water source navigation
* real-time navigation
* GPS tracking
* waypoint comments/social layers

Those are already handled effectively by tools like FarOut.

⸻

Versioning

Schema Version

Current:

* 0.1-draft

⸻

Topology Versioning

Topology products must include:

* source provenance
* extraction methodology
* generation timestamp

⸻

Terrain Versioning

Terrain products must include:

* DEM source
* sample interval
* DEM tile provenance

⸻

Current Known Limitations

* LT spine currently measures 249.1 miles
* official LT mileage differs (~272 mi)
* overnight node reconciliation remains incomplete
* effort scoring remains experimental
* terrain classification remains undefined

⸻

Future Systems

Planned future engines include:

* segment generation engine
* cadence feasibility engine
* recovery modeling
* itinerary synthesis
* terrain burden analytics
* resupply accessibility modeling
* fatigue propagation modeling

⸻

Guiding Principle

CairnOS is fundamentally an operational reasoning system.

The goal is not perfect GIS representation.

The goal is stable, explainable, terrain-aware traversal planning.
