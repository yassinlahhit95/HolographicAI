# Renderiza imagenes de prueba desde Camera_Main y las guarda como PNG en
# Saved/Preview. Abre el nivel, pero NO lo guarda.
# Espera varios cientos de fotogramas para que terminen de compilarse los shaders.
import unreal, os

OUT_DIR = os.path.join(unreal.Paths.project_saved_dir(), "Preview")
WAIT_TICKS = 900
SHOTS_AT = [WAIT_TICKS, WAIT_TICKS + 40, WAIT_TICKS + 80]   # 3 fotos seguidas
print("=== PREVIEW START ===")
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les.load_level("/Game/Hologram/L_Hologram")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

actors = eas.get_all_level_actors()
cam = [a for a in actors if a.get_actor_label() == "Camera_Main"][0]
cc = cam.get_component_by_class(unreal.CameraComponent)

rt = unreal.RenderingLibrary.create_render_target2d(
    world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8)
cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, cam.get_actor_location(),
                                 cam.get_actor_rotation())
sc = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
sc.set_editor_property("texture_target", rt)
sc.set_editor_property("fov_angle", cc.get_editor_property("field_of_view"))
sc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
os.makedirs(OUT_DIR, exist_ok=True)

state = {"tick": 0}

def on_tick(dt):
    state["tick"] += 1
    t = state["tick"]
    if t % 150 == 0:
        print("tick", t)
    sc.capture_scene()
    if t in SHOTS_AT:
        name = "preview_%d.png" % SHOTS_AT.index(t)
        unreal.RenderingLibrary.export_render_target(world, rt, OUT_DIR, name)
        print("saved:", name)
    if t >= SHOTS_AT[-1]:
        unreal.unregister_slate_post_tick_callback(handle)
        print("=== PREVIEW END ===")
        unreal.SystemLibrary.quit_editor()

handle = unreal.register_slate_post_tick_callback(on_tick)
