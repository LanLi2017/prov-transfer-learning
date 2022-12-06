import json
from pathlib import Path
from pprint import pprint
import pandas as pd


def op_summarize(json_file):
    json_list = []
    op_list = []
    col_list = []
    steps_list = []
    print(json_file)
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
    # df.to_csv('workflow-analysis/test_metadata.csv')
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
    stepids_list = [list(v) for v in df_groups.values()]
    
    sub_dfs = [gb.get_group(x) for x in gb.groups]
    mass_edits_integrate = [] # output edits: [{"from":[], "to":[]},{...}...] as the knowledge base
    for i,sub_df in enumerate(sub_dfs):
        seen_from_values = []
        seen_to_values = []
        json_f = jsonf_paths[i]
        mass_edits_sub = []
        with open(json_f, 'rt')as file:
            json_data = json.load(file)
            for index, row in sub_df.iterrows():
                step_id = row['Step ID']
                mass_edits = json_data[step_id]['edits']
                for single_edit in mass_edits:
                    from_nodes = single_edit['from']
                    seen_from_values.append(from_nodes)
                    overlap_node = list(set(from_nodes) & set(seen_to_values))
                    to_node = single_edit['to']
                    if overlap_node:
                        print(overlap_node)
                        print(seen_to_values)
                        # overwritten/conflicts within the same JSON file 
                        # deal with cases when a->b->c...->n => a->n
                        # only save a -> n [replace the internal products with the final versions]
                        assert len(overlap_node) == 1
                        overlap_node_v = overlap_node[0]
                        idx = seen_to_values.index(overlap_node_v)
                        mass_edits_sub[idx]['to'] = to_node
                        from_nodes.remove(overlap_node_v)
                        mass_edits_sub.append(
                            {
                                "from":from_nodes,
                                "to": to_node
                            }
                        )

                    else:
                        mass_edits_sub.append(
                            {
                                "from":from_nodes,
                                "to": to_node
                            }
                        )
                    seen_to_values.append(to_node)
        mass_edits_sub = dedup_mass_edits(mass_edits_sub)
        mass_edits_integrate.append(mass_edits_sub)

    return mass_edits_integrate    


def dedup_mass_edits(mass_edits):
    #TODO: "deduplicate"/integrate mass-edits if they share the same "to_values"
    res_dicts = {}
    for edits_value in mass_edits:
        from_v = edits_value['from']
        to = edits_value['to']
        res_dicts.setdefault(to, []).extend(from_v)
    merge_data = [
        {
        'from': from_,
        'to': to,
    }
    for to, from_ in res_dicts.items()
    ]
    return merge_data


def clean_mass_edits(mass_edits):
    #TODO: resolve the conflicts of the mass edits across recipes
    # Deal with overwritten/conflicts across JSON file
    pass


def viz_kb():
    #TODO NEO4j could be better db [draw the knowledge graph]

    pass
    

def main():
    # json_files = ['dish-oh/test-dish.json']
    json_files = [
                  'dish-oh/team3-OpenRefineHistory_Dish.json',
                  'dish-oh/team15-OpenRefineHistory_Dish.json',
                  'dish-oh/team140-OpenRefineHistory_Dish.json',
                  #   'dish-oh/team2020-OpenRefineHistory_Dish.json',
                  'dish-oh/team2022-OpenRefineHistory_Dish.json'
    ]
    df = save_metadata(json_files)
    # recipe_kb = mass_edit_analysis(df)
    # pprint(recipe_kb)


if __name__ == '__main__':
    main()