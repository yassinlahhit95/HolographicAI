# Stage 1 - crea material holografico + nivel negro + camara.
# Crea solo cosas NUEVAS en /Game/Hologram. No modifica /Game/MetaHumans.
import unreal

MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
HEAD_TEX = "/Game/MetaHumans/yassinAI/Face/Baked/T_Head_BC"
FACE_MESH = "/Game/MetaHumans/yassinAI/Face/SKM_yassinAI_FaceMesh"
DIR = "/Game/Hologram"
print("=== BUILD START ===")

EAL.make_directory(DIR)

# ---------------------------------------------------------------- material
def build_material():
    name = "M_Hologram"
    if EAL.does_asset_exist(DIR + "/" + name):
        EAL.delete_asset(DIR + "/" + name)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = tools.create_asset(name, DIR, unreal.Material, unreal.MaterialFactoryNew())

    for prop, val in [("shading_model", unreal.MaterialShadingModel.MSM_UNLIT),
                      # Opaco: con translucido se veia el interior de la boca
                      # y la cavidad de la cabeza a traves de la piel.
                      ("blend_mode", unreal.BlendMode.BLEND_OPAQUE),
                      ("used_with_skeletal_mesh", True),
                      ("used_with_morph_targets", True)]:
        try:
            mat.set_editor_property(prop, val)
        except Exception as e:
            print("WARN property", prop, e)

    def node(cls, x, y, **props):
        n = MEL.create_material_expression(mat, cls, x, y)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def const(v, x, y):
        return node(unreal.MaterialExpressionConstant, x, y, r=v)

    def op(cls, a, b, x, y):
        n = node(cls, x, y)
        MEL.connect_material_expressions(a, "", n, "A")
        MEL.connect_material_expressions(b, "", n, "B")
        return n

    Mul = unreal.MaterialExpressionMultiply
    Add = unreal.MaterialExpressionAdd

    tex = node(unreal.MaterialExpressionTextureSampleParameter2D, -1400, -300,
               parameter_name="FaceTex", texture=EAL.load_asset(HEAD_TEX))
    desat = node(unreal.MaterialExpressionDesaturation, -1150, -300)
    MEL.connect_material_expressions(tex, "RGB", desat, "")
    lum = op(Mul, desat, const(1.7, -1150, -150), -950, -300)

    fres = node(unreal.MaterialExpressionFresnel, -1150, 0, exponent=2.5)
    fres_k = op(Mul, fres, const(1.6, -1150, 120), -950, 0)

    base = op(Add, lum, fres_k, -750, -150)
    base = op(Add, base, const(0.08, -750, 0), -600, -150)

    # lineas de escaneo suaves (suben con el tiempo)
    wp = node(unreal.MaterialExpressionWorldPosition, -1400, 300)
    z = node(unreal.MaterialExpressionComponentMask, -1200, 300, b=True)
    MEL.connect_material_expressions(wp, "", z, "")
    zf = op(Mul, z, const(0.15, -1200, 420), -1000, 300)
    t = node(unreal.MaterialExpressionTime, -1400, 500)
    tf = op(Mul, t, const(0.3, -1400, 620), -1200, 520)
    ph = op(Add, zf, tf, -800, 400)
    sn = node(unreal.MaterialExpressionSine, -620, 400)
    MEL.connect_material_expressions(ph, "", sn, "")
    sn_k = op(Mul, sn, const(0.08, -620, 520), -440, 400)
    scan = op(Add, sn_k, const(0.92, -440, 540), -260, 400)

    shaded = op(Mul, base, scan, -60, -50)
    cyan = node(unreal.MaterialExpressionConstant3Vector, -60, 120,
                constant=unreal.LinearColor(0.0, 0.75, 1.0, 1.0))
    emissive = op(Mul, shaded, cyan, 160, 0)
    MEL.connect_material_property(emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    op_f = op(Mul, fres, const(0.4, -950, 220), -750, 220)
    opacity = op(Add, op_f, const(0.6, -750, 320), -560, 260)
    MEL.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)

    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    print("material OK:", mat.get_path_name())
    return mat

# ---------------------------------------------------------------- ojos
IRIS_TEX = "/Game/MetaHumans/yassinAI/Face/Baked/T_EyeIrisL_BC"
CORNEA_R = 0.165      # radio del iris en las UV del globo ocular (MetaHuman "Cornea Size")

def build_eye_material():
    """Ojo holografico: iris cian brillante con el detalle real del iris,
    pupila oscura, anillo luminoso en el borde y blanco del ojo tenue."""
    name = "M_HologramEye"
    if EAL.does_asset_exist(DIR + "/" + name):
        EAL.delete_asset(DIR + "/" + name)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = tools.create_asset(name, DIR, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property("used_with_skeletal_mesh", True)
    mat.set_editor_property("used_with_morph_targets", True)

    def node(cls, x, y, **props):
        n = MEL.create_material_expression(mat, cls, x, y)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n
    def const(v, x, y):
        return node(unreal.MaterialExpressionConstant, x, y, r=v)
    def op(cls, a, b, x, y):
        n = node(cls, x, y)
        MEL.connect_material_expressions(a, "", n, "A")
        MEL.connect_material_expressions(b, "", n, "B")
        return n
    def one(cls, a, x, y, **props):
        n = node(cls, x, y, **props)
        MEL.connect_material_expressions(a, "", n, "")
        return n
    Mul, Add, Sub, Div = (unreal.MaterialExpressionMultiply, unreal.MaterialExpressionAdd,
                          unreal.MaterialExpressionSubtract, unreal.MaterialExpressionDivide)
    Sat = unreal.MaterialExpressionSaturate

    uv = node(unreal.MaterialExpressionTextureCoordinate, -1600, 0)
    center = node(unreal.MaterialExpressionConstant2Vector, -1600, 120, r=0.5, g=0.5)
    d = op(unreal.MaterialExpressionDistance, uv, center, -1400, 0)

    # UV del iris: la textura del iris es un primer plano -> ampliamos alrededor del centro
    irs = 2.0 * CORNEA_R / 0.86
    iuv = op(Add, op(Div, op(Sub, uv, center, -1400, -300), const(irs, -1400, -180), -1250, -300),
             center, -1100, -300)
    tex = node(unreal.MaterialExpressionTextureSampleParameter2D, -950, -300,
               parameter_name="IrisTex", texture=EAL.load_asset(IRIS_TEX))
    MEL.connect_material_expressions(iuv, "", tex, "UVs")
    lum = one(unreal.MaterialExpressionDesaturation, tex, -700, -300)
    MEL.connect_material_expressions(tex, "RGB", lum, "")
    detail = one(Sat, op(Mul, lum, const(3.2, -700, -180), -550, -300), -400, -300)

    # mascara del iris (suave en el borde) y anillo luminoso del limbo
    iris_mask = one(Sat, op(Div, op(Sub, const(CORNEA_R + 0.01, -1250, 100), d, -1100, 60),
                            const(0.02, -1100, 180), -950, 60), -800, 60)
    ring_d = one(unreal.MaterialExpressionAbs, op(Sub, d, const(CORNEA_R, -1250, 260), -1100, 260), -950, 260)
    ring = one(Sat, op(Sub, const(1.0, -950, 380), op(Div, ring_d, const(0.012, -950, 440), -800, 300),
                       -650, 300), -500, 300)

    cyan = node(unreal.MaterialExpressionConstant3Vector, -400, -120,
                constant=unreal.LinearColor(0.1, 0.85, 1.0, 1.0))
    iris_col = op(Mul, op(Mul, detail, const(2.2, -400, -20), -250, -200), cyan, -100, -200)
    sclera_col = op(Mul, cyan, const(0.22, -250, 80), -100, 40)
    base = node(unreal.MaterialExpressionLinearInterpolate, 80, -60)
    MEL.connect_material_expressions(sclera_col, "", base, "A")
    MEL.connect_material_expressions(iris_col, "", base, "B")
    MEL.connect_material_expressions(iris_mask, "", base, "Alpha")
    ring_col = op(Mul, op(Mul, ring, const(1.5, -350, 420), -200, 360), cyan, -50, 360)
    final = op(Add, base, ring_col, 250, 0)
    MEL.connect_material_property(final, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    print("eye material OK:", mat.get_path_name())
    return mat

# ---------------------------------------------------------------- level
def build_level(mat, eye_mat):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    path = DIR + "/L_Hologram"
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    les.new_level(path)

    # IMPORTANTE: no usamos BP_yassinAI. Su script de construccion vuelve a
    # crear los materiales de la piel cada vez que se carga el nivel y borraba
    # nuestro material holografico. Un SkeletalMeshActor normal con la malla de
    # la cara conserva los materiales que le ponemos.
    face_mesh = unreal.load_asset(FACE_MESH)
    head = eas.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0))
    head.set_actor_label("Head_yassinAI")
    face = head.get_component_by_class(unreal.SkeletalMeshComponent)
    face.set_skeletal_mesh_asset(face_mesh)

    hide_mat = None
    slots = face_mesh.get_editor_property("materials")
    for s in slots:
        mi = s.get_editor_property("material_interface")
        if mi and mi.get_name() == "M_Hide":
            hide_mat = mi
            break

    for i, s in enumerate(slots):
        slot = str(s.get_editor_property("material_slot_name"))
        low = slot.lower()
        # Dientes con material holografico: al abrir la boca al hablar se ven.
        if low.startswith("head") or low.startswith("teeth"):
            face.set_material(i, mat)            # holograma (cara + todos los LOD)
            what = "hologram"
        elif low.startswith("eyeleft") or low.startswith("eyeright"):
            face.set_material(i, eye_mat)        # ojos cian brillantes
            what = "hologram eye"
        elif hide_mat:
            face.set_material(i, hide_mat)       # pestanas, saliva, lagrimal...
            what = "hidden"
        else:
            what = "original"
        print("slot %d %-28s -> %s" % (i, slot, what))

    # Siempre el LOD de mas calidad (LOD0) para que no cambie de material.
    try:
        face.set_forced_lod(1)
    except Exception as e:
        print("WARN forced lod", e)

    # Animacion autonoma (C++: Source/HolographicAI/HoloFaceAnimInstance.cpp).
    # Parpadeo, mirada, cuello/cabeza y respiracion; no depende de la IA.
    face.set_mobility(unreal.ComponentMobility.MOVABLE)   # la cabeza gira sobre el cuello
    face.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    face.set_anim_instance_class(unreal.HoloFaceAnimInstance.static_class())
    print("anim class:", face.get_editor_property("anim_class"))

    # La cara del MetaHuman mira hacia +Y. Apuntamos la camara al punto
    # medio entre los ojos, un poco por debajo para encuadrar toda la cabeza.
    le = face.get_socket_location("FACIAL_L_Eye")
    re = face.get_socket_location("FACIAL_R_Eye")
    target = unreal.Vector((le.x + re.x) / 2, (le.y + re.y) / 2, (le.z + re.z) / 2 - 4)
    print("look target:", target)

    # Rotator(roll, pitch, yaw): yaw -90 = mirar hacia -Y (hacia la cara)
    cam = eas.spawn_actor_from_class(unreal.CameraActor,
                                     unreal.Vector(target.x, target.y + 95, target.z),
                                     unreal.Rotator(0, 0, -90))
    cam.set_actor_label("Camera_Main")
    cc = cam.get_component_by_class(unreal.CameraComponent)
    cc.set_editor_property("field_of_view", 30.0)
    cam.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)

    pp = eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
    pp.set_actor_label("PostProcess_Hologram")
    pp.set_editor_property("unbound", True)
    s = pp.get_editor_property("settings")
    s.set_editor_property("override_auto_exposure_method", True)
    s.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    # Sin camara fisica: si no, los materiales emisivos se ven casi negros
    s.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
    s.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
    s.set_editor_property("override_auto_exposure_bias", True)
    s.set_editor_property("auto_exposure_bias", 0.0)
    s.set_editor_property("override_bloom_intensity", True)
    s.set_editor_property("bloom_intensity", 1.0)
    pp.set_editor_property("settings", s)

    # Sin luces: piel y ojos son emisivos (brillan por si solos).

    # Etapa 2: director de voz (C++ HoloDirector). Reproduce la presentacion al
    # arrancar y la repite con la tecla R.
    director = eas.spawn_actor_from_class(unreal.HoloDirector, unreal.Vector(0, 0, 0))
    director.set_actor_label("HoloDirector")
    print("director:", director.get_class().get_name())

    les.save_current_level()
    print("level OK:", path)

try:
    m = build_material()
    e = build_eye_material()
    build_level(m, e)
except Exception as e:
    import traceback
    print("BUILD ERROR:", e)
    traceback.print_exc()
print("=== BUILD END ===")
