#!/usr/bin/env python3
"""
STEP to STL Converter with admesh mesh repair

This script converts STEP files to STL format using:
- OpenCASCADE (OCP) for STEP reading and initial meshing
- admesh for repairing non-manifold meshes (command-line tool)

admesh repairs meshes by:
- Finding and connecting nearby facets (-n)
- Filling holes (-f)
- Fixing normal directions (-d)
- Fixing normal values (-v)
- Removing unconnected facets (-u)

Requirements:
- Python 3.11+
- OCP (OpenCASCADE Python bindings): conda install -c conda-forge cadquery
- admesh: brew install admesh

Usage:
    python convert_step_to_stl.py

Author: Generated with Claude Code
"""
import os
import subprocess
import tempfile
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


def repair_stl_with_admesh(input_file: str, output_file: str):
    """
    Repair STL file using admesh to fix non-manifold edges and other issues.
    """
    print(f"  Repairing mesh with admesh...")

    # Run admesh with all repair options
    cmd = [
        'admesh',
        '-n',           # nearby facets
        '-f',           # fill holes
        '-d',           # fix normal directions
        '-v',           # fix normal values
        '-u',           # remove unconnected
        '-i', '3',      # iterations
        '-t', '0.001',  # tolerance
        '-b', output_file,  # output binary STL
        input_file
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"    Warning: admesh returned {result.returncode}")
            if result.stderr:
                print(f"    stderr: {result.stderr[:200]}")
        else:
            # Parse admesh output for stats
            for line in result.stdout.split('\n'):
                if 'edges fixed' in line.lower() or 'facets' in line.lower() or 'normal' in line.lower():
                    print(f"    {line.strip()}")
    except subprocess.TimeoutExpired:
        print(f"    Warning: admesh timed out")
    except Exception as e:
        print(f"    Warning: admesh failed: {e}")


def mesh_and_export(shape, filename: str, linear_defl: float = 0.001, angular_defl: float = 0.05):
    """Mesh shape and export to STL with high precision, then repair with admesh"""
    print(f"\nMeshing {filename}...")
    print(f"  Linear deflection: {linear_defl} mm")
    print(f"  Angular deflection: {angular_defl} rad (~{angular_defl * 180 / 3.14159:.1f} degrees)")

    mesh = BRepMesh_IncrementalMesh(shape, linear_defl, False, angular_defl, True)
    mesh.Perform()

    if not mesh.IsDone():
        raise Exception(f"Meshing failed for {filename}")

    # First export to a temp file
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
        temp_file = tmp.name

    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    result = writer.Write(shape, temp_file)

    if not result:
        os.unlink(temp_file)
        raise Exception(f"Failed to save temp STL")

    # Repair with admesh
    repair_stl_with_admesh(temp_file, filename)

    # Clean up temp file
    os.unlink(temp_file)

    if os.path.exists(filename):
        size = os.path.getsize(filename)
        print(f"  Saved: {filename} ({size / 1024 / 1024:.2f} MB)")
    else:
        print(f"  Warning: Output file not created")


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
    Convert 眼镜框 related STEP files to STL:
    - 眼镜-提取1.step -> 眼镜框_内壳.stl (merge all solids)
    - 眼镜-提取2.step -> 眼镜框_其余.stl (merge all solids)
    """
    # Process 眼镜-提取1.step -> 眼镜框_内壳.stl
    print("\n--- Processing 眼镜-提取1.step -> 眼镜框_内壳.stl ---")
    shape1 = read_step(os.path.join(input_dir, "眼镜-提取1.step"))
    solids1 = get_solids(shape1)
    print(f"Total solids: {len(solids1)}")

    if len(solids1) > 1:
        compound1 = make_compound(solids1)
        mesh_and_export(compound1, os.path.join(output_dir, "眼镜框_内壳.stl"))
    elif len(solids1) == 1:
        mesh_and_export(solids1[0]['solid'], os.path.join(output_dir, "眼镜框_内壳.stl"))
    else:
        # Use entire shape if no solids found
        mesh_and_export(shape1, os.path.join(output_dir, "眼镜框_内壳.stl"))

    # Process 眼镜-提取2.step -> 眼镜框_其余.stl
    print("\n--- Processing 眼镜-提取2.step -> 眼镜框_其余.stl ---")
    shape2 = read_step(os.path.join(input_dir, "眼镜-提取2.step"))
    solids2 = get_solids(shape2)
    print(f"Total solids: {len(solids2)}")

    if len(solids2) > 1:
        compound2 = make_compound(solids2)
        mesh_and_export(compound2, os.path.join(output_dir, "眼镜框_其余.stl"))
    elif len(solids2) == 1:
        mesh_and_export(solids2[0]['solid'], os.path.join(output_dir, "眼镜框_其余.stl"))
    else:
        # Use entire shape if no solids found
        mesh_and_export(shape2, os.path.join(output_dir, "眼镜框_其余.stl"))


def main():
    # Get paths relative to script location
    script_dir = Path(__file__).parent.parent
    input_dir = script_dir / "assets" / "step"
    output_dir = script_dir / "assets" / "stl"

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("STEP to STL Converter (with admesh Repair)")
    print("Fixes non-manifold edges for 3D printing!")
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
    print("Converting 眼镜框 (from 眼镜-提取1.step and 眼镜-提取2.step)")
    print("=" * 60)
    convert_yanjingkuang(str(input_dir), str(output_dir))

    print("\n" + "=" * 60)
    print("All conversions complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
