import unreal
import os
import glob
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--file')
args = parser.parse_args()
print(args.file)

actors = unreal.EditorLevelLibrary.get_all_level_actors()
export_dir = os.path.join(os.path.abspath(args.file), "objects")
exported_meshes = set()
# Ensure the export directory exists
if not os.path.exists(export_dir):
    os.makedirs(export_dir)

for actor in actors:
    if isinstance(actor, unreal.StaticMeshActor):
        static_mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if static_mesh_component:
            static_mesh = static_mesh_component.static_mesh
            if static_mesh and static_mesh not in exported_meshes:
                mesh_name = static_mesh.get_name()
                unreal.log(f"Found static mesh: {mesh_name}")
                export_path = os.path.join(export_dir, f"{mesh_name}.obj")
                export_task = unreal.AssetExportTask()
                export_task.object = static_mesh
                export_task.filename = export_path
                export_task.automated = True
                export_task.replace_identical = True
                export_task.prompt = False
                success = unreal.Exporter.run_asset_export_tasks([export_task])
                if success:
                    unreal.log(f"Exported: {export_path}")
                    exported_meshes.add(static_mesh)  # Avoid duplicate exports
                else:
                    unreal.log(f"Failed to export: {mesh_name}")
            else:
                unreal.log("No static mesh is assigned to this actor.")

for file in glob.glob(os.path.join(export_dir, "*.obj")):
    if "_Internal.obj" in file or "_UV1.obj" in file:
        os.remove(file)