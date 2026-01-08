#!/usr/bin/env python3
"""
STEP to STL Converter with high precision mesh control

This script converts STEP files to STL format using OpenCASCADE (OCP).
It supports:
- Splitting assemblies into left/right parts by X position
- Extracting specific solids by index
- High precision mesh with configurable linear and angular deflection

Requirements:
- Python 3.11+
- OCP (OpenCASCADE Python bindings): conda install -c conda-forge cadquery

Usage:
    python convert_step_to_stl.py

Author: Generated with Claude Code
"""
import os
from pathlib import Path

from OCP.STEPControl import STEPControl_Reader
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopoDS import TopoDS
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound


def read_step(filepath: str):
    """Read STEP file and return shape"""
    print(f"Reading STEP file: {filepath}")
    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    if status != 1:
        raise Exception(f"Failed to read STEP file, status: {status}")
    reader.TransferRoots()
    return reader.OneShape()


def get_solids(shape):
    """Extract all solids from shape with bounding box info"""
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    solids = []
    while explorer.More():
        solid = TopoDS.Solid_s(explorer.Current())
        bbox = Bnd_Box()
        BRepBndLib.Add_s(solid, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
        solids.append({
            'solid': solid,
            'center_x': (xmin + xmax) / 2,
            'bbox': (xmin, ymin, zmin, xmax, ymax, zmax)
        })
        explorer.Next()
    return solids


def make_compound(solid_list):
    """Create compound from list of solids"""
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for s in solid_list:
        if isinstance(s, dict):
            builder.Add(compound, s['solid'])
        else:
            builder.Add(compound, s)
    return compound


def mesh_and_export(shape, filename: str, linear_defl: float = 0.001, angular_defl: float = 0.05):
    """Mesh shape and export to STL with high precision"""
    print(f"\nMeshing {filename}...")
    print(f"  Linear deflection: {linear_defl} mm")
    print(f"  Angular deflection: {angular_defl} rad (~{angular_defl * 180 / 3.14159:.1f} degrees)")

    mesh = BRepMesh_IncrementalMesh(shape, linear_defl, False, angular_defl, True)
    mesh.Perform()

    if not mesh.IsDone():
        raise Exception(f"Meshing failed for {filename}")

    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    result = writer.Write(shape, filename)

    if result:
        size = os.path.getsize(filename)
        print(f"  Saved: {filename} ({size / 1024 / 1024:.2f} MB)")
    else:
        raise Exception(f"Failed to save: {filename}")


def split_left_right(solids, left_name: str, right_name: str):
    """Split solids into left and right by X position"""
    x_centers = [s['center_x'] for s in solids]
    x_mid = (min(x_centers) + max(x_centers)) / 2

    left = [s for s in solids if s['center_x'] < x_mid]
    right = [s for s in solids if s['center_x'] >= x_mid]

    print(f"\nSplit by X midpoint ({x_mid:.2f}):")
    print(f"  Left: {len(left)} solids")
    print(f"  Right: {len(right)} solids")

    if left:
        mesh_and_export(make_compound(left), left_name)
    if right:
        mesh_and_export(make_compound(right), right_name)


def extract_and_rest(solids, extract_idx: int, extract_name: str, rest_name: str):
    """Extract one solid by index and merge the rest"""
    extract_solid = solids[extract_idx]['solid']
    rest_solids = [s['solid'] for i, s in enumerate(solids) if i != extract_idx]

    print(f"\nExtract solid index {extract_idx}:")
    print(f"  Extracted: 1 solid")
    print(f"  Rest: {len(rest_solids)} solids")

    mesh_and_export(extract_solid, extract_name)
    mesh_and_export(make_compound(rest_solids), rest_name)


def convert_jingtuiwaike(input_dir: str, output_dir: str):
    """Convert 镜腿外壳.step -> left/right STL"""
    shape = read_step(os.path.join(input_dir, "镜腿外壳.step"))
    solids = get_solids(shape)
    print(f"Total solids: {len(solids)}")
    split_left_right(
        solids,
        os.path.join(output_dir, "镜腿外壳_左.stl"),
        os.path.join(output_dir, "镜腿外壳_右.stl")
    )


def convert_jingtui_neike(input_dir: str, output_dir: str):
    """Convert 镜腿内壳.step -> left/right STL"""
    shape = read_step(os.path.join(input_dir, "镜腿内壳.step"))
    solids = get_solids(shape)
    print(f"Total solids: {len(solids)}")
    split_left_right(
        solids,
        os.path.join(output_dir, "镜腿内壳_左.stl"),
        os.path.join(output_dir, "镜腿内壳_右.stl")
    )


def convert_yanjingkuang(input_dir: str, output_dir: str):
    """
    Convert 眼镜框.step -> 内壳 + rest STL

    Based on STEP file analysis, solid order is:
    #33 = 外壳 (1)   -> idx 0
    #51 = 外壳 (11)  -> idx 1
    #52 = 外壳 (6)   -> idx 2
    #53 = 外壳 (5)   -> idx 3
    #54 = 外壳 (4)   -> idx 4
    #55 = 外壳 (3)   -> idx 5
    #56 = 实体84     -> idx 6
    #57 = 外壳 (2)   -> idx 7
    #58 = 内壳 (2)   -> idx 8  <-- COMPOUND008
    #59 = 实体94     -> idx 9
    #60 = 实体100    -> idx 10
    #61 = 实体47     -> idx 11
    #62 = 实体48     -> idx 12
    #63 = 实体49     -> idx 13
    #64 = SC850      -> idx 14
    #65 = 实体104    -> idx 15
    #66 = 实体98     -> idx 16
    """
    shape = read_step(os.path.join(input_dir, "眼镜框.step"))
    solids = get_solids(shape)
    print(f"Total solids: {len(solids)}")

    # 内壳 (2) / COMPOUND008 is at index 8
    extract_and_rest(
        solids,
        extract_idx=8,
        extract_name=os.path.join(output_dir, "眼镜框_内壳.stl"),
        rest_name=os.path.join(output_dir, "眼镜框_其余.stl")
    )


def main():
    # Get paths relative to script location
    script_dir = Path(__file__).parent.parent
    input_dir = script_dir / "assets" / "step"
    output_dir = script_dir / "assets" / "stl"

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("STEP to STL Converter")
    print("=" * 60)

    # Convert all files
    print("\n" + "=" * 60)
    print("Converting 镜腿外壳.step")
    print("=" * 60)
    convert_jingtuiwaike(str(input_dir), str(output_dir))

    print("\n" + "=" * 60)
    print("Converting 镜腿内壳.step")
    print("=" * 60)
    convert_jingtui_neike(str(input_dir), str(output_dir))

    print("\n" + "=" * 60)
    print("Converting 眼镜框.step")
    print("=" * 60)
    convert_yanjingkuang(str(input_dir), str(output_dir))

    print("\n" + "=" * 60)
    print("All conversions complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
