import json
from pathlib import Path
from pprint import pprint
import pandas as pd
from OR_Client_Library.google_refine.refine import refine
# recipes without merging: dish-oh/*.json
# recipe with merging: prepared_recipe/*.json

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


def viz_kb():
    #TODO NEO4j could be better db [draw the knowledge graph]

    pass


def oh_map_history(op):
    '''
        operation history from data.txt
        => include a complete record (single-edit; star/flag rows)
    '''
    oh_list = op.get_operations()

    '''
        history list: 
        history id; time stamp; description [retrospective provenance]
    '''
    histories = op.list_history()  # history id/ time/ desc
    past_histories = histories['past']

    assert len(oh_list) == len(past_histories)
    map_result = [
        {**oh, **history}
        for oh, history in zip(oh_list, past_histories)
    ]
    # description will be overwrite with retrospective info from history list.
    return oh_list, past_histories, map_result


def load_ds_from_or(project_id):
    # load dataset from openrefine client library 
    # return: list of dictionary [{column-name: cell-value, ...},...]
    or_server = refine.RefineProject(refine.RefineServer(), project_id) 
    res = or_server.export_rows()
    ds_dict = list(res)
    return ds_dict


def diff_ds(prev_ds, cur_ds, edits):
    '''premise: mass-edits will not change the data structure; so prev_ds and cur_ds share the same shape'''
    # compare two list dictionaries 
    # return edits with signature (record id, column name)
    for row_id, prev_row_value in enumerate(prev_ds):
        cur_row_value = cur_ds[row_id]
        for col_name, prev_cell_value in prev_row_value.items():
            cur_cell_value = cur_row_value[col_name]
            if cur_cell_value == prev_cell_value:
                pass
            else:
                for edit in edits:
                    if prev_cell_value in edit['from'] and cur_cell_value==edit['to']:
                        # locate the place to add key-value provenance pair
                        edit.setdefault('changed-cells', []).append((row_id, col_name))
                    else:
                        edit = edit
                        # if 'changed-cells' in edits:
                        #     edit['changed-cells'].append((row_id, col_name))
                        # else:
                        #     edit.update({'changed-cells': [(row_id, col_name)]})
    return edits


def prov_enable_recipe(project_id, recipe, col_name='name'): 
    # recipe with record-id preservation: prov_save_recipe/*.json
    # return: add a key-value pair under "edits": changed-cells:[((record id, column name, function))]
    or_server = refine.RefineProject(refine.RefineServer(), project_id) # load openrefine project 
    or_server.undo_redo_project(0) # initialize project status 
    response_res = or_server.apply_operations(recipe)
    print(response_res)
    oh_list, past_histories, map_result = oh_map_history(or_server)
    for op_idx,op_dict in enumerate(map_result):
        if op_dict['op'] == 'core/mass-edit' and op_dict['columnName']==col_name:
            prev_idx = op_idx-1
            if prev_idx <0:
                assert prev_idx == -1
                # in this case, previous status is the clean dataset 
                prev_history_id = 0  
            else:
                prev_history_id = map_result[prev_idx]['id']
            cur_history_id = op_dict['id']
            or_server.undo_redo_project(prev_history_id)
            prev_ds = load_ds_from_or(project_id)
            or_server.undo_redo_project(cur_history_id)
            cur_ds = load_ds_from_or(project_id)
            edits_op = op_dict['edits']
            assert type(edits_op) is list
            op_dict['edits'] = diff_ds(prev_ds, cur_ds, edits_op)
    pprint(map_result)
    return map_result


def save_merged_recipe():
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


def save_prov_recipe():
    raw_data = 'project-files/temp/temp_raw.csv'
    recipe = 'dish-oh/temp-oh.json'
    project_id = 1729702572071
    # for row in res:
    #     print(row) 
    prov_emb_recipe = prov_enable_recipe(project_id, recipe, col_name='value')
    with open('prov_save_recipe/temp_prov_embed.json', 'wt') as fp:
        json.dump(prov_emb_recipe, fp, indent=6)

def main():
    save_prov_recipe()

if __name__ == '__main__':
    main()