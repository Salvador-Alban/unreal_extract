import unreal
import json
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--file')
parser.add_argument('-o', '--obj', action='store_true')


def ls_static_mesh(actor, world):
    sequence = actor.get_sequence() # Get the MovieSequence
    bindings = sequence.get_bindings() # Get all the MovieSceneBindingProxy
    objects = []
    # Get the bound object per MovieSceneBindingProxy
    for binding in bindings:
        obs = sequence.locate_bound_objects(binding, world)
        objects.append(obs) 
    return objects

def extract(file, obj):
    """
    Exports the current level to a JSON file.

    :param file: The file path where the JSON file will be saved.
    :param obj: Boolean for extracting OBJs
    :param path: The path of the main code directory
    """
    if obj:
        export_dir = os.path.join(os.path.dirname(file), "objects")
        exported_meshes = set()
        # Ensure the export directory exists
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

    world = unreal.EditorLevelLibrary.get_editor_world()
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    outliner_data = []
    for actor in actors:
        actor_info = {
            "name": actor.get_actor_label(),
            "class": actor.get_class().get_name(),
        }
        if isinstance(actor, unreal.StaticMeshActor):
            static_mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
            if static_mesh_component:
                static_mesh = static_mesh_component.static_mesh
                actor_info["mesh"] = static_mesh.get_name() if static_mesh else "None"
                if obj:
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
        if (isinstance(actor, unreal.CineCameraActor)):
            cine_camera_component = actor.get_cine_camera_component()
            rotation = cine_camera_component.relative_rotation
            filmback_settings = cine_camera_component.filmback
            post_process = cine_camera_component.post_process_settings
            lut = post_process.color_grading_lut
            actor_info["Camera Settings"] = {
                "Sensor Width": filmback_settings.sensor_width,
                "Sensor Height": filmback_settings.sensor_height,
                "Aspect Ratio": filmback_settings.sensor_aspect_ratio,
                "Focal Length": cine_camera_component.current_focal_length,
                "Aperture": cine_camera_component.current_aperture,
                "Focus Distance": cine_camera_component.current_focus_distance,
                "ISO": post_process.camera_iso,
                "Tilt": rotation.pitch,
                "Roll": rotation.roll,
            }
        if isinstance(actor, unreal.LevelSequenceActor):
            bound_objects = ls_static_mesh(actor, world)
            bound_list = []
            for object in bound_objects:
                if len(object) > 0:
                    if isinstance(object[0], unreal.Actor):
                        bound_list.append(object[0].get_actor_label())
            actor_info["Bound Actors"] = {
                "names": bound_list
            }

        outliner_data.append(actor_info)
    
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    class_path = unreal.TopLevelAssetPath("/Script/LevelSequence.LevelSequence")
    assets = registry.get_assets_by_class(class_path, True)

    level_sequences = []

    for asset_data in assets:
        x = {"name": str(asset_data.asset_name), "path": str(asset_data.package_path)}
        level_sequences.append(x)
        
    outliner_data.append(level_sequences)

    json_object = json.dumps(outliner_data, indent=4)
    with open(file, "w") as outfile:
        outfile.write(json_object)

args = parser.parse_args()
extract(args.file, args.obj)
if args.obj:
    import glob
    export_dir = os.path.join(os.path.dirname(args.file), "objects")
    for file in glob.glob(os.path.join(export_dir, "*.obj")):
        if "_Internal.obj" in file or "_UV1.obj" in file:
            os.remove(file)
            
print("Done!")