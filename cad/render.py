#!/usr/bin/env python3
"""Shaded renders of the assembly and of single parts with matplotlib (no OpenGL needed).
   ../.venv/bin/python render.py            -> out/render_*.png"""
import json, os, sys
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
REND = os.path.join(OUT, "render_parts")

def shade(mesh, rgb, light=(0.4, -0.5, 0.75)):
    l = np.array(light) / np.linalg.norm(light)
    n = mesh.face_normals
    k = 0.35 + 0.65 * np.clip(n @ l, 0, 1)
    c = np.clip(np.outer(k, rgb[:3]), 0, 1)
    return np.hstack([c, np.ones((len(c), 1))])

def draw(ax, meshes, elev, azim, title=None, lim=None):
    allv = np.vstack([m.vertices for m, _ in meshes])
    for m, rgb in meshes:
        pc = Poly3DCollection(m.vertices[m.faces], facecolors=shade(m, rgb), edgecolors="none", linewidths=0)
        ax.add_collection3d(pc)
    lo, hi = allv.min(0), allv.max(0)
    c, r = (lo + hi) / 2, (hi - lo).max() / 2 if lim is None else lim
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=9)

def sort_painter(meshes, elev, azim):
    """Matplotlib has no depth buffer: merge into one collection sorted far-to-near per face."""
    e, a = np.radians(elev), np.radians(azim)
    view = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    tris, cols = [], []
    for m, rgb in meshes:
        tris.append(m.vertices[m.faces]); cols.append(shade(m, rgb))
    tris = np.vstack(tris); cols = np.vstack(cols)
    depth = (tris.mean(1) @ view)
    o = np.argsort(depth)
    return tris[o], cols[o]

def draw_sorted(ax, meshes, elev, azim, title=None, pad=1.0):
    tris, cols = sort_painter(meshes, elev, azim)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolors="none", linewidths=0))
    allv = tris.reshape(-1, 3)
    lo, hi = allv.min(0), allv.max(0)
    c, r = (lo + hi) / 2, (hi - lo).max() / 2 * pad
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    if title: ax.set_title(title, fontsize=9)

def load_assembly(skip=()):
    colors = json.load(open(os.path.join(REND, "colors.json")))
    ms = []
    for name, rgb in colors.items():
        if any(name.startswith(s) for s in skip):
            continue
        m = trimesh.load(os.path.join(REND, name + ".stl"))
        ms.append((m, rgb))
    return ms

if __name__ == "__main__":
    full = load_assembly()
    fig = plt.figure(figsize=(12, 9))
    views = [(25, -130, "iso rear-left"), (30, 40, "iso front-right"), (90, -90, "top"), (0, -90, "side (left)")]
    for i, (e, a, t) in enumerate(views):
        draw_sorted(fig.add_subplot(2, 2, i + 1, projection="3d"), full, e, a, t)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "render_assembly.png"), dpi=110); plt.close(fig)

    # without panel + frame, to see the drivetrain and bay
    inner = load_assembly(skip=("panel",))
    fig = plt.figure(figsize=(12, 6))
    draw_sorted(fig.add_subplot(1, 2, 1, projection="3d"), inner, 35, -120, "without panel")
    rear = [(m, c) for m, c in inner if m.bounds[0][0] < 30 and m.bounds[1][0] < 60]
    draw_sorted(fig.add_subplot(1, 2, 2, projection="3d"), rear, 30, -60, "rear drivetrain")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "render_inside.png"), dpi=110); plt.close(fig)

    # single printable parts
    names = sys.argv[1:] or ["chassis", "front_carrier", "rim_silicone", "spur_42T_m05", "mold_base", "mold_lid",
                             "panel_frame", "motor_clamp", "bearing_cap"]
    n = len(names); cols = 3; rows = (n + cols - 1) // cols
    fig = plt.figure(figsize=(4 * cols, 3.6 * rows))
    for i, nm in enumerate(names):
        m = trimesh.load(os.path.join(OUT, "stl", nm + ".stl"))
        draw_sorted(fig.add_subplot(rows, cols, i + 1, projection="3d"), [(m, (0.9, 0.55, 0.15))], 35, -60, nm)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "render_parts.png"), dpi=100); plt.close(fig)
    print("ok")
