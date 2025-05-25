# Introduction
This GUI is intended to be used to help extract information from Unreal Engine projects and organise it to send it to the next person of interest. It also allows for the categorisation of StaticMeshActors using [CLIP](https://github.com/openai/CLIP). We leverage the zero-shot prediction capabilities of CLIP by taking rotating pictures of the mesh and averaging predictions for each object and seeing which of the user inputted categories they fin into.

# Set up Instructions
1. Set up the conda envvironment using the `environment.yaml` file
2. Install and build the USD code following [these instructions](https://github.com/PixarAnimationStudios/OpenUSD)
3. Set up a MySQL database using the schemas foudn in the `schemas` folder 
4. Make sure to edit the database details in the `info.yaml` file for the database

# Tutorial

## Extraction
1. Activate the virtual environment and run the `joined_gui.py`
2. Select the `.uproject` file that you want to extract information from using the **Select Project** button
3. Click on the **Extract Outliner** button to pull information from the level outliner of your project and select a directory to save it as a `.json` file
    - If you wish to export the StaticMeshActors as OBJ file for the classification, a pop-up will show up to ask you.
4. Click on the **Extract Scene as USD** button to export the project as a `.usda` file. 
    - If you wish to also save the animations, a pop-up will show up to ask you. 
5. Once you have uploaded extracted the `.json` file, click ont the **Upload Asset Info** to upload the information to the MySQL database
6. If your level has any Spawnable cameras, make sure you export the LevelSequences as USDs and click on the **Upload Spawnable Info** button

## Database
1. Once your MySQL databse has been populated, you can view the database from the **View Assets** tab
2. If you need to search for any asset, you can you the search bar at the bottom and chose the category from the drop down menu you wish to filter by

## Categorise
1. If you want to categorise your StaticMeshActors in the database, make sure you export them as `.obj` files. You can do this manually through Unreal Engine, selecting the option in the pop-up menu as shown in [Extraction](#extraction), or using the **Extract OBJs** button in the **Categorise** tab
2. Once the `.obj` files are extracted, you can add which categories you want CLIP to fit the `.obj` files into.
3. After adding all the categories, press the **Extract Categories** button so CLIP runs inference. Once it is done, you can view the top 3 predictions
4. If you are happy with the top predictions, click on the **Push Categories** button to add these predictions into the MySQL database.