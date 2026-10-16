"""Robust mesh booleans for the body: CadQuery solid -> watertight mesh -> manifold3d."""
import numpy as np, trimesh, manifold3d as m3d, cadquery as cq

def to_mesh(wp, tol=0.03, ang=0.12):
    shape = wp.val() if hasattr(wp, "val") else wp
    vs, ts = shape.tessellate(tol, ang)
    v = np.array([[p.x, p.y, p.z] for p in vs], dtype=np.float64)
    t = np.array(ts, dtype=np.int64)
    m = trimesh.Trimesh(v, t, process=True)
    m.merge_vertices(digits_vertex=5)
    return m

def M(wp, tol=0.03, ang=0.12):
    tm = to_mesh(wp, tol, ang)
    mesh = m3d.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32), tri_verts=np.asarray(tm.faces, dtype=np.uint32))
    out = m3d.Manifold(mesh)
    if out.status() != m3d.Error.NoError:
        raise RuntimeError(f"not manifold: {out.status()} (watertight={tm.is_watertight})")
    return out

def to_trimesh(man):
    mm = man.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=False)

def save(man, path):
    to_trimesh(man).export(path)

def vol(man):
    return man.volume() / 1000.0
