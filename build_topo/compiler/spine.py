# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys
import json
import math
import xml.etree.ElementTree as ET

ELEVATION_UNIT = "m"
ELEVATION_METHOD = "source_embedded_gpx_ele"
SOURCE_LICENSE_STATUS = "UNKNOWN — needs review"


#
# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
#

def load_gpx_track(gpx_path):
    horizontal_coords = []
    elevated_coords = []
    root = ET.parse(gpx_path).getroot()
    for point in root.iter():
        if point.tag.rsplit("}", 1)[-1] != "trkpt":
            continue
        longitude = float(point.attrib["lon"])
        latitude = float(point.attrib["lat"])
        horizontal_coords.append((longitude, latitude))
        elevation = next(
            (
                child.text
                for child in point
                if child.tag.rsplit("}", 1)[-1] == "ele"
            ),
            None,
        )
        elevation_value = _finite_float_or_none(elevation)
        if elevation_value is not None:
            elevated_coords.append((
                longitude,
                latitude,
                elevation_value,
            ))

    if not horizontal_coords:

        raise RuntimeError(
            "No GPX coordinates found"
        )

    coordinates = (
        elevated_coords
        if len(elevated_coords) == len(horizontal_coords)
        else horizontal_coords
    )
    return coordinates


def _finite_float_or_none(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def serialize_spine_geojson(payload, *, name):
    feature = payload["features"][0]
    properties = feature["properties"]
    coordinates = feature["geometry"]["coordinates"]
    properties_text = "{ " + ", ".join(
        f"{json.dumps(key)}: {json.dumps(value, ensure_ascii=False)}"
        for key, value in properties.items()
    ) + " }"
    coordinates_text = "[ " + ", ".join(
        "[ "
        + ", ".join(json.dumps(value) for value in coordinate)
        + " ]"
        for coordinate in coordinates
    ) + " ]"
    return (
        "{\n"
        '"type": "FeatureCollection",\n'
        f'"name": {json.dumps(name)},\n'
        '"crs": { "type": "name", "properties": { "name": '
        '"urn:ogc:def:crs:OGC:1.3:CRS84" } },\n'
        '"features": [\n'
        '{ "type": "Feature", "properties": '
        + properties_text
        + ', "geometry": { "type": "LineString", "coordinates": '
        + coordinates_text
        + " } }\n"
        "]\n"
        "}\n"
    )


#
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
#

def main():

    if len(sys.argv) != 2:

        print("")
        print("Usage:")
        print("")
        print(
            "python -m build_topo.compiler.spine "
            "trails/vermont_long_trail"
        )
        print("")

        sys.exit(1)

    trail_root = Path(sys.argv[1]).resolve()

    RAW_DIR = trail_root / "raw"
    COMPILED_DIR = trail_root / "compiled"
    INTERMEDIATE_DIR = trail_root / "intermediate"

    GPX_DIR = RAW_DIR / "gpx"

    #
    # find GPX
    #

    gpx_files = list(
        GPX_DIR.glob("*.gpx")
    )

    if not gpx_files:

        raise FileNotFoundError(
            f"No GPX files found in: {GPX_DIR}"
        )

    gpx_path = gpx_files[0]

    print("")
    print("=== CairnOSv1 Spine Builder ===")
    print("")
    print(f"Trail Root: {trail_root}")
    print(f"GPX: {gpx_path.name}")

    #
    # build geometry
    #

    line = load_gpx_track(gpx_path)
    elevation_coordinate_count = sum(
        1
        for coordinate in line
        if len(coordinate) >= 3
        and math.isfinite(float(coordinate[2]))
    )
    elevation_status = (
        "complete"
        if elevation_coordinate_count == len(line)
        else "unavailable"
    )
    source_path = gpx_path.relative_to(trail_root).as_posix()

    payload = {
        "type": "FeatureCollection",
        "name": "spine",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84",
            },
        },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "trail_name": trail_root.name,
                    "schema_version": "1.0",
                    "geometry_id": "defined_trail_spine",
                    "source_path": source_path,
                    "source_kind": "Raw GPX track",
                    "source_license_status": SOURCE_LICENSE_STATUS,
                    "elevation_status": elevation_status,
                    "elevation_unit": ELEVATION_UNIT,
                    "elevation_method": ELEVATION_METHOD,
                    "elevation_coordinate_count": elevation_coordinate_count,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": line,
                },
            },
        ],
    }

    #
    # ensure dirs
    #

    COMPILED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    INTERMEDIATE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    #
    # export
    #

    compiled_path = (
        COMPILED_DIR /
        "spine.geojson"
    )

    intermediate_path = (
        INTERMEDIATE_DIR /
        "canonical_spine.geojson"
    )

    output_names = {
        compiled_path: "spine",
        intermediate_path: "canonical_spine",
    }
    for path, name in output_names.items():
        with path.open("w", encoding="utf-8") as handle:
            handle.write(serialize_spine_geojson(payload, name=name))

    #
    # metadata
    #

    metadata = {

        "trail": trail_root.name,
        "schema_version": "1.0",
        "spine_points": len(line),
        "spine_elevation_status": elevation_status,
        "spine_elevation_unit": ELEVATION_UNIT,
        "spine_elevation_method": ELEVATION_METHOD,
        "spine_elevation_points": elevation_coordinate_count,
        "spine_source_path": source_path,
        "spine_source_license_status": SOURCE_LICENSE_STATUS,
    }

    with open(
        COMPILED_DIR / "metadata.json",
        "w",
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2,
        )

    print("")
    print("[OK] spine.geojson")
    print("[OK] canonical_spine.geojson")
    print("")
    print("[DONE]")


if __name__ == "__main__":

    main()
