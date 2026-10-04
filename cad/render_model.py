"""Render the exported printable meshes with an orthographic software z-buffer.

Usage: python cad/render_model.py [project_directory]
The images use actual CAD geometry; no generated product illustration or simulated LCD.
"""
import os
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/mpl-step-counter")
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
OUT = ROOT / "renders"
OUT.mkdir(exist_ok=True)
INK = "#34303e"
MUTED = "#736d7b"
PURPLE = "#8e6dab"
BG = "#faf8f5"


@dataclass
class Part:
    name: str
    triangles: np.ndarray
    normals: np.ndarray
    color: tuple

    def shifted(self, offset):
        return Part(self.name, self.triangles + np.asarray(offset), self.normals, self.color)


def part_color(name):
    if any(s in name for s in ("foot", "feet", "cheek", "accent", "middle", "shell", "loop")):
        return to_rgb("#b29acb")
    if any(s in name for s in ("carrier", "retainer", "clamp")):
        return to_rgb("#9884b0")
    return to_rgb("#efe5d7")


def load_parts():
    paths = sorted((ROOT / "cad" / "assembly").glob("*_assembled.stl"))
    if not paths:
        raise SystemExit("No assembly STLs found. Generate the CAD files before rendering.")
    parts = []
    for path in paths:
        mesh = trimesh.load(path, force="mesh", process=False)
        name = path.stem.removesuffix("_assembled")
        parts.append(Part(name, np.asarray(mesh.triangles), np.asarray(mesh.face_normals), part_color(name)))
    return parts


def bounds(parts):
    points = np.concatenate([p.triangles.reshape(-1, 3) for p in parts])
    return points.min(0), points.max(0)


def camera_basis(camera):
    cam = np.asarray(camera, dtype=float)
    cam /= np.linalg.norm(cam)
    right = np.cross(cam, [0., 1., 0.])
    right /= np.linalg.norm(right)
    up = np.cross(right, cam)
    return cam, right, up


def raster(parts, camera, scale=7.0):
    """Orthographic opaque STL renderer with exact per-pixel depth ordering."""
    cam, right, up = camera_basis(camera)
    triangles = np.concatenate([p.triangles for p in parts])
    normals = np.concatenate([p.normals for p in parts])
    colors = np.concatenate([np.tile(p.color, (len(p.triangles), 1)) for p in parts])
    front = normals @ cam > 1e-8
    triangles, normals, colors = triangles[front], normals[front], colors[front]
    light = -.45 * right + .65 * up + .85 * cam
    light /= np.linalg.norm(light)
    fill = .4 * right + .1 * up + cam
    fill /= np.linalg.norm(fill)
    shade = .66 + .27 * np.maximum(normals @ light, 0) + .07 * np.maximum(normals @ fill, 0)
    colors *= shade[:, None]
    xy = np.stack((triangles @ right, triangles @ up), axis=-1)
    lo, hi = xy.reshape(-1, 2).min(0), xy.reshape(-1, 2).max(0)
    nx, ny = np.ceil((hi - lo) * scale).astype(int) + 3
    depth_buffer = np.full((ny, nx), -np.inf)
    bitmap = np.tile(to_rgb(BG), (ny, nx, 1))
    pixels = (xy - lo) * scale + 1
    z_values = triangles @ cam
    z_min, z_max = z_values.min(), z_values.max()
    for poly, z, color in zip(pixels, z_values, colors):
        x0 = max(0, int(np.floor(poly[:, 0].min())))
        x1 = min(nx - 1, int(np.ceil(poly[:, 0].max())))
        y0 = max(0, int(np.floor(poly[:, 1].min())))
        y1 = min(ny - 1, int(np.ceil(poly[:, 1].max())))
        if x1 < x0 or y1 < y0:
            continue
        den = ((poly[1, 1] - poly[2, 1]) * (poly[0, 0] - poly[2, 0])
               + (poly[2, 0] - poly[1, 0]) * (poly[0, 1] - poly[2, 1]))
        if abs(den) < 1e-10:
            continue
        xx, yy = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
        a = ((poly[1, 1] - poly[2, 1]) * (xx - poly[2, 0])
             + (poly[2, 0] - poly[1, 0]) * (yy - poly[2, 1])) / den
        b = ((poly[2, 1] - poly[0, 1]) * (xx - poly[2, 0])
             + (poly[0, 0] - poly[2, 0]) * (yy - poly[2, 1])) / den
        c = 1 - a - b
        depth = a * z[0] + b * z[1] + c * z[2]
        region = depth_buffer[y0:y1+1, x0:x1+1]
        take = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6) & (depth > region)
        region[take] = depth[take]
        # Gentle depth falloff reveals the empty aperture and internal fasteners.
        depth_shade = .86 + .14 * np.clip((depth - z_min) / max(z_max - z_min, 1e-8), 0, 1)
        rgb = bitmap[y0:y1+1, x0:x1+1]
        rgb[take] = color * depth_shade[take, None]
    extent = [lo[0] - 1 / scale, lo[0] + (nx - 1) / scale,
              lo[1] - 1 / scale, lo[1] + (ny - 1) / scale]
    return bitmap, extent, lo, hi


def draw_view(fig, rect, parts, camera, title, pad=(10, 10, 15, 10), scale=7):
    ax = fig.add_axes(rect, facecolor=BG)
    bitmap, extent, lo, hi = raster(parts, camera, scale)
    ax.imshow(bitmap, origin="lower", extent=extent, interpolation="antialiased")
    ax.set_xlim(lo[0] - pad[0], hi[0] + pad[1])
    ax.set_ylim(lo[1] - pad[2], hi[1] + pad[3])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, color=INK, fontsize=13, fontweight="bold", pad=15)
    return ax, lo, hi


def dim_h(ax, x0, x1, y, source_y, text):
    ax.plot([x0, x0], [source_y, y - 1.5], color=PURPLE, lw=.65)
    ax.plot([x1, x1], [source_y, y - 1.5], color=PURPLE, lw=.65)
    ax.annotate("", (x0, y), (x1, y), arrowprops={"arrowstyle": "<->", "color": PURPLE, "lw": 1})
    ax.text((x0+x1)/2, y-4, text, ha="center", va="top", fontsize=11, color=PURPLE)


def dim_v(ax, y0, y1, x, source_x, text, side="left"):
    ax.plot([source_x, x+(-1.5 if side=="left" else 1.5)], [y0, y0], color=PURPLE, lw=.65)
    ax.plot([source_x, x+(-1.5 if side=="left" else 1.5)], [y1, y1], color=PURPLE, lw=.65)
    ax.annotate("", (x, y0), (x, y1), arrowprops={"arrowstyle": "<->", "color": PURPLE, "lw": 1})
    ax.text(x+(-3 if side=="left" else 3), (y0+y1)/2, text, rotation=90,
            ha="right" if side=="left" else "left", va="center", fontsize=11, color=PURPLE)


def figure_header(fig, title, subtitle):
    fig.text(.045, .942, title, fontsize=25, fontweight="bold", color=INK)
    fig.text(.045, .902, subtitle, fontsize=12, color=MUTED)


def assembly_sheet(parts):
    fig = plt.figure(figsize=(16, 9.5), dpi=140, facecolor=BG)
    figure_header(fig, "Step counter · printable CAD", "Cream covers + lavender shell  /  orthographic views  /  all dimensions in mm")
    front, lo, hi = draw_view(fig, [.025, .17, .33, .67], parts, [0, 0, -1], "FRONT", (17, 17, 20, 7))
    b0, b1 = bounds(parts)
    dim_h(front, b0[0], b1[0], b0[1]-8, b0[1], f"{b1[0]-b0[0]:g} overall")
    dim_v(front, -39, 39, b0[0]-8, -35, "78 body")
    dim_v(front, b0[1], b1[1], b1[0]+8, 35, f"{b1[1]-b0[1]:g} incl. loop", side="right")
    side_parts = parts
    side, slo, shi = draw_view(fig, [.37, .17, .215, .67], side_parts, [1, 0, 0], "RIGHT SIDE", (8, 8, 20, 7))
    # For this camera, screen-right is +Z, so the depth reads directly.
    dim_h(side, slo[0], shi[0], slo[1]-8, slo[1], f"{shi[0]-slo[0]:g} overall")
    draw_view(fig, [.612, .17, .36, .67], parts, [1.05, .65, -1.8], "ASSEMBLED", (8, 8, 20, 7))
    fig.text(.045, .105, "Actual exported STL geometry. Electronics are omitted; the display aperture is open.",
             color=INK, fontsize=12, fontweight="bold")
    fig.text(.045, .068, "Body 70 × 78 × 28 mm  ·  Print the fit checks before committing to a complete enclosure.", color=MUTED, fontsize=11)
    path = OUT / "model-preview.png"
    fig.savefig(path, dpi=140, facecolor=BG)
    plt.close(fig)
    return path


def exploded_parts(parts):
    moved = []
    for p in parts:
        if any(s in p.name for s in ("front", "feet", "foot", "cheek")):
            offset = (0, 0, -28)
        elif "back" in p.name:
            offset = (0, 0, 63)
        elif "carrier" in p.name:
            offset = (0, 0, 29)
        elif "clamp" in p.name:
            offset = (0, 0, 43)
        elif "retainer" in p.name:
            offset = (0, 0, 12)
        else:
            offset = (0, 0, 0)
        moved.append(p.shifted(offset))
    return moved


def interior_sheet(parts):
    fig = plt.figure(figsize=(16, 10), dpi=140, facecolor=BG)
    figure_header(fig, "Assembly & interior", "Actual CAD geometry  /  covers, retention parts and accelerometer carrier")
    exploded = exploded_parts(parts)
    draw_view(fig, [.025, .33, .62, .51], exploded, [1.6, .45, -1.1], "EXPLODED ASSEMBLY", (10, 10, 5, 5), scale=5.5)
    inside = [p for p in parts if "back" not in p.name]
    draw_view(fig, [.67, .34, .30, .50], inside, [-.3, .2, 1.8], "BACK COVER REMOVED", (8, 8, 5, 5))
    fig.text(.055, .28, "01  Front bezel", fontsize=12, fontweight="bold", color=INK)
    fig.text(.055, .245, "02  Main shell with integrated lanyard loop", fontsize=11, color=MUTED)
    fig.text(.055, .215, "03  Removable back cover", fontsize=11, color=MUTED)
    fig.text(.49, .28, "Internal retention", fontsize=12, fontweight="bold", color=INK)
    fig.text(.49, .245, "Sensor carrier, TFT retainers and sensor clamp", fontsize=11, color=MUTED)
    fig.text(.49, .215, "Clearance and fastening details are defined in the CAD source.", fontsize=11, color=MUTED)
    fig.text(.045, .125, "The exploded view separates printed parts along the enclosure depth; it is not an assembly spacing guide.",
             color=INK, fontsize=11)
    fig.text(.045, .087, "Screen and ADXL345 are not modelled as printed solids. Confirm the purchased board dimensions and hole locations.",
             color=MUTED, fontsize=11)
    path = OUT / "assembly-preview.png"
    fig.savefig(path, dpi=140, facecolor=BG)
    plt.close(fig)
    return path


def detail_sheet(parts):
    fig = plt.figure(figsize=(14, 9), dpi=140, facecolor=BG)
    figure_header(fig, "Mounting & rear cover", "Actual CAD geometry  /  electronics omitted  /  shallow face details are engraved for paint")
    front = [p for p in parts if any(s in p.name for s in ("front", "retainer", "foot", "cheek"))]
    rear = [p for p in parts if "back" in p.name]
    draw_view(fig, [.04, .23, .43, .60], front, [-.25, .18, 1.8],
              "FRONT SHELL — INSIDE", (7, 7, 5, 5))
    draw_view(fig, [.54, .23, .42, .60], rear, [.45, .22, 1.8],
              "BACK COVER — OUTSIDE", (7, 7, 5, 5))
    fig.text(.075, .18, "Carrier removed to expose the TFT retainers and cover posts.", color=INK, fontsize=11)
    fig.text(.57, .18, "Four recessed screw holes and the engraved character face.", color=INK, fontsize=11)
    fig.text(.045, .085, "Use the assembly guide for screw sizes, fit checks and the order of assembly.", color=MUTED, fontsize=11)
    path = OUT / "mounting-detail.png"
    fig.savefig(path, dpi=140, facecolor=BG)
    plt.close(fig)
    return path


def main():
    parts = load_parts()
    lo, hi = bounds(parts)
    results = [assembly_sheet(parts), interior_sheet(parts), detail_sheet(parts)]
    report = {"renders": [str(p) for p in results], "parts": len(parts),
              "assembly_bounds_mm": np.round([lo, hi], 3).tolist(),
              "overall_dimensions_mm": np.round(hi - lo, 3).tolist()}
    (OUT / "render-metadata.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
