import json
from pathlib import Path
from pprint import pprint
import pandas as pd


def op_summarize(json_file):
    json_list = []
    op_list = []
    col_list = []
    steps_list = []
    with open(json_file, 'rt')as f:
        json_data = json.load(f)
        for step_id,data in enumerate(json_data):
            steps_list.append(step_id)
            json_list.append(json_file)
            op_name = data['op']
            op_list.append(op_name)
            if op_name =='core/column-rename':
                col_name = data['oldColumnName']
            elif op_name == 'core/column-addition':
                col_name = data['baseColumnName']
            else:
                try:
                    col_name = data['columnName']
                except KeyError:
                    col_name = 'NULL'
            col_list.append(col_name)
    assert len(col_list) == len(json_list) == len(op_list) == len(steps_list)
    return json_list, op_list, col_list, steps_list


def save_metadata(json_files):
    # json_f = 'dish-oh/team3-OpenRefineHistory_Dish.json'
    df = pd.DataFrame(columns=['JSON File Name', 'Operation Name', 'Column Name', 'Step ID']) 
    jsonf_n_col = []
    op_n_col = []
    col_n_col = []
    steps_col = []
    # freq_col = []
    for json_f in json_files:
        json_list, op_list, col_list, step_id_list = op_summarize(json_f)
        jsonf_n_col += json_list
        op_n_col += op_list
        col_n_col += col_list
        steps_col += step_id_list
    df['JSON File Name'] = jsonf_n_col
    df['Operation Name'] = op_n_col
    df['Column Name'] = col_n_col
    df['Step ID'] = steps_col
    df.index.name = 'Index'
    df.to_csv('workflow-analysis/metadata.csv')
    # print(df)
    return df


def mass_edit_analysis(df):
    # display(dataFrame.loc[(dataFrame['Salary']>=100000) & (dataFrame['Age']< 40) & (dataFrame['JOB'].str.startswith('D')),
    #                 ['Name','JOB']])
    rslt_df = df.loc[(df['Operation Name']=='core/mass-edit') & (df['Column Name']=='name')]
    # print(rslt_df_1.compare(rslt_df))
    gb = rslt_df.groupby('JSON File Name')   
    df_groups = gb.groups
    jsonf_paths = list(df_groups.keys())
    print(jsonf_paths)
    stepids_list = [list(v) for v in df_groups.values()]
    pprint(stepids_list)
    
    sub_dfs = [gb.get_group(x) for x in gb.groups]
    mass_edits_json = []
    for i,sub_df in enumerate(sub_dfs):
        seen_from_values = []
        seen_to_values = []
        json_f = jsonf_paths[i]
        json_data = json.load(json_f)
        stepid_list = stepids_list[i]
        for index, row in sub_df.iterrows():
            step_id = row['Step ID']
            mass_edits = json_data[step_id]['edits'][0]
            from_nodes = mass_edits['from']
            seen_from_values.append(from_nodes)
            to_node = mass_edits['to']
            seen_to_values.append(to_node)
            if to_node in seen_from_values or from_nodes in seen_from_values:
                # overwritten/conflicts within the same JSON file 
                # 1.deal with cases when a->b->c...->n => a->n
                # 2. similarly, when prev edits: a->b; cur edits: a->c => a->c
                # only save a -> n [replace the internal products with the final versions]
                idx = seen_to_values.index(to_node)
                stepid = stepid_list[idx]
                pass
            else:
                pass
        # Deal with overwritten/conflicts across JSON file

            
            
    #TODO NEO4j could be better db [draw the knowledge graph]


def main():
    json_files = [
    # 'dish-oh/team3-OpenRefineHistory_Dish.json']
                #   'dish-oh/team15-OpenRefineHistory_Dish.json',
                  'dish-oh/team140-OpenRefineHistory_Dish.json',
                  'dish-oh/team2020-OpenRefineHistory_Dish.json',
                #   'dish-oh/team2022-OpenRefineHistory_Dish.json'
                ]
    df = save_metadata(json_files)
    mass_edit_analysis(df)


if __name__ == '__main__':
    main()