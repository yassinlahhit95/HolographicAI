# Diagnostico del material M_Hologram. Solo lectura.
import unreal
print("=== MATCHECK START ===")
mat = unreal.load_asset("/Game/Hologram/M_Hologram")
for p in ["shading_model", "blend_mode", "used_with_skeletal_mesh",
          "used_with_morph_targets", "two_sided"]:
    try:
        print("prop", p, "=", mat.get_editor_property(p))
    except Exception as e:
        print("prop", p, "ERR", e)
try:
    st = unreal.MaterialEditingLibrary.get_statistics(mat)
    print("stats: vs=%s ps=%s samplers=%s" % (st.num_vertex_shader_instructions,
          st.num_pixel_shader_instructions, st.num_samplers))
except Exception as e:
    print("stats ERR", e)
print("num expressions:", unreal.MaterialEditingLibrary.get_num_material_expressions(mat))
for prop in [unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialProperty.MP_OPACITY]:
    n = unreal.MaterialEditingLibrary.get_material_property_input_node(mat, prop)
    print("input", prop, "->", n.get_class().get_name() if n else None)
print("=== MATCHECK END ===")
