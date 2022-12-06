# this file is to approve the completeness of provenance 
# provenance^-1 * clean_version dataset => raw_input dataset
# => can not resolve irreversible provenance  
# solution: Invoke operations from OpenRefine python library 
# assert apply(raw_input) == clean_version
import json
from pathlib import Path
from OR_Client_Library.google_refine.refine import refine
import pandas as pd
import OpenRefineOperations as OR

# Goal: evaluate all the replacement 
# return record id that mass-edits applied on 
# logic: apply operations from lib step by step
# before meeting the "core/mass-edit"
metadata_df = pd.read_csv('workflow-analysis/metadata.csv',index_col=False)
mass_edits_df = metadata_df[metadata_df['Operation Name']=="core/mass-edit"]
gb = mass_edits_df.groupby('JSON File Name')['Step ID'].apply(list)
mass_edits_dict = dict(gb) # json_file_name: [step ids of mass-edit]

historyid_list ={
    "team3": 2548411792946,
    "team15": 2336650708031,
    "team140": 2363115749966,
    "team2022":2265712870646
}
for k,v in historyid_list.items():  
    # connect OpenRefine server 
    or_server = refine.RefineProject(refine.RefineServer(), v)
    fp = f"dish-oh/{k}-OpenRefineHistory_Dish.json"
    steps_list = []
    if Path(fp).exists:
        with open(fp, 'rt')as json_f:
            recipe_data = json.load(json_f)
        try:
            steps_list = mass_edits_dict[fp]
            print(steps_list)
            for step in steps_list:
                if step != 0:
                    prev_step = step-1
                    if prev_step not in steps_list:
                        op = recipe_data[prev_step]
                        pass
                else:
                    pass 
        except KeyError:
            print(f'Not find mass edits in {fp}')
            pass 
        