# Box miroir + porte de bateau. Lancer : blender -b -P box_miroir.py
import bpy, bmesh, math, os

# --- Dimensions (mètres) : ajuster ici ---
W, D, H = 4.0, 3.0, 2.6          # largeur (x), profondeur (y), hauteur (z) de la box
DOOR_W, DOOR_H, DOOR_R = 0.95, 2.15, 0.32   # porte : largeur, hauteur, rayon des coins
DOOR_X, DOOR_Z0 = 0.9, 0.12      # position : décalage horizontal, hauteur du bas
DOOR_T = 0.10                    # épaisseur de porte (saillie)

OUT = os.path.dirname(os.path.abspath(__file__))
FRONT = -D / 2                   # face avant (y)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, color, metallic=0.0, rough=0.5):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    return m


MIRROR = mat("Miroir", (0.93, 0.94, 0.93), 1.0, 0.012)
CORE = mat("Joint", (0.02, 0.02, 0.02), 0.0, 0.6)
WHITE = mat("Porte_Blanc", (0.86, 0.86, 0.84), 0.0, 0.35)
WHITE.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 0.4
BRASS = mat("Laiton", (0.85, 0.62, 0.28), 1.0, 0.22)
GLASS = mat("Hublot_Verre", (0.02, 0.03, 0.04), 0.0, 0.03)
GROUND = mat("Sol", (0.35, 0.35, 0.36), 0.0, 0.45)


def obj(name, mesh, material):
    o = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(o)
    o.data.materials.append(material)
    return o


def smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


def bevel_mod(o, width, segs=3):
    m = o.modifiers.new("Bevel", "BEVEL")
    m.width, m.segments, m.limit_method = width, segs, "ANGLE"
    o.modifiers.new("WN", "WEIGHTED_NORMAL")


def rounded_slab(name, w, h, r, t, y, material, z0):
    """Rectangle arrondi (plan XZ) extrudé vers -y sur une épaisseur t."""
    bm = bmesh.new()
    x0 = DOOR_X - w / 2
    vs = [bm.verts.new(c) for c in [(x0, y, z0), (x0 + w, y, z0), (x0 + w, y, z0 + h), (x0, y, z0 + h)]]
    bm.faces.new(vs)
    bmesh.ops.bevel(bm, geom=vs, offset=r, offset_type="OFFSET", segments=16, profile=0.5, affect="VERTICES")
    bm.faces.ensure_lookup_table()
    face = bm.faces[0]
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, -t, 0), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = obj(name, me, material)
    bevel_mod(o, 0.012)
    return o


# --- Box : noyau sombre + panneaux miroir séparés par des joints ---
PANEL, GAP, T = 1.3, 0.004, 0.01   # largeur max d'un panneau, joint, épaisseur


def cube(name, loc, size, material, bevel=0.002):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name, o.scale = name, size
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(material)
    bevel_mod(o, bevel, 2)
    return o


cube("Box_Noyau", (0, 0, H / 2), (W - 2 * T, D - 2 * T, H - T), CORE)
cube("Box_Toit", (0, 0, H - T / 2), (W, D, T), MIRROR)
for side, (length, axis, off) in enumerate([(W, "x", -D / 2), (W, "x", D / 2), (D, "y", -W / 2), (D, "y", W / 2)]):
    n = math.ceil(length / PANEL)
    pw = length / n
    for i in range(n):
        c = -length / 2 + pw * (i + 0.5)
        thick = off - math.copysign(T / 2, off)
        loc = (c, thick, (H - T) / 2) if axis == "x" else (thick, c, (H - T) / 2)
        size = (pw - GAP, T, H - T - GAP) if axis == "x" else (T, pw - GAP, H - T - GAP)
        cube(f"Miroir_{side}_{i}", loc, size, MIRROR)

# --- Cadre + porte ---
rounded_slab("Cadre_Porte", DOOR_W + 0.08, DOOR_H + 0.08, DOOR_R + 0.04, 0.03, FRONT, WHITE, DOOR_Z0 - 0.04)
door = rounded_slab("Porte", DOOR_W, DOOR_H, DOOR_R, DOOR_T, FRONT - 0.03, WHITE, DOOR_Z0)
door_face = FRONT - 0.03 - DOOR_T


def torus(name, loc, R, r, material):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc,
                                     rotation=(math.pi / 2, 0, 0), major_segments=64, minor_segments=16)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    smooth(o)
    return o


def cyl(name, loc, radius, depth, rot, material):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc, rotation=rot, vertices=32)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    smooth(o)
    return o


# Hublot : bague laiton + verre
pz = DOOR_Z0 + DOOR_H - 0.42
torus("Hublot_Bague", (DOOR_X, door_face - 0.02, pz), 0.17, 0.035, BRASS)
cyl("Hublot_Verre", (DOOR_X, door_face - 0.005, pz), 0.15, 0.01, (math.pi / 2, 0, 0), GLASS)

# Volant (côté gauche) : jante, moyeu, 6 rayons, poignées
wx, wz, wy = DOOR_X - DOOR_W / 2 + 0.16, DOOR_Z0 + 1.0, door_face - 0.09
parts = [torus("Volant_Jante", (wx, wy, wz), 0.14, 0.012, BRASS),
         cyl("Volant_Moyeu", (wx, wy, wz), 0.03, 0.04, (math.pi / 2, 0, 0), BRASS),
         cyl("Volant_Axe", (wx, (wy + door_face) / 2, wz), 0.012, door_face - wy, (math.pi / 2, 0, 0), BRASS)]
for i in range(6):
    a = i * math.pi / 3
    parts.append(cyl(f"Volant_Rayon_{i}", (wx + 0.075 * math.cos(a), wy, wz + 0.075 * math.sin(a)),
                     0.007, 0.15, (0, math.pi / 2 - a, 0), BRASS))
    parts.append(cyl(f"Volant_Poignee_{i}", (wx + 0.175 * math.cos(a), wy, wz + 0.175 * math.sin(a)),
                     0.012, 0.05, (0, math.pi / 2 - a, 0), BRASS))
# Levier de verrouillage à droite du volant
parts.append(cyl("Levier", (wx + 0.22, door_face - 0.03, wz + 0.05), 0.014, 0.22, (0, 0, 0), BRASS))

# Charnières (côté droit)
hx = DOOR_X + DOOR_W / 2 + 0.01
for i, z in enumerate((DOOR_Z0 + 0.35, DOOR_Z0 + DOOR_H - 0.35)):
    cyl(f"Charniere_{i}", (hx, door_face + 0.03, z), 0.03, 0.22, (0, 0, 0), WHITE)

# Parent tout à la porte (pour la déplacer/ouvrir d'un bloc)
for o in scene.objects:
    if o.name.startswith(("Hublot", "Volant", "Levier")):
        o.parent = door

# --- Sol, lumière, caméra, ciel ---
# Sol invisible qui ne garde que les ombres : le sol de l'HDRI reste visible
bpy.ops.mesh.primitive_plane_add(size=60)
bpy.context.object.name = "Sol"
bpy.context.object.data.materials.append(GROUND)
bpy.context.object.is_shadow_catcher = True

bpy.ops.object.camera_add(location=(5.5, -7.0, 1.6))
cam = bpy.context.object
cam.data.lens = 35
c = cam.constraints.new("TRACK_TO")
bpy.ops.object.empty_add(location=(0.3, 0, 1.2))
c.target = bpy.context.object
scene.camera = cam

# Éclairage + reflets : HDRI de place urbaine (Poly Haven, CC0)
HDRI_ROT = 225  # degrés : tourner la ville autour de la box
world = bpy.data.worlds.new("Ville")
world.use_nodes = True
scene.world = world
nt = world.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(OUT, "potsdamer_platz_4k.hdr"))
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value[2] = math.radians(HDRI_ROT)
nt.links.new(nt.nodes.new("ShaderNodeTexCoord").outputs["Generated"], mapping.inputs[0])
nt.links.new(mapping.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0])

# Le sol reflété dans les miroirs = sol de l'HDRI projeté depuis la hauteur de prise de vue
gt = GROUND.node_tree
out, bsdf = gt.nodes["Material Output"], gt.nodes["Principled BSDF"]
pos = gt.nodes.new("ShaderNodeVectorMath")
pos.operation = "SUBTRACT"
pos.inputs[1].default_value = (0, 0, 1.7)
gt.links.new(gt.nodes.new("ShaderNodeNewGeometry").outputs["Position"], pos.inputs[0])
gmap = gt.nodes.new("ShaderNodeMapping")
gmap.inputs["Rotation"].default_value[2] = math.radians(HDRI_ROT)
gt.links.new(pos.outputs[0], gmap.inputs[0])
genv = gt.nodes.new("ShaderNodeTexEnvironment")
genv.image = env.image
gt.links.new(gmap.outputs[0], genv.inputs[0])
emit = gt.nodes.new("ShaderNodeEmission")
gt.links.new(genv.outputs[0], emit.inputs[0])
mix = gt.nodes.new("ShaderNodeMixShader")
gt.links.new(gt.nodes.new("ShaderNodeLightPath").outputs["Is Camera Ray"], mix.inputs[0])
gt.links.new(emit.outputs[0], mix.inputs[1])
gt.links.new(bsdf.outputs[0], mix.inputs[2])
gt.links.new(mix.outputs[0], out.inputs[0])

scene.render.engine = "CYCLES"
scene.cycles.samples = 128
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "box_miroir.blend"))
scene.render.filepath = os.path.join(OUT, "apercu.png")
bpy.ops.render.render(write_still=True)
