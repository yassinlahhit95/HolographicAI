# Solo LEE informacion. No guarda nada en el proyecto.
import unreal

print("=== INSPECT START ===")
bp = unreal.load_asset("/Game/MetaHumans/yassinAI/BP_yassinAI")
print("blueprint:", bp)
cls = bp.generated_class() if hasattr(bp, "generated_class") else None
print("class:", cls)

# Nivel temporal en memoria (no se guarda)
unreal.EditorLevelLibrary.new_level("/Temp/InspectLevel")
actor = unreal.EditorLevelLibrary.spawn_actor_from_class(cls, unreal.Vector(0, 0, 0))
print("actor:", actor)

for comp in actor.get_components_by_class(unreal.SceneComponent):
    line = "%s | %s" % (comp.get_name(), comp.get_class().get_name())
    if isinstance(comp, unreal.SkeletalMeshComponent):
        mesh = comp.get_editor_property("skeletal_mesh_asset")
        line += " | mesh=%s" % (mesh.get_name() if mesh else None)
        for i, slot in enumerate(comp.get_material_slot_names()):
            mat = comp.get_material(i)
            line += "\n      slot %d %s -> %s" % (i, slot, mat.get_name() if mat else None)
    print(line)
print("=== INSPECT END ===")
