def merge_edits(exp):
    # for better edits preparation: ignore operations in-between
    # return a single mass-edit operation with cascading edits 
    from_v_list = []
    to_v_list = []
    merge_edits_list = []
    to_be_deleted_idx = []
    for per_edits in exp:
        from_values = per_edits['from']
        to_values = per_edits['to']
        new_dict = {'from': from_values, 'to': to_values}
        from_v_list.append(from_values)
        if to_values in to_v_list:
            # to_idx = to_v_list.index(to_values)
            # print(to_idx)
            to_be_deleted_idices = [i for i, x in enumerate(to_v_list) if x == to_values]
            to_be_deleted_idx += to_be_deleted_idices
            new_key_list = from_values
            for idx in to_be_deleted_idices:
                new_key_list += from_v_list[idx]
            new_key = list(set(new_key_list))
            new_dict = {'from': new_key, 'to': to_values}
        to_v_list.append(to_values)
        merge_edits_list.append(new_dict)
    to_deleted = list(set(to_be_deleted_idx))
    print(to_deleted)
    merge_edits_list = [i for j, i in enumerate(merge_edits_list) if j not in to_deleted]
    
    return merge_edits_list


a = [{'from': ['New York', 'NYC'], 'to': 'New York'},
     {'from': ['New york'], 'to': 'New York'},
     {'from': ['Chicagoo', 'CHI'], 'to': 'Chicago'},
     {'from': ['New York', 'NY city'], 'to': 'New York'},
     {'from': ['Chicago', 'Cicago'], 'to': 'Chicago'}]

res = merge_edits(a)
assert len(res) == 2
print(res)

import json 
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
        # mass_edits_sub = dedup_mass_edits(mass_edits_sub)
        mass_edits_integrate.append(mass_edits_sub)

    return mass_edits_integrate  


def merge_edits(mass_edits_ops):
    # for better edits preparation: ignore operations in-between
    # return a single mass-edit operation with cascading edits 
    res = [mass_edits_ops[0]]
    collapse_edits_list = []
    for op in mass_edits_ops:
        edits = op['edits']
        # merge keys if value is the same 
        collapse_edits_list += edits 
    from_v_list = []
    to_v_list = []
    merge_edits_list = []
    to_be_deleted_idx = []
    for per_edits in collapse_edits_list:
        from_values = per_edits['from']
        to_value = per_edits['to']
        new_dict = {'from': from_values, 'to': to_value}
        from_v_list.append(from_values)
        if to_value in to_v_list:
            to_be_deleted_idices = [i for i,x in enumerate(to_v_list) if x==to_value]
            to_be_deleted_idx += to_be_deleted_idices
            new_key_list = from_values
            for idx in to_be_deleted_idices:
                new_key_list += from_v_list[idx]
            new_key = list(set(new_key_list))
            new_dict = {'from': new_key, 'to': to_value}
        to_v_list.append(to_value)
        merge_edits_list.append(new_dict)
    merge_edits_list = [i for j, i in enumerate(merge_edits_list) if j not in to_be_deleted_idx]
    
    res[0]['edits'] = merge_edits_list 
    assert len(res) == 1
    return res