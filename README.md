# 3D Models - AI Glasses Hardware

STEP to STL conversion tools and 3D model assets for AI Glasses project.

## Directory Structure

```
3d_models/
├── assets/
│   ├── step/          # Source STEP files
│   ├── stl/           # Generated STL files
│   └── dxf/           # DXF files
├── src/
│   └── convert_step_to_stl.py  # Conversion script
└── README.md
```

## Generated STL Files

| Source STEP | Output STL | Description |
|-------------|------------|-------------|
| 镜腿外壳.step | 镜腿外壳_左.stl | Left temple outer shell |
| 镜腿外壳.step | 镜腿外壳_右.stl | Right temple outer shell |
| 镜腿内壳.step | 镜腿内壳_左.stl | Left temple inner shell |
| 镜腿内壳.step | 镜腿内壳_右.stl | Right temple inner shell |
| 眼镜框.step | 眼镜框_内壳.stl | Frame inner shell (COMPOUND008) |
| 眼镜框.step | 眼镜框_其余.stl | Frame remaining parts |

## Requirements

- Python 3.11+
- OpenCASCADE Python bindings (OCP)

### Installation

```bash
# Using conda (recommended)
conda create -n occt_env python=3.11
conda activate occt_env
conda install -c conda-forge cadquery
```

## Usage

```bash
cd src
python convert_step_to_stl.py
```

## Mesh Parameters

- Linear deflection: 0.001 mm
- Angular deflection: 0.05 rad (~2.9 degrees)

These parameters provide high-quality mesh suitable for 3D printing.
