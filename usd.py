import unreal
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--file')
parser.add_argument('-l', '--level', action="store_true")
parser.add_argument('-o', '--options', nargs='+')
parser.add_argument('-u', '--usd_obj', action="store_true")

def export_level_to_usd(output_path):
    """
    Exports the current level to a USD file using LevelExporterUSD.

    :param output_path: The file path where the USD file will be saved.
    """
    # Create an instance of the USD level exporter
    usd_export_task = unreal.AssetExportTask()
    
    # Configure the export task
    usd_export_task.automated = True
    usd_export_task.replace_identical = True
    usd_export_task.prompt = False
    usd_export_task.exporter = unreal.LevelExporterUSD()  # Use the LevelExporterUSD class
    usd_export_task.filename = output_path
    usd_export_task.object = unreal.EditorLevelLibrary.get_editor_world()
    
    # Perform the export
    success = unreal.Exporter.run_asset_export_task(usd_export_task)
    
    if success:
        unreal.log(f"Successfully exported level to USD at: {output_path}")
    else:
        unreal.log_error(f"Failed to export level to USD at: {output_path}")

def export_ls_to_usd(output):
    """
    Exports all the LevelSequenceActors from the outliner

    :param output: The directory where all USD files will be saved
    """
    # Get the current world
    editor_level_library = unreal.EditorLevelLibrary()

    # Get all Level Sequence Actors in the level
    actors = editor_level_library.get_all_level_actors()
    level_sequence_actors = [actor for actor in actors if isinstance(actor, unreal.LevelSequenceActor)]

    # Create an instance of the USD level exporter
    usd_export_task = unreal.AssetExportTask()

    # USD Export Settings
    usd_export_task.automated = True
    usd_export_task.replace_identical = True
    usd_export_task.prompt = False
    usd_export_task.exporter = unreal.LevelSequenceExporterUsd()

    # Export each Level Sequence
    for lsa in level_sequence_actors:
        sequence = lsa.get_sequence()  # Get the Level Sequence asset
        if sequence:
            usd_export_task.object = sequence
            output_path = os.path.join(os.path.dirname(output), f"{sequence.get_name()}.usda")
            usd_export_task.filename = output_path
            success = unreal.Exporter.run_asset_export_task(usd_export_task)
            if success:
                unreal.log(f"Successfully exported level to USD at: {output_path}")
            else:
                unreal.log_error(f"Failed to export level to USD at: {output_path}")
            if args.usd_obj:
                spawnable_mesh(sequence, output, "all")

def export_select(selected, output):
    """
    Exports all selected LevelSequences

    :param selected: array of the LevelSequences' paths
    :param output: The directory where all USD files will be saved 
    """
    # Create an instance of the USD level exporter
    usd_export_task = unreal.AssetExportTask()

    # USD Export Settings
    usd_export_task.automated = True
    usd_export_task.replace_identical = True
    usd_export_task.prompt = False
    usd_export_task.exporter = unreal.LevelSequenceExporterUsd()
    for asset_path in selected:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset:
            usd_export_task.object = asset
            usd_export_task.filename = os.path.join(output, f"{asset.get_name()}.usda")
            success = unreal.Exporter.run_asset_export_task(usd_export_task)
            if success:
                unreal.log(f"Successfully exported {asset_path}")
            else:
                unreal.log_error(f"Failed to export {asset_path}")
            if args.usd_obj:
                spawnable_mesh(asset, output, "selected")

def spawnable_mesh(sequence, output, mode):
    """
    Exports the spawnable meshes in a LevelSequence

    :param sequence: The LevelSeuence being scanned for spawnable meshes
    :param output: The directory where all USD files will be saved 
    :param mode: Parameter to know whether it needs to look at parent directory or not
    """
    # USD Export Settings
    export_task = unreal.AssetExportTask()
    export_task.automated = True
    export_task.replace_identical = True
    export_task.prompt = False
    spawnables = sequence.get_spawnables()
    for spawn in spawnables:
        object_template = spawn.get_object_template() # Get templaye of spawnable
        if isinstance(object_template, unreal.StaticMeshActor):
            sm_component = object_template.static_mesh_component
            if sm_component:
                mesh = sm_component.get_editor_property('static_mesh') # Get the static mesh the actor is using
                if mesh and mesh not in exported_meshes:
                    export_path = os.path.join(output, f"{mesh.get_name()}.obj") if mode == "selected" else os.path.join(os.path.dirname(output), f"{mesh.get_name()}.obj")
                    export_task.object = mesh
                    export_task.filename = export_path
                    success = unreal.Exporter.run_asset_export_tasks([export_task])
                    if success:
                        unreal.log(f"Exported: {export_path}")
                        exported_meshes.add(mesh)  # Avoid duplicate exports
                    else:
                        unreal.log(f"Failed to export: {mesh.get_name()}")
                else:
                    unreal.log("No static mesh is assigned to this actor.")

args = parser.parse_args()
exported_meshes = set()
if args.options:
    export_select(args.options, args.file)
else:
    export_level_to_usd(args.file)
    if args.level:
        export_ls_to_usd(args.file)