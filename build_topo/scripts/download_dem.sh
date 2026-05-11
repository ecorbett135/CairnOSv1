#!/bin/bash

mkdir -p data/dem
cd data/dem || exit 1

urls=(
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n43w072/USGS_13_n43w072_20260323.tif"
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n43w073/USGS_13_n43w073_20260331.tif"
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n43w074/USGS_13_n43w074_20260331.tif"
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n44w072/USGS_13_n44w072_20260126.tif"
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n44w073/USGS_13_n44w073_20260331.tif"
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n44w074/USGS_13_n44w074_20260331.tif"
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n45w072/USGS_13_n45w072_20260331.tif"
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n45w073/USGS_13_n45w073_20260331.tif"
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n45w074/USGS_13_n45w074_20260331.tif"
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n46w072/USGS_13_n46w072_20260331.tif"
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n46w073/USGS_13_n46w073_20260331.tif"
"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n46w074/USGS_13_n46w074_20260331.tif"
)

for url in "${urls[@]}"; do
    echo ""
    echo "Downloading:"
    echo "$url"
    echo ""

    curl -L -C - -O "$url"
done

echo ""
echo "[DONE] DEM downloads complete"
echo ""
