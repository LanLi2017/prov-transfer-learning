from itertools import permutations
import json
from pathlib import Path
from pprint import pprint
import pandas as pd
from OR_Client_Library.google_refine.refine import refine
import os
from datetime import datetime
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


def save_metadata(json_files, fname='metadata.csv'):
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
    df.to_csv(fname)
    # df.to_csv('workflow-analysis/temp_metadata.csv')
    # print(df)
    return df


def merge_edits(mass_edits_ops):
    # for better edits preparation: ignore operations in-between
    # return a single mass-edit operation with cascading edits 
    res = [mass_edits_ops[0]]
    collapse_edits_list = []
    for op in mass_edits_ops:
        edits = op['edits']
        # merge keys if value is the same 
        collapse_edits_list += edits 
    # merge keys if value is the same 
    from_v_list = []
    to_from_mapping = {}
    merge_edits_list = []
    to_be_deleted_idx = []
    for per_edits in collapse_edits_list:
        to_from_mapping.setdefault(per_edits['to'], []).extend(per_edits['from'])
    
    merge_edits_list = [
        {
            'from': from_,
            'to': to,

    }
    for to, from_ in to_from_mapping.items()]
    print(merge_edits_list)
    
    res[0]['edits'] = merge_edits_list 
    assert len(res) == 1
    return res


def mass_edit_net(df, logging_f, col_name='name'):
    logging_f.write('Merge step 1: output of previous edits overlap with input of current edits \n')
    logging_f.write('Example: {from: a, to:b}, {from:b, to:c} >>> {from:a, to:b}, {from: [a,b], to:c} \n')
    rslt_df = df.loc[(df['Operation Name']=='core/mass-edit') & (df['Column Name']==col_name)]  
    gb = rslt_df.groupby('JSON File Name', group_keys=True)['Step ID'].apply(list)
    df_groups = dict(gb) # json_file_name: [step ids of mass-edit]
    print(f'the df groups are : {df_groups}')
    # df_groups = gb.groups
    jsonf_paths = list(df_groups.keys())
    # stepids_list = [list(v) for v in df_groups.values()]
    mass_edits_integrate = [] # output edits: [{"from":[], "to":[]},{...}...] as the knowledge base
    no_of_changes_list = [] # output list of number of changes 
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
            #Include conditions/facets for mass-edits that are not working globally
            if facets:
                for per_edit in mass_edits_op['edits']:
                    per_edit.update({"facets": facets})
            mass_edits_steps.append(mass_edits_op)
        merge_mass_edits = merge_edits(mass_edits_steps)[0]
        print(merge_mass_edits)
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
                logging_f.write('\nPrevious edits: \n')
                overlap_node_v = overlap_node[0]
                idx = seen_to_values.index(overlap_node_v)
                # mass_edits_sub[idx]['to'] = to_node
                logging_f.write(f'from: {seen_from_values[idx]} >>> \n to: {overlap_node} \n')
                logging_f.write(f'Current edits that use previous outputs: \n')
                logging_f.write(f'Current from: {from_nodes} >>> \n to: {to_node} \n')
                from_nodes += seen_from_values[idx]
                single_edit['from'] = from_nodes
            else:
                pass
            seen_to_values.append(to_node)
            mass_edits_dicts[i] = single_edit
        merge_mass_edits['edits'] = mass_edits_dicts
        mass_edits_dedup, no_of_changes = dedup_mass_edits(merge_mass_edits, logging_f)
        mass_edits_integrate.append(mass_edits_dedup)
        no_of_changes_list.append(no_of_changes)
    
    return mass_edits_integrate, no_of_changes_list  


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


def dedup_mass_edits(mass_edits_dicts, logging_f):
    # if cur_from_nodes is the superclass of prev_from_nodes
    # then deduplicate mass edits by drop prev_from_nodes
    logging_f.write(f'Merge step 2: Remove sub-edits that is contained by super-edits in the list \n')
    logging_f.write('Example: {from:a, to:b}, {from: [a,b], to:c} >>> {from:[a,b], to:c} \n') 
    from_values_dict_mapping = {}
    for index,d in enumerate(mass_edits_dicts['edits']):
        from_values = frozenset(d['from'])
        from_values_dict_mapping[from_values] = index

    to_be_deleted = set()
    for values1, values2 in permutations(from_values_dict_mapping.keys(), 2):
        if values1 <= values2:
            idx = from_values_dict_mapping[values1]
            to_be_deleted.add(idx)
    logging_f.write(f'The number of edits that require to be merged: {len(to_be_deleted)}')
    mass_edits_dicts['edits'] = [
        mass_edits
        for i,mass_edits in enumerate(mass_edits_dicts['edits'])
        if i not in to_be_deleted
    ]
    return mass_edits_dicts, len(to_be_deleted)  


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
    recipe_kb = mass_edit_net(df, col_name='value', logging_f='logging/')
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
    # datetime object containing current date and time
    now = datetime.now()
    # dd/mm/YY H:M:S
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    logging_fname = os.path.join('logging', f'transfer_prov.txt')
    with open(logging_fname, 'a') as logging_f:
        logging_f.write(f"date and time = {dt_string} \n")
        # json_files = ['dish-oh/team3-OpenRefineHistory_Dish.json']
        json_files = ['dish-oh/temp-oh-version1.json']
        # metadata_fn = os.path.join('workflow-analysis','team3_metadata.csv')
        metadata_fn = os.path.join('workflow-analysis','temp_v1_metadata.csv')
        logging_f.write(f'\nStep 1: Load Recipe and Save its Metadata to >>> {metadata_fn} \n')
        if not os.path.exists(metadata_fn):
            df = save_metadata(json_files, metadata_fn)
        else: 
            df = pd.read_csv(metadata_fn, index_col=None)
        logging_f.write('\nStep 2: Summarize Mass-edits >>> Apply Net Effect to Merge Edits \n')
        # merged_fn = os.path.join('prepared_recipe', 'team3_prepared.json')
        merged_fn = os.path.join('prepared_recipe', 'temp_v1_prepared.json')
        logging_f.write(f'Save Merged Recipe to >>> {merged_fn} \n')
        recipe_merged, no_of_changes_diff_list = mass_edit_net(df, logging_f, col_name='value')
        print(recipe_merged)
        # print(f'Number of changes: {no_of_changes_diff_list[0]} \n')
        if not os.path.exists(merged_fn):
            with open(merged_fn, 'wt') as fp:
                json.dump(recipe_merged, fp, indent=6)
        logging_f.write('\nStep 3: Compare number of edits From Original Recipe and Merged Recipe: \n')
        old_no_edits = 0
        with open(json_files[0], 'rb')as json_f:
            original_recipe = json.load(json_f) 
        for dicts in original_recipe:
            if dicts['op']=='core/mass-edit':
                print(f'The number of edits is {len(dicts["edits"])}')
                old_no_edits += len(dicts['edits'])
        logging_f.write(f'Before merging,the total number of edits is {old_no_edits} \n')
        #todo: here we only have one single recipe, so only select the first element from the list
        # no_of_changes_merge = len(recipe_merged[0]['edits'])
        # logging_f.write(f'After merging, the number of edits is {no_of_changes_merge} \n')
        print(no_of_changes_diff_list)
        # assert no_of_changes_diff_list[0] == old_no_edits - no_of_changes_merge
        # logging_f.write('Step 4: Enable Provenance with Mass-edits >>> \n ') 
        # prov_fn = os.path.join('prov_save_recipe', 'team3_prov.json')
        # project_id = 2548411792946
        # logging_f.write(f'Start OpenRefine with Project id >>> {project_id} \n')
        # logging_f.write(f'Save Recipe Embeded with Provenance to >>> {prov_fn} \n')
        # if not os.path.exists(prov_fn):
        #     prov_emb_recipe = prov_enable_recipe(project_id, json_files[0])
        #     with open(prov_fn, 'wt') as fp:
        #         json.dump(prov_emb_recipe, fp, indent=6)


if __name__ == '__main__':
    main()