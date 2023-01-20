import copy
from itertools import permutations
import json
from pathlib import Path
from pprint import pprint
import random
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


def Deduplication(mass_edits_ops, logging_f):
    # De-duplication: Edits share the same target value of "to"
    # Merge keys 
    res = [mass_edits_ops[0]]
    collapse_edits_list = []
    for op in mass_edits_ops:
        edits = op['edits']
        collapse_edits_list += edits  
    to_from_mapping = {}
    merge_edits_list = []
    for per_edits in collapse_edits_list:
        item_to = per_edits['to']
        if item_to in to_from_mapping:
            logging_f.write(f'{to_from_mapping[item_to]}:{item_to} and {per_edits["from"]}:{item_to} are merged \n')
        # merge keys if value is the same
        to_from_mapping.setdefault(per_edits['to'], []).extend(per_edits['from'])
    
    merge_edits_list = [
        {
            'from': from_,
            'to': to,

    }
    for to, from_ in to_from_mapping.items()]
    
    res[0]['edits'] = merge_edits_list 
    assert len(res) == 1
    return res


def mass_edit_seq(df, logging_f, col_name='name'):
    # Sequential Composition
    rslt_df = df.loc[(df['Operation Name']=='core/mass-edit') & (df['Column Name']==col_name)]  
    gb = rslt_df.groupby('JSON File Name', group_keys=True)['Step ID'].apply(list)
    df_groups = dict(gb) # json_file_name: [step ids of mass-edit]
    # print(f'the df groups are : {df_groups}')
    mass_edits_prepared = [] # output edits: [{"from":[], "to":[]},{...}...] as the knowledge base
    for k,v in df_groups.items():
        seen_from_values = []
        seen_to_values = []
        json_f = k
        steps_list = v
        # mass_edits_sub = []
        logging_f.write(f'Load Original Recipe >>>>> {json_f} \n')
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
        logging_f.write(f'Deduplication process >>>>>>>\n')
        merge_mass_edits = Deduplication(mass_edits_steps, logging_f)[0] # composition func1: deduplication 
        # print(merge_mass_edits)
        mass_edits_dicts = merge_mass_edits['edits']
        # ensure all the value replacement are working on "All"
        logging_f.write('Refinement Process >>>>>>> \n')
        for i,single_edit in enumerate(mass_edits_dicts):
            # deal with value replacement within the single mass-edit operation 
            from_nodes = single_edit['from']
            seen_from_values.append(from_nodes)
            # composition func2: refinement 
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
                logging_f.write(f'from: {seen_from_values[idx]} >>> to: {overlap_node} \n')
                logging_f.write(f'Current edits that use previous outputs: \n')
                logging_f.write(f'Current from: {from_nodes} >>> to: {to_node} \n')
                from_nodes += seen_from_values[idx]
                single_edit['from'] = from_nodes
            else:
                pass
            seen_to_values.append(to_node)
            mass_edits_dicts[i] = single_edit
        merge_mass_edits['edits'] = mass_edits_dicts
        mass_edits_refine = refine_mass_edits(merge_mass_edits, logging_f)
        merged_fn = os.path.join('prepared_recipe', f'{json_f.split("/")[-1].split(".")[0]}_prepared.json')
        logging_f.write(f'Prepare Recipe By Sequantial Composition and Save it To >>> {merged_fn} \n')
        with open(merged_fn, 'wt') as fp:
            json.dump(mass_edits_refine, fp, indent=6)
        mass_edits_prepared.append(merged_fn)
        # mass_edits_integrate.append(mass_edits_dedup)
        # no_of_changes_list.append(no_of_changes)
    
    return mass_edits_prepared


def refine_mass_edits(mass_edits_dicts, logging_f):
    # if cur_from_nodes is the superclass of prev_from_nodes
    # then deduplicate mass edits by drop prev_from_nodes
    # logging_f.write(f'Merge step 2: Remove sub-edits that is contained by super-edits in the list \n')
    # logging_f.write('Example: {from:a, to:b}, {from: [a,b], to:c} >>> {from:[a,b], to:c} \n') 
    from_values_dict_mapping = {}
    for index,d in enumerate(mass_edits_dicts['edits']):
        from_values = frozenset(d['from'])
        from_values_dict_mapping[from_values] = index

    to_be_deleted = set()
    for values1, values2 in permutations(from_values_dict_mapping.keys(), 2):
        if values1 <= values2:
            idx1 = from_values_dict_mapping[values1]
            to_be_deleted.add(idx1)
            logging_f.write(f'{values1} is refined as {values2}\n')
    logging_f.write(f'The number of edits that require to be merged: {len(to_be_deleted)} \n')
    mass_edits_dicts['edits'] = [
        mass_edits
        for i,mass_edits in enumerate(mass_edits_dicts['edits'])
        if i not in to_be_deleted
    ]
    return mass_edits_dicts  


def try_to_merge(old_edits, new_edit, logging_f):
    new_input = new_edit['from']
    from_to_merge = [*new_input, new_edit['to']]
    for old_edit in old_edits:
        input_v = old_edit['from']
        if set(from_to_merge) <= set(input_v):
            logging_f.write(f'{new_edit} is subsumed under {old_edit} \n ')
            return (True, old_edit)
    return (False, new_edit)


def overwrite(base_edits, new_edits, logging_f):
    # E1, E2: E2 is subclass of E1.input => keep superclass E1 only 
    # @params: [{E1}, {E2}, ...{En}]
    logging_f.write("Overwrite Process >>>>>>> \n")
    base_res = [*base_edits]
    # new_edits_ref = copy.copy(new_edits)
    for new_edit in new_edits:
        flag, res = try_to_merge(base_edits, new_edit, logging_f)
        if not flag:
            base_res.append(res)
    return base_res


def css_recipes(json_fp):
    # return casecading edits: base-graph, new-edits
    mass_edits_ds = {}
    base_recipe = json_fp[0]
    new_recipe = json_fp[1]
    with open(base_recipe, 'r')as json_ds:
        mass_edits_ds = json.load(json_ds) 
    with open(new_recipe, 'r')as new_json_ds:
        new_mass_edits_ds = json.load(new_json_ds)    
    return mass_edits_ds, new_mass_edits_ds


def rewrite_edits(edits):
    # split the list of from values [many to one] => [one to one]*n
    res = {}
    for edit in edits:
        for e_from in edit['from']:
            element = {e_from:edit['to']}
            res.update(element)
    return res


def formatted_style(graph):
    # merge the source values if share the same target value: 
    # [one-to-one]*n => many-to-one
    cache = {}
    for k, v in graph.items():
        cache.setdefault(v, []).append(k)
    return [
        {
            'from': us,
            'to': v,
        }
        for v, us in cache.items()
    ]

# >>>>> recipe composition: [deterministic seq machine, random parallel machine]
def deter_seq_machine(result, cur_edits,logging_f):
    print(result)
    print(cur_edits)
    """if conclicts occur, later appended edge will overwrite prev version"""
    # @params result: edit functions from initial recipe that work as base
    # @params cur_edits: update/overwrite edges from current edits
    # return: a merged mass-edits dictionary  
    logging_f.write("Deterministic Sequential Machine Running: >>>>> \n")
    for from_v, to_v in cur_edits.items():
        if from_v not in result:
            result[from_v] = to_v
        elif result[from_v] != from_v:  # u is a 'from'
            if (to_v not in result) or (result[from_v] != result[to_v]):
                print(f'Conflict {from_v}->{to_v}, {from_v}->{result[from_v]} \n')
                logging_f.write(f'Conflict {from_v}->{to_v}, {from_v}->{result[from_v]} \n')
                logging_f.write(f'Resolve Conflict by Overwriting with new edge: {from_v}->{to_v} \n')
                result[from_v] = to_v
                if to_v not in result:
                    result[to_v] = to_v
                    logging_f.write(f'Add one edge {to_v}->{to_v} to base graph \n')
                else:
                    # transitive rule 
                    result[from_v] = result[result[to_v]] 
                    logging_f.write(f'Transitive rule is applied: {from_v}->{to_v} >>> {from_v}->{result[result[to_v]]} \n')
        else:  # u is a 'to'
            # add v(u->v) to base graph 
            if to_v not in result:
                result[to_v] = to_v
                logging_f.write(f'Add edge based on to-value from new graph: {to_v}->{to_v} \n')
            if result[result[to_v]] == from_v:
                print(f'Loop Exist: {from_v}->{to_v}; {to_v}->{from_v} \n')
                logging_f.write(f'Loop Exist: {from_v}->{to_v}; {to_v}->{from_v} \n')
                logging_f.write(f'Resolve loop by overwriting with new edge: {from_v}->{to_v} \n')

                del result[to_v]
                # result.update({from_v: to_v})
                logging_f.write(f'Delete Loop Edit from base graph: {to_v}->{from_v} \n')
                if to_v not in result:
                    logging_f.write(f'Add edge based on to-value from new graph: {to_v}->{to_v} \n')
                    result[to_v] = to_v
                # transitive rule
                logging_f.write('Processing Transitive Rule >>>>>> \n')
                result = {
                    # for all kk pointing to u,
                    # merge to the tree of v.
                    kk: to_v if vv == from_v else vv
                    for kk, vv in result.items()
                }
            else:
                result = {
                    # for all kk pointing to u,
                    # merge to the tree of v.
                    kk: result[to_v] if vv == from_v else vv
                    for kk, vv in result.items()
                }
    result = {
    k: v
    for k, v in result.items()
    if k != v
    }

    final_res = formatted_style(result)
    return final_res


def parallel_machine(result, rev_new_edits, logging_f, mode='user'):
    # @params result: base edits that work as base graph 
    # @params rev_new_edits: update edges from new edits
    # @params logging_f: logging file
    # @params mode: [user, random, ignore]
    # return: a merged mass-edits dictionary  
    logging_f.write(f'Random Parallel Machine Running: >>>>> Mode->{mode} \n')
    for from_v, to_v in rev_new_edits.items():
        if from_v not in result:
            result[from_v] = to_v
        elif result[from_v] != from_v:  # u is a 'from'
            if (to_v not in result) or (result[from_v] != result[to_v]):
                logging_f.write(f'Conflict {from_v}->{to_v}, {from_v}->{result[from_v]} \n')
                if mode == 'random':
                    sample_set = (0,1) # 0: old; 1:new
                    edge_item = random.choice(sample_set)
                    if edge_item == 0:
                        logging_f.write(f'Choose old {from_v}->{result[from_v]} from the base graph \n')
                        pass
                    else:
                        logging_f.write(f'Choose new edge: {from_v}->{to_v} \n')
                        result[from_v] = to_v
                        if to_v not in result:
                            result[to_v] = to_v
                            logging_f.write(f'Add one edge {to_v}->{to_v} to base graph \n')
                        else:
                            # transitive rule 
                            result[from_v] = result[result[to_v]] 
                            logging_f.write(f'Transitive rule is applied: {from_v}->{to_v} >>> {from_v}->{result[result[to_v]]} \n')
                elif mode == 'ignore':
                    pass
                elif mode == 'user':
                    conflict_edit = [{from_v:to_v}, {from_v: result[from_v]}]
                    choose_idx = int(input(f"Choose index of the edit from the conflict edges (0/1): {conflict_edit}"))
                    if choose_idx==0:
                        logging_f.write(f'Choose {from_v}->{to_v} \n')
                        result[from_v] = to_v
                        if to_v not in result:
                            result[to_v] = to_v
                            logging_f.write(f'Add one edge {to_v}->{to_v} to base graph \n')
                        else:
                            # transitive rule 
                            result[from_v] = result[result[to_v]] 
                            logging_f.write(f'Transitive rule is applied: {from_v}->{to_v} >>> {from_v}->{result[result[to_v]]} \n')
                    else:
                        logging_f.write(f'Choose old {from_v}->{result[from_v]} from the base graph \n')
                        pass
        else:  # u is a 'to'
            # add v(u->v) to base graph 
            if to_v not in result:
                result[to_v] = to_v
                logging_f.write(f'Add edge based on to-value from new graph: {to_v}->{to_v} \n')
            if result[result[to_v]] == from_v:
                logging_f.write(f'Loop Exist: {from_v}->{to_v}; {to_v}->{from_v} \n')
                if mode == 'random':
                    print(f'mode is {mode}')
                    sample_set = (0,1) # 0: old; 1:new
                    edge_item = random.choice(sample_set)
                    if edge_item==0:
                        logging_f.write(f'Choose Edit from base graph: {to_v}->{from_v} \n')
                    else:
                        logging_f.write(f'Choose Edit from new graph: {from_v}->{to_v} \n')
                        del result[to_v]
                        logging_f.write(f'Delete Loop Edit from base graph: {to_v}->{from_v} \n')
                        if to_v not in result:
                            logging_f.write(f'Add edge based on to-value from new graph: {to_v}->{to_v} \n')
                            result[to_v] = to_v
                        # transitive rule
                        logging_f.write('Processing Transitive Rule >>>>>> \n')
                        result = {
                            # for all kk pointing to u,
                            # merge to the tree of v.
                            kk: result[to_v] if vv == from_v else vv
                            for kk, vv in result.items()
                        }
                elif mode == 'ignore':
                    pass
                elif mode == 'user':
                    conflict_edit = [{from_v:to_v}, {to_v: from_v}]
                    choose_idx = int(input(f"Choose index of the edit from the conflict edges (0/1): {conflict_edit}"))
                    if choose_idx==0:
                        logging_f.write(f'Choose Edit from new graph: {from_v}->{to_v} \n')
                        del result[to_v]
                        logging_f.write(f'Delete Loop Edit from base graph: {to_v}->{from_v} \n')
                        if to_v not in result:
                            logging_f.write(f'Add edge based on to-value from new graph: {to_v}->{to_v} \n')
                            result[to_v] = to_v
                        # transitive rule
                        logging_f.write('Processing Transitive Rule >>>>>> \n')
                        result = {
                            # for all kk pointing to u,
                            # merge to the tree of v.
                            kk: result[to_v] if vv == from_v else vv
                            for kk, vv in result.items()
                        }
                    else:
                        logging_f.write(f'Keep Edit from base graph: {to_v}->{from_v} \n')
                        pass
            else:
                result = {
                    # for all kk pointing to u,
                    # merge to the tree of v.
                    kk: result[to_v] if vv == from_v else vv
                    for kk, vv in result.items()
                }
    result = {
    k: v
    for k, v in result.items()
    if k != v
    }

    final_res = formatted_style(result)
    return final_res


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
    # print(response_res)
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
    # pprint(map_result)
    return map_result


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
    # json_files = ['dish-oh/temp-oh-version1.json', 'dish-oh/temp_p1-oh.json']
    json_files = ['dish-oh/temp_p1-oh.json']
    json_integrate = ['recipe_integrated/seq.json', 
                      'recipe_integrated/par_user.json', 
                      'recipe_integrated/par_random.json', 
                      'recipe_integrated/par_ignore.json']
    metadata_fname = 'temp_metadata.csv'
    scheduler = [0,1]
    # datetime object containing current date and time
    now = datetime.now()
    # dd/mm/YY H:M:S
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    logging_fname = os.path.join('logging', f'transfer_prov.txt')
    with open(logging_fname, 'a') as logging_f:
        logging_f.write(f"date and time = {dt_string} \n")
        metadata_fn = os.path.join('workflow-analysis',metadata_fname)
        logging_f.write(f'\nStep 1: Load Recipes and Save Metadata to >>>>> {metadata_fn} \n')
        # if not os.path.exists(metadata_fn):
        df = save_metadata(json_files, metadata_fn)
        # else: 
        #     df = pd.read_csv(metadata_fn, index_col=None)
        logging_f.write('\nStep 2: Sequential Composition >>>>> \n')
        recipes_prepared = mass_edit_seq(df, logging_f, col_name='value')
        assert len(recipes_prepared) == len(json_files)
        # logging_f.write('\nStep 3: Recipe Merge Scheduler >>>>> \n')
        logging_f.write("\nStep 3 Recipe Integration Running: >>>>>> \n")
        # logging_f.write('\nStep 4: Parallel Composition >>>>> \n')
        json_prepared_files = ['prepared_recipe/temp_v1_prepared.json', 'prepared_recipe/temp_v2_prepared.json']
        base_recipe, new_recipe = css_recipes(json_prepared_files)
        base_seq = base_recipe.copy()
        base_par = base_recipe.copy()

        rev_base_edits = rewrite_edits(base_recipe[0]['edits'])
        rev_new_edits = rewrite_edits(new_recipe[0]['edits'])
        base_graph = rev_base_edits.copy()
        base_graph.update({
            v: v
            for v in base_graph.values()
        })
        base_seq_g = base_graph.copy()
        base_par_g = base_graph.copy()
        # integrate edit functions from recipes
        # integration method 1: sequential merge
        recipe_seq_edits = deter_seq_machine(base_seq_g, rev_new_edits, logging_f)
        base_seq[0]['edits'] = recipe_seq_edits
        with open(json_integrate[0], 'wt') as fp:
            logging_f.write(f'Save Integrated Recipe by Determinisic Sequential Machine to >>>>> {json_integrate[0]} \n')
            json.dump(base_seq, fp, indent=6)
        
        # modes = ['user', 'random', 'ignore']
        modes = ['user']
        for idx,mode in enumerate(modes):
            base_par_edits = parallel_machine(base_par_g, rev_new_edits, logging_f, mode)
            base_par[0]['edits'] = base_par_edits
            with open(json_integrate[1], 'wt') as fp:
                logging_f.write(f'Save Integrated Recipe by Random Parallel Machine [{mode} Mode] to >>>>> {json_integrate[1]} \n')
                json.dump(base_par, fp, indent=6) 
        # with open(json_integrate[2], 'wt') as fp:
        #     logging_f.write(f'Save Integrated Recipe by Random Parallel Machine [Random mode] to >>>>> {json_integrate[2]} \n')
        #     json.dump(base_par_r, fp, indent=6) 
        # with open(json_integrate[3], 'wt') as fp:
        #     logging_f.write(f'Save Integrated Recipe by Random Parallel Machine [Ignore mode] to >>>>> {json_integrate[3]} \n')
        #     json.dump(base_par_i, fp, indent=6)
if __name__ == '__main__':
    main()