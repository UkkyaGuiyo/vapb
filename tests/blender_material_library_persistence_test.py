"""A late material provider remains available across save/reopen before binding."""

import sys
import tempfile
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unitypackage_blender_importer.blender.material_builder import build_material
from unitypackage_blender_importer.unity.material_model import UnityMaterialData


class SyntheticAssetDB:
    source_package_id = "synthetic-provider"

    def find_guid(self, _guid):
        return None


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    guid = "b" * 32
    material = build_material(
        UnityMaterialData(path=Path("Synthetic.mat"), name="SyntheticProvider",
                          guid=guid, unity_path="Assets/Synthetic.mat", file_id=2100000),
        SyntheticAssetDB(), use_textures=False,
    )
    assert not any(material is slot.material for obj in bpy.data.objects for slot in obj.material_slots)
    with tempfile.TemporaryDirectory(prefix="vapb_provider_") as folder:
        blend = str(Path(folder) / "provider.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend, check_existing=False)
        bpy.ops.wm.open_mainfile(filepath=blend, load_ui=False)
        matches = [item for item in bpy.data.materials
                   if item.get("unity_material_guid") == guid
                   and item.get("unity_source_package_id") == "synthetic-provider"]
        assert len(matches) == 1, len(matches)
    print("UNBOUND_PROVIDER_PERSISTENCE=PASS")


if __name__ == "__main__":
    main()
