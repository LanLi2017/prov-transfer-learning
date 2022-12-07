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
    # df.to_csv('workflow-analysis/metadata.csv')
    df.to_csv('workflow-analysis/temp_metadata.csv')
    # print(df)
    return df


def merge_edits(mass_edits_ops):
    # for better edits preparation: ignore operations in-between
    # return a single mass-edit operation with cascading edits 
    res = [mass_edits_ops[0]]
    merge_edits_list = []
    for op in mass_edits_ops:
        edits = op['edits']
        merge_edits_list += edits 
    res[0]['edits'] = merge_edits_list 
    assert len(res) == 1
    return res


def mass_edit_net(df, col_name='name'):
    rslt_df = df.loc[(df['Operation Name']=='core/mass-edit') & (df['Column Name']==col_name)]  
    gb = rslt_df.groupby('JSON File Name')['Step ID'].apply(list)
    df_groups = dict(gb) # json_file_name: [step ids of mass-edit]
    # df_groups = gb.groups
    jsonf_paths = list(df_groups.keys())
    # stepids_list = [list(v) for v in df_groups.values()]
    mass_edits_integrate = [] # output edits: [{"from":[], "to":[]},{...}...] as the knowledge base
    for k,v in df_groups.items():
        seen_from_values = []
        seen_to_values = []
        json_f = k
        steps_list = v
        # mass_edits_sub = []
        with open(json_f, 'rt')as file:
            json_data = json.load(file)
        mass_edits_steps = []
        for step_id in steps_list:
            mass_edits_op = json_data[step_id]
            facets = json_data[step_id]['engineConfig']['facets']
            if not facets:
                mass_edits_steps.append(mass_edits_op)
        merge_mass_edits = merge_edits(mass_edits_steps)[0]
        mass_edits_dicts = merge_mass_edits['edits']
        # ensure all the value replacement are working on "All"
        for i,single_edit in enumerate(mass_edits_dicts):
            # deal with value replacement within the single mass-edit operation 
            from_nodes = single_edit['from']
            seen_from_values.append(from_nodes)
            overlap_node = list(set(from_nodes) & set(seen_to_values))
            to_node = single_edit['to']
            if overlap_node:
                # net effect: a->b->c...->n => a,b,c,...->n
                # [append the internal products with the final versions]
                # provenance tracking weakness: how to distinguish old values and new values
                overlap_node_v = overlap_node[0]
                idx = seen_to_values.index(overlap_node_v)
                # mass_edits_sub[idx]['to'] = to_node
                from_nodes += seen_from_values[idx]
                single_edit['from'] = from_nodes
            else:
                pass
            seen_to_values.append(to_node)
            mass_edits_dicts[i] = single_edit
        merge_mass_edits['edits'] = mass_edits_dicts
        mass_edits_dedup = dedup_mass_edits(merge_mass_edits)
        mass_edits_integrate.append(mass_edits_dedup)
    
    return mass_edits_integrate    


# def dedup_mass_edits(mass_edits_dicts):
#     res_dicts = {}
#     for edits_value in mass_edits_dicts['edits']:
#         from_v = edits_value['from']
#         to = edits_value['to']
#         res_dicts.setdefault(to, []).extend(from_v)
#     merge_data = [
#         {
#         'from': from_,
#         'to': to,
#     }
#     for to, from_ in res_dicts.items()
#     ]
#     return merge_data


def dedup_mass_edits(mass_edits_dicts):
    # if cur_from_nodes is the superclass of prev_from_nodes
    # then deduplicate mass edits by drop prev_from_nodes 
    seen_from_nodes = []
    for edits_value in mass_edits_dicts['edits']:
        from_v = edits_value['from']
        for seen_values in seen_from_nodes:
            diff = list(set(from_v) & set(seen_values))
            print(f'from_v is {from_v}; seen_values is {seen_values}; overlap is {diff}')
            if not diff:
                pass
            else:
                overlap_index = seen_from_nodes.index(diff)
                del mass_edits_dicts['edits'][overlap_index]
        seen_from_nodes.append(from_v)
    return mass_edits_dicts
    


def mass_edit_offset(df, col_name='name'):
    # display(dataFrame.loc[(dataFrame['Salary']>=100000) & (dataFrame['Age']< 40) & (dataFrame['JOB'].str.startswith('D')),
    #                 ['Name','JOB']])
    rslt_df = df.loc[(df['Operation Name']=='core/mass-edit') & (df['Column Name']==col_name)]
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
        'dish-oh/temp-oh.json'
                #   'dish-oh/team3-OpenRefineHistory_Dish.json',
                #   'dish-oh/team15-OpenRefineHistory_Dish.json',
                #   'dish-oh/team140-OpenRefineHistory_Dish.json',
                  #   'dish-oh/team2020-OpenRefineHistory_Dish.json',
                #   'dish-oh/team2022-OpenRefineHistory_Dish.json'
    ]
    df = save_metadata(json_files)
    # recipe_kb = mass_edit_analysis(df, col_name='value')
    recipe_kb = mass_edit_net(df, col_name='value')
    with open('prepared_recipe/temp_prepared.json', 'wt') as fp:
        json.dump(recipe_kb, fp, indent=6)


if __name__ == '__main__':
    main()