import tkinter as tk
from tkinter import ttk, simpledialog
import yaml
# from shotgrid import upload
from configparser import ConfigParser
from tkinter.filedialog import asksaveasfilename, askopenfilename, askdirectory
import json
import mysql.connector
from pxr import Usd, UsdGeom
import os

# Opening yaml files for all the information
with open('info.yaml', 'r') as file:
    info = yaml.safe_load(file)

# Crutial global variables
unreal = info['PATHS']['unreal']
project = info['PATHS']['project']
config_path = info['PATHS']['config']
GUI = info['PATHS']['GUI']
DB_CONFIG = {
    "host": info["DATABASE"]['host'],
    "user": info["DATABASE"]['user'],
    "password": info["DATABASE"]['password'],
    "database": info["DATABASE"]['database']
}

# Lists for ease of slate conventions and camera details
CAM_CAT = ["Sensor Width", "Sensor Height", "Aspect Ratio", "Focal Length", "Aperture", "Focus Distance", "ISO", "Tilt", "Roll"]
FILM = ["Film ID", "Sequel", "Sequence", "Scene", "Slate", "Take"]
TV = ["Show ID", "Season", "Episode", "Scene", "Shot ID", "Camera", "Lens"]

database = [] # Holds all the database locally 

def command(mode, file=None, extra=0):
    """
    Runs unreal functions through the GUI

    :param mode: which file to run
    :param file: where to save the exports if needed
    :param extra: Boolean for extra extraction
    """
    import subprocess
    if mode == "extract":
        if extra == 1:
            complete = f'{unreal} "{project}" -ExecutePythonScript="{GUI}extract.py -f {file} -o"'
        else:
            complete = f'{unreal} "{project}" -ExecutePythonScript="{GUI}extract.py -f {file}"'
    elif mode == "usd":
        if extra == 1 and obj_var.get() == 0:
           complete = f'{unreal} "{project}" -ExecutePythonScript="{GUI}usd.py -f {file} -l"'
        elif extra == 1 and obj_var.get() == 1:
            complete =  f'{unreal} "{project}" -ExecutePythonScript="{GUI}usd.py -f {file} -l -u"'
        else: 
            complete = f'{unreal} "{project}" -ExecutePythonScript="{GUI}usd.py -f {file}"'
    elif mode == "category":
        complete = f'{unreal} "{project}" -ExecutePythonScript="{GUI}mesh_extract.py -f "{GUI}"'
    try:
        subprocess.run(complete, check=True)
        print(f"\n{mode}: Command ran")
        print(complete)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

def save(mode, extra):
    """
    Helper function to select file for exporting

    :param mode: which file to run
    """
    files = [('All Files', '*.*'),
             ("JSON Files", "*.json"),
             ("USDA Files", "*.usda")]
    file = asksaveasfilename(filetypes=files, defaultextension=files)
    if file is None or len(file) == 0:
        return
    else:
        command(mode, file, extra)

def extract_options(mode):
    """Selects projext extraction options"""
    files = [('All Files', '*.*'),
            ("JSON Files", "*.json")]
    file = askopenfilename(filetypes=files, defaultextension=files)
    if file is None or len(file) == 0:
        return
    with open(file, "r") as file:
        asset_data = json.load(file)
    
    e_options = tk.Toplevel(m)
    e_options.title("Extraction Options")
    e_options.geometry("300x300")

    var1 = tk.IntVar(value=1)
    choice_btn = ttk.Checkbutton(e_options, text="Extract all LevelSequenceActors", variable=var1, onvalue=1, offvalue=0)
    choice_btn.pack(pady=5)

    levels = ttk.Frame(e_options)
    levels.pack()

    check_vars = {}
    for level_sequence in asset_data[-1]:
        asset_path = level_sequence["path"] + "/" + level_sequence["name"]
        int_var = tk.IntVar(value = 0)
        check = ttk.Checkbutton(levels, text = asset_path, variable=int_var, onvalue=1, offvalue=0)
        check.pack(pady=5)
        check_vars[asset_path] = int_var
    
    select_btn = ttk.Button(levels, text="Extract Select", command=lambda:selected_ls(check_vars), style="Custom.TButton").pack()
    pass_btn = ttk.Button(e_options, text = "Extract All", command=lambda:save(mode, var1.get()), style="Custom.TButton").pack()

def selected_ls(checked):
    """
    Runs the USD extraction file on the selected LevelSequences

    :param checked: selected LevelSequence
    """
    output = askdirectory()
    if output is None or len(output) == 0:
        return
    else:
        import subprocess
        selected = [k for k, v in checked.items() if v.get() == 1]
        joined_paths = " ".join(selected)
        cmd = f'{unreal} "{project}" -ExecutePythonScript="{GUI}usd.py -o {joined_paths} -f {output}"' if obj_var.get() == 0 else f'{unreal} "{project}" -ExecutePythonScript="{GUI}usd.py -u -o {joined_paths} -f {output}"'
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")

def projectname(project_label):
    """
    Helper function to set what unreal project is being used and to change the heading

    :param project_label: heading widget 
    """
    global project
    files = [("Unreal Project", "*.uproject"),
             ("All files", "*.*")]
    file = askopenfilename(filetypes=files, defaultextension=files)
    if file is None or len(file) == 0:
        return
    project_label["text"] = file
    info['PATHS']['project'] = file
    project = file
    with open("info.yaml", "w") as f:
        yaml.dump(info, f, default_flow_style=False, sort_keys=False)

def sql_upload():
    """Uploads JSON file of extracted information to database"""
    files = [('All Files', '*.*'),
            ("JSON Files", "*.json")]
    file = askopenfilename(filetypes=files, defaultextension=files)
    if file is None or len(file) == 0:
        return
    with open(file, "r") as file:
        asset_data = json.load(file)

    mydb = mysql.connector.connect(**DB_CONFIG)

    cur = mydb.cursor()
    # Delete all rows
    cur.execute("DELETE FROM camera;")
    cur.execute("DELETE FROM transform;")
    cur.execute("DELETE FROM sequences;")
    cur.execute("DELETE FROM assets;")

    # Reset auto-increment
    cur.execute("ALTER TABLE transform AUTO_INCREMENT = 1;")
    cur.execute("ALTER TABLE assets AUTO_INCREMENT = 1;")
    cur.execute("ALTER TABLE camera AUTO_INCREMENT = 1;")
    cur.execute("ALTER TABLE sequences AUTO_INCREMENT = 1;")

    # Insert JSON data into the database
    for asset in asset_data[:-1]:
        # Insert into assets table
        if asset["class"] == "StaticMeshActor":
            cur.execute(
                "INSERT INTO assets (name, class, mesh) VALUES (%s, %s, %s)",
                (asset["name"], asset["class"], asset["mesh"])
            )
        else:
            cur.execute(
                "INSERT INTO assets (name, class) VALUES (%s, %s)",
                (asset["name"], asset["class"],)
            )
        asset_id = cur.lastrowid  # Get the last inserted asset ID

        # If it's a camera, add additional information
        if asset["class"] == "CineCameraActor":
            camera_info = asset["Camera Settings"]
            cur.execute(
                """
                INSERT INTO camera (asset_id, sensor_width, sensor_height, aspect_ratio, focal_length, aperture, focus_distance, iso, tilt, roll)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (asset_id, camera_info["Sensor Width"], camera_info["Sensor Height"], camera_info["Aspect Ratio"], camera_info["Focal Length"], camera_info["Aperture"], camera_info["Focus Distance"], camera_info["ISO"], camera_info["Tilt"], camera_info["Roll"])
            )
        # If it's a LevelSequence, add bound actors
        if asset["class"] == "LevelSequenceActor":
            bounds = asset["Bound Actors"]
            for object in bounds["names"]:
                cur.execute(
                    """
                    INSERT INTO sequences (asset_id, bound_object)
                    VALUES (%s, %s)
                    """,
                    (asset_id, object)
                )


    # Commit changes and close connection
    mydb.commit()
    cur.close()
    mydb.close()

    print("Data successfully inserted into MySQL!")

def spawn_check():
    """
    Checks if the LevelSequence is part of the project before uploading \n 
    Also passes the MySQL ID of the LevelSequence
    """
    user_input = simpledialog.askstring("Input", "Sequence Name:")
    if user_input:
        for item in database:
            if user_input.lower() in item[1].lower():
                spawn_upload(item[0])
                return
        print("Sequence not in project")
        return
    else:
        print("No Input")

def spawn_upload(id):
    """
    Uploads SpawnableCamera details from selected USD file

    :param id: ID of LevelSequence
    """
    files = [('All Files', '*.*'),
             ("USDA Files", "*.usda")]
    
    # Ask user for USD file 
    file = askopenfilename(filetypes=files, defaultextension=files)
    if file is None or len(file) == 0:
        return
    
    # Load USD stage and time stamp for extraction
    stage = Usd.Stage.Open(file, load=Usd.Stage.LoadAll)
    time0 = Usd.TimeCode.EarliestTime()
    mydb = mysql.connector.connect(**DB_CONFIG)
    cur = mydb.cursor()

    # Find Cameras and get additional details and submit them to MySQL
    for prim in stage.TraverseAll():
        if prim.GetTypeName() =="Camera":
            name = prim.GetParent().GetName()
            print("Camera Detected")
            camera = UsdGeom.Camera(prim)
            focal_length = camera.GetFocalLengthAttr().Get(time0)
            fstop_aperture = camera.GetFStopAttr().Get(time0)
            cur.execute(
                "INSERT INTO assets (name, class) "
                "VALUES (%s, %s)",
                (name,"CineCameraActor")
            )
            asset_id = cur.lastrowid 

            cur.execute(
                """
                INSERT INTO transform (asset_id)
                VALUES (%s)
                """,
                (asset_id,)
            )

            cur.execute(
                """
                INSERT INTO camera (asset_id, focal_length, aperture)
                VALUES (%s, %s, %s)
                """,
                (asset_id, focal_length, fstop_aperture)
            )
            cur.execute(
                """
                INSERT INTO sequences (asset_id, bound_object)
                VALUES (%s, %s)
                """,
                (asset_id, name)
            )
    mydb.commit()
    cur.close()
    mydb.close()

def fetch_data():
    """
    Gets all the information from the MySQL database and saves it to a local variable
    """
    global database
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Fetch data from assets and transform tables
    # cur.execute("""
    #     SELECT assets.id, assets.name, assets.class, assets.category,
    #            transform.location_x, transform.location_y, transform.location_z,
    #            transform.rotation_pitch, transform.rotation_yaw, transform.rotation_roll,
    #            transform.scale_x, transform.scale_y, transform.scale_z
    #     FROM assets
    #     JOIN transform ON assets.id = transform.asset_id
    # """)
    cur.execute("""
    SELECT assets.id, assets.name, assets.class, assets.category, assets.mesh
    FROM assets
    """)
    
    rows = cur.fetchall()
    database = rows
    conn.close()
    return rows

def display_data():
    """
    Displays database data in Databse Tab Treeview
    """
    for row in tree.get_children():
        tree.delete(row)  # Clear previous data
    
    data = fetch_data()
    for row in data:
        tree.insert("", "end", values=row)  # Insert new rows

def show_info(event):
    """
    Shos additional information about cameras and LevelSequences when clicked on in the Treeview
    """
    selected_item = tree.focus() # Get selected row
    if not selected_item:
        return
    item_data = tree.item(selected_item, "values")
    asset_class = item_data[2]  # Get class name
    if asset_class == "CineCameraActor":
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT sensor_width, sensor_height, aspect_ratio, focal_length, aperture, focus_distance, iso, tilt, roll
            FROM camera
            WHERE asset_id = %s
            """,
            (int(item_data[0]),)
        )
        info = cur.fetchall()
        cur.close()
        joined = zip(CAM_CAT, info[0])
        popup = tk.Toplevel(m)
        popup.title("Camera Details")
        popup.geometry("300x500")
        for cat, val in joined:
            tk.Label(popup, text= f"{cat}: {val}").pack(pady=5)
        ttk.Button(popup, text="Close", command=popup.destroy, style="Custom.TButton").pack()

    elif asset_class =="LevelSequenceActor":
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT bound_object
            FROM sequences
            WHERE asset_id = %s
            """,
            (int(item_data[0]),)
        )
        info = cur.fetchall()
        cur.close()
        popup = tk.Toplevel(m)
        popup.title("Bound Objects")
        popup.geometry("300x500")
        for names in info:
            tk.Label(popup, text= f"Object: {names[0]}").pack(pady=5)
        ttk.Button(popup, text="Close", command=popup.destroy, style="Custom.TButton").pack()
    else:
        return

def filter_treeview():
    """Filter the treeview based on user input."""
    query = search_var.get().lower()
    index = search_cat.get()
    for item in tree.get_children():
        tree.delete(item)
    if index == "Label":
        var = 1
    elif index == "Category":
        var = 3
    
    # Clear current items in treeview
    tree.delete(*tree.get_children())  

    # If the search box is empty, reload everything
    if not query:
        for item in database:
            tree.insert("", "end", iid=item[0], values=item)
        return

    for item in database:
        if item[var] != None:
            if query in item[var].lower():  # Check if query is in label
                tree.insert("", "end", iid=item[0], values=item)

def categorise(frame, extract, image):
    """
    Initiate the category prediction

    :param frame: Tk.Frame to get all the labels
    :param extract: Boolean for extracting OBJs
    """
    global preds
    inputs = [widget.get() for widget in frame.winfo_children() if isinstance(widget, ttk.Entry)]
    labels = list(filter(None, inputs))
    if extract == 1:
        command("category")
    if image == 1:
        images()
    preds = predictions(labels) 
    for obj, obj_list in preds.items():
        row = [obj]
        for label, confidence in obj_list.items():
            row.append(label)
        cat_tree.insert("", "end", values=row)

def images():
    """Generates rotating images from OBJs"""
    import open3d as o3d
    import numpy as np
    import cv2

    obj_dir = "objects"
    angles = [0, 45, 90, 135, 180, 225, 270, 315]

    for file in os.listdir(obj_dir):
        obj_name = os.path.join(obj_dir, file)
        export_dir = os.path.join("images", file)
        os.makedirs(export_dir, exist_ok=True)

        # Load 3D mesh
        mesh = o3d.io.read_triangle_mesh(obj_name)
        mesh.compute_vertex_normals()

        # Create a hidden visualizer window
        vis = o3d.visualization.Visualizer()
        vis.create_window(visible=False)  # Prevents window from opening

        vis.add_geometry(mesh)
        vis.update_renderer()

        ctr = vis.get_view_control()

        for angle in angles:
            ctr.rotate(45, 0)
            vis.poll_events()
            vis.update_renderer()

            # Capture image
            img = vis.capture_screen_float_buffer(True)
            img = (np.array(img) * 255).astype(np.uint8)
            
            # Save image
            cv2.imwrite(f"{export_dir}/rendered_{angle}.jpg", img)
        vis.clear_geometries()
        vis.destroy_window()  # Clean up

def predictions(labels):
    """
    Returns all mean predictions from the images

    :params labels: the list of labels to match the images to
    """
    from transformers import CLIPProcessor, CLIPModel
    from PIL import Image
    import torch
    from collections import defaultdict
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    for obj in os.listdir("images"):
        img_dir = os.path.join("images",obj)
        # Store prediction counts
        class_counts = defaultdict(int)
        class_confidences = defaultdict(float)
        for img_file in os.listdir(img_dir):
            img_file=os.path.join(img_dir, img_file)
            image = Image.open(img_file)
            # Preprocess and run inference
            inputs = processor(text=labels, images=image, return_tensors="pt", padding=True)
            outputs = model(**inputs)

            # Convert logits to probabilities
            probs = outputs.logits_per_image.softmax(dim=1).tolist()[0]

            # Get the top 3 predictions
            top3_indices = torch.tensor(probs).argsort(descending=True)[:3]

            for idx in top3_indices:
                label = labels[idx]
                confidence = probs[idx]

                # Accumulate results
                class_counts[label] += 1
                class_confidences[label] += confidence

        # Compute average confidence for each class
        for label in class_confidences:
            class_confidences[label] /= class_counts[label]

        # Sort by frequency (highest first), then by confidence
        sorted_classes = sorted(class_counts.keys(), key=lambda x: (-class_confidences[x], -class_counts[x]))
        obj_list={}
        for rank, label in enumerate(sorted_classes[:3], 1):
            obj_list[label]=class_confidences[label]
        preds[obj[:-4]]=obj_list
    print(preds)
    return(preds)

def push_cat():
    """Add the categories to the MySQL database"""
    global preds
    mydb = mysql.connector.connect(**DB_CONFIG)
    cur = mydb.cursor()
    for obj, obj_list in preds.items():
        cat = list(obj_list.items())[0][0]

        cur.execute(
            """
            UPDATE assets
            SET category = %s
            WHERE mesh = %s
            """ ,
            (cat, obj,)
        )
    mydb.commit()
    cur.close()
    mydb.close()
    display_data()

def change_pred(event):
    selected_item = cat_tree.focus() # Get selected row
    if not selected_item:
        return
    item_data = cat_tree.item(selected_item, "values")
    change = tk.Toplevel(m)
    change.title("Predictions")
    change.geometry("300x500")
    text = tk.Label(change, text = item_data[0], font=header_font, bg="#f0f0f0")
    text.pack(pady=5)
    entries = ttk.Frame(change)
    entries.pack()
    for index in range(len(item_data)-1):
        input = ttk.Entry(entries)
        input.pack(pady=5)
        input.insert(tk.END, item_data[index+1])
    change_btn = ttk.Button(change, text = "Change Predictions", command=lambda:reorder(item_data[0], entries), style="Custom.TButton").pack(pady=5)

def reorder(obj, frame):
    global preds
    inputs = [widget.get() for widget in frame.winfo_children() if isinstance(widget, ttk.Entry)]
    print(preds[obj])
    preds.update({obj: {inputs[0]:1.0, inputs[1]: 0.5, inputs[2]: 0.1}})
    print(preds[obj])

    for row in cat_tree.get_children():
        cat_tree.delete(row)  # Clear previous data

    for obj, obj_list in preds.items():
        row = [obj]
        for label, confidence in obj_list.items():
            row.append(label)
        cat_tree.insert("", "end", values=row)

m = tk.Tk()
m.geometry("900x500")
m.configure(bg="#f0f0f0")
header_font = ("Helvetica", 16, "bold")

# Create notebook
notebook = ttk.Notebook(m)
notebook.pack(expand=True, fill="both")

style = ttk.Style()
style.configure("Custom.TButton", 
                font=("Helvetica", 12), 
                padding=10,
                relief="raised",
                background="#e6e6e6")

#------------------Extract------------------#
extract_tab = ttk.Frame(notebook)
notebook.add(extract_tab, text="Extract Assets")

project_heading = tk.Label(extract_tab, text = "Selected Project", font=header_font, bg="#f0f0f0")
project_heading.pack(pady=(10,20))

project_name=tk.Label(extract_tab, text=project)
project_name.pack(pady=(10,20))

project_btn = ttk.Button(extract_tab, text="Select Project", command=lambda:projectname(project_name), style="Custom.TButton")
project_btn.pack()

extract_btn = ttk.Button(extract_tab, text="Extract Outliner", command=lambda:save("extract", obj_var.get()), style="Custom.TButton")
extract_btn.pack()

obj_var = tk.IntVar(value=1)
obj_check = ttk.Checkbutton(extract_tab, text="Extract OBJs", variable=obj_var, onvalue=1, offvalue=0)
obj_check.pack(pady=5)

usd_btn = ttk.Button(extract_tab, text = "Export Scene as USD", command=lambda:extract_options("usd"), style="Custom.TButton")
usd_btn.pack()

sql_btn = ttk.Button(extract_tab, text = "Upload Asset Info", command=lambda:sql_upload(), style="Custom.TButton")
sql_btn.pack()

spawn_btn = ttk.Button(extract_tab, text = "Upload Spawnable Info", command=lambda:spawn_check(), style="Custom.TButton")
spawn_btn.pack()

#-----------------Database------------------#
viewer_tab = ttk.Frame(notebook)
notebook.add(viewer_tab, text="View Assets")

# Create Treeview widget
# columns = ("ID", "Label", "Class", "Category", "Loc X", "Loc Y", "Loc Z", "Pitch", "Yaw", "Roll", "Scale X", "Scale Y", "Scale Z")
columns = ("ID", "Label", "Class", "Mesh" "Category")
tree = ttk.Treeview(viewer_tab, columns=columns, show="headings")

# Define column headings
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, anchor="center", width=80)

tree.pack(expand=True, fill="both", padx=10, pady=10)
tree.bind("<<TreeviewSelect>>", show_info)

search_cat = ttk.Combobox(
    viewer_tab,
    state="readonly",
    values=["Label", "Category"]
)
search_cat.pack(pady = 5)

# Search Bar
search_var = tk.StringVar()
search_var.trace_add("write", lambda *args: filter_treeview())  # Auto-filter on input

search_entry = tk.Entry(viewer_tab, textvariable=search_var)
search_entry.pack(pady=5)

# Refresh Button
refresh_btn = ttk.Button(viewer_tab, text="Refresh Data", command=lambda:display_data(), style="Custom.TButton")
refresh_btn.pack(pady=5)

display_data()

#-------------------Category-------------------#
cat_tab =ttk.Frame(notebook)
notebook.add(cat_tab, text="Categorise")

popup_heading = tk.Label(cat_tab, text = "Select Categories", font=header_font, bg="#f0f0f0")
popup_heading.pack(pady=(10,20))

left_frame = ttk.Frame(cat_tab)
left_frame.pack(side=tk.LEFT, padx=5, fill=tk.Y)

right_frame = ttk.Frame(cat_tab)
right_frame.pack(side=tk.RIGHT, padx=5, fill=tk.BOTH, expand=True)

option = ttk.Frame(left_frame)
option.pack()
categories = ["cube", "cylinder", "floor", "cone"]
for entry in categories:
    input = ttk.Entry(option)        
    input.pack(pady=5)
    input.insert(tk.END, entry)

table_col = ("Mesh", "Pred 1", "Pred 2", "Pred 3")
cat_tree = ttk.Treeview(right_frame, columns=table_col, show="headings")

for col in table_col:
    cat_tree.heading(col, text=col)
    cat_tree.column(col, anchor="center", width=80)

cat_tree.pack(expand=True, fill="both", padx=10, pady=10)
cat_tree.bind("<<TreeviewSelect>>", change_pred)

btns = ttk.Frame(left_frame)
btns.pack()
add_btn = ttk.Button(btns, text="+", command=lambda:ttk.Entry(option).pack(pady=5), style="Custom.TButton").pack(side=tk.RIGHT, pady=5)
del_btn = ttk.Button(btns, text="-", command=lambda:option.winfo_children()[-1].destroy(), style="Custom.TButton").pack(side=tk.LEFT, pady=5)

var = tk.IntVar(value=1)
check_btn = ttk.Checkbutton(left_frame, text="Extract OBJs", variable=var, onvalue=1, offvalue=0)
check_btn.pack(pady=5)

var_i = tk.IntVar(value=1)
checki_btn = ttk.Checkbutton(left_frame, text="Extract Images", variable=var_i, onvalue=1, offvalue=0)
checki_btn.pack(pady=5)

preds={}

do_btn = ttk.Button(left_frame, text="Extract Category", command=lambda:categorise(option, var.get(), var_i.get()), style="Custom.TButton").pack(side=tk.BOTTOM, pady=5, anchor="s")

submit_btn = ttk.Button(right_frame, text="Push Categories",command=lambda:push_cat(), style="Custom.TButton").pack(side=tk.BOTTOM, pady=5, anchor="s")

m.eval("tk::PlaceWindow . center")
m.mainloop()