#!/usr/bin/env python3
"""
Blender mesh repair script - run with blender --background --python this_script.py

This script repairs STL meshes using Blender's powerful mesh tools:
- 3D Print Toolbox: Make Manifold
- Merge by Distance
- Fill Holes
- Recalculate Normals
"""
import bpy
import sys
import os

def repair_mesh(input_file, output_file):
    """Repair mesh using Blender's tools"""

    # Clear existing objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Import STL
    bpy.ops.wm.stl_import(filepath=input_file)

    # Get the imported object
    obj = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = obj

    # Enter edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # 1. Merge vertices by distance (remove duplicates)
    bpy.ops.mesh.remove_doubles(threshold=0.0001)

    # 2. Make normals consistent
    bpy.ops.mesh.normals_make_consistent(inside=False)

    # 3. Fill holes
    bpy.ops.mesh.fill_holes(sides=100)

    # 4. Delete loose geometry
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)

    # 5. Try to make manifold using 3D Print Toolbox
    try:
        bpy.ops.mesh.print3d_clean_non_manifold()
    except:
        print("  3D Print Toolbox not available, using alternative method")
        # Alternative: select non-manifold and try to fix
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_non_manifold()
        # Try dissolving degenerate
        bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)

    # 6. Recalculate normals again
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)

    # Back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Export STL
    bpy.ops.wm.stl_export(
        filepath=output_file,
        export_selected_objects=True,
        ascii_format=False
    )

    # Get mesh stats
    mesh = obj.data
    print(f"  Repaired: {len(mesh.vertices)} vertices, {len(mesh.polygons)} faces")

if __name__ == "__main__":
    # Get arguments after "--"
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    if len(argv) >= 2:
        input_file = argv[0]
        output_file = argv[1]
        print(f"  Input: {input_file}")
        print(f"  Output: {output_file}")
        repair_mesh(input_file, output_file)
    else:
        print("Usage: blender --background --python blender_repair.py -- input.stl output.stl")
