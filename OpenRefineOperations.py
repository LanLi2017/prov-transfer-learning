import json
import os
from pprint import pprint

from OR_Client_Library.google_refine.refine import refine


def list_objects():
    # list projects
    return refine.Refine(refine.RefineServer()).list_projects()


def create_project(project_path,project_name):
    # create a new project
    projectID=refine.Refine(refine.RefineServer()).new_project(project_path,project_name,project_format='.csv')[1]
    return projectID


def open_project(project_id):
    # open a project with project id
    return refine.Refine(refine.RefineServer()).open_project(project_id)


def get_project_name(project_id):
    # get the project name
    return refine.Refine(refine.RefineServer()).get_project_name(project_id)

def project_name(project_id):
    # functions in RefineProject:
    # project_name
    return refine.RefineProject(refine.RefineServer(),project_id).project_name()

'''
Niko
'''
def list_history(project_id):
    return refine.RefineProject(refine.RefineServer(),project_id).list_history()

def undo_redo(project_id,lastDone_id):
    return refine.RefineProject(refine.RefineServer(),project_id).undo_redo_project(lastDone_id)

"""
Niko
"""

def project_url(project_id):
    # project_url
    return refine.RefineProject(refine.RefineServer(),project_id).project_url()


def do_raw(project_id,command,data):
    # do_raw :  issue a command to the server & return a response object
    return refine.RefineProject(refine.RefineServer(),project_id).do_raw(command, data)


def do_json(project_id,command,data):
    # do_json: issue a command to the server, parse & return encoded OR_JSON.
    return refine.RefineProject(refine.RefineServer(),project_id).do_json(command,data)


def get_models(project_id):
    # get_models: fill out column metadata.
    # Column structure is a list of columns in their order.
    # The cellIndex is an index for that column's data into the list returned from get_rows().
    return refine.RefineProject(refine.RefineServer(),project_id).get_models()


def get_cell_value(project_id,columnIndex):
    # split break.....
    # nestedlist: [{u'cells': [{u'v': u'10136'},....{}]},{u 'cells': [...]}]
    # The cellIndex is an index for that column's data into the list returned from get_rows().
    # 'from': cell_value, 'to': new_cell_value
    nested_list=refine.RefineProject(refine.RefineServer(),project_id).get_cell_value()
    AimCellValue=[]
    for inner_dicts in nested_list:
        AimCellValue.append(inner_dicts['cells'][columnIndex])
    return AimCellValue


def get_single_cell_value(project_id,cellIndex, rowIndex):
    nested_list=refine.RefineProject(refine.RefineServer(),project_id).get_cell_value()
    aim_single_cell_value=nested_list[rowIndex]['cells'][cellIndex]
    return aim_single_cell_value


def get_split_cell_value(project_id,origin_column_length):
    nested_list=refine.RefineProject(refine.RefineServer(),project_id).get_cell_value()
    print(len(nested_list))
    AimcellValue=[]
    counter=[]
    for inner_dicts in nested_list:
        if len(inner_dicts['cells'])>origin_column_length:
            counter.append(len(inner_dicts['cells'])-origin_column_length-1)
            AimcellValue.append(inner_dicts['cells'][origin_column_length+1:])
    return counter,AimcellValue


def get_preference(project_id,name):
    # get preference: returns the (OR_JSON) value of a given preference setting.
    return refine.RefineProject(refine.RefineServer(),project_id).get_preference(name)


def apply_operations(project_id,file_path):
    # apply operations: apply the json file
    return refine.RefineProject(refine.RefineServer(),project_id).apply_operations(file_path)


def export(project_id,export_format='tsv') :
    # export : return a fileobject of a project's data.
    return refine.RefineProject(refine.RefineServer(),project_id).export(export_format)

def export_rows(project_id,**kwargs):
    # return an iterable of parsed rows of a project's data
    return refine.RefineProject(refine.RefineServer(),project_id).export_rows(**kwargs)


def delete(project_id):
    # delete the project
    return refine.RefineProject(refine.RefineServer(),project_id).delete()


def compute_facets(project_id,facets=None):
    return refine.RefineProject(refine.RefineServer(),project_id).compute_facets(facets)


def get_rows(project_id,facets=None,sort_by=None,start=1,limit=100):
    return refine.RefineProject(refine.RefineServer(),project_id).get_rows(facets,sort_by,start,limit)


def reorder_rows(project_id,sort_by=None):
    return refine.RefineProject(refine.RefineServer(),project_id).reorder_rows(sort_by)


def remove_rows(project_id,facets=None):
    return refine.RefineProject(refine.RefineServer(),project_id).remove_rows(facets)


def text_transform(project_id,column,expression,on_error='set-to-blank',repeat=False,repeat_count=10):
    return refine.RefineProject(refine.RefineServer(),project_id).text_transform(column,expression,on_error,repeat,repeat_count)


'''insert a function to automatically get 'from' '''
def getFromValue(computeCluster):
    fromlist=[]
    fromlistInner=[]
    for list3 in computeCluster:
        for list4 in list3:
            fromlistInner.append(list4['value'])
        fromlist.append(fromlistInner)
        fromlistInner=[]
    return fromlist


'''insert a function to automatically get 'to' '''
def getToValue(computeCluster):
    result=[
        max(list_of_dicts, key=lambda d: d['count'])
        for list_of_dicts in computeCluster
    ]
    chosenvaluelist=[]
    for chosendict in result:
        chosenvaluelist.append(chosendict['value'])
    return chosenvaluelist


def compute_clusters(project_id,column,clusterer_type='binning',function=None,params=None):
    # returns a list of cluters of {'value';..., 'count':...}
    return refine.RefineProject(refine.RefineServer(),project_id).compute_clusters(column,clusterer_type,function,params)


def edit(project_id,column,edit_from,edit_to):
    return refine.RefineProject(refine.RefineServer(),project_id).edit(column,edit_from,edit_to)


def mass_edit(project_id,column,edits,expression='value'):
    return refine.RefineProject(refine.RefineServer(),project_id).mass_edit(column,edits,expression)


def single_edit(project_id,row,cell,type,value):
    return refine.RefineProject(refine.RefineServer(),project_id).single_edit(row,cell,type,value)


def annotate_one_row(project_id,row,annotation,state=True):
    return refine.RefineProject(refine.RefineServer(),project_id).annotate_one_row(row,annotation,state)


def flag_row(project_id,row,flagged=True):
    return refine.RefineProject(refine.RefineServer(),project_id).flag_row(row,flagged)


def star_row(project_id,row,starred=True):
    return refine.RefineProject(refine.RefineServer(),project_id).star_row(row,starred)


def add_column(project_id,column,new_column,expression='value'):
    return refine.RefineProject(refine.RefineServer(),project_id).add_column(column,new_column,expression)


def split_column(project_id,column,separator=',', mode='separator',regex=False,guess_cell_type=True,remove_original_column=True):
    return refine.RefineProject(refine.RefineServer(),project_id).split_column(column,separator,mode,regex,guess_cell_type,remove_original_column)


def rename_column(project_id,column,new_column):
    return refine.RefineProject(refine.RefineServer(),project_id).rename_column(column,new_column)


def reorder_columns(project_id,new_column_order):
    return refine.RefineProject(refine.RefineServer(),project_id).reorder_columns(new_column_order)


def move_column(project_id,column,index):
    return refine.RefineProject(refine.RefineServer(),project_id).move_column(column,index)


def blank_down(project_id,column):
    return refine.RefineProject(refine.RefineServer(),project_id).blank_down(column)


def fill_down(project_id,column):
    return refine.RefineProject(refine.RefineServer(),project_id).fill_down(column)


def transpose_columns_into_rows(project_id,start_column, column_count,
            combined_column_name, separator=':', prepend_column_name=True,
            ignore_blank_cells=True):
    return refine.RefineProject(refine.RefineServer(),project_id).transpose_columns_into_rows(start_column,column_count,combined_column_name,
                                                                                            separator,prepend_column_name,ignore_blank_cells)


def transpose_rows_into_columns(project_id,column,row_count):
    return refine.RefineProject(refine.RefineServer(),project_id).transpose_rows_into_columns(column,row_count)


def guess_types_of_column(project_id,column,service):
    return refine.RefineProject(refine.RefineServer(),project_id).guess_types_of_column(column,service)


def get_reconciliation_services(project_id):
    return refine.RefineProject(refine.RefineServer(),project_id).get_reconciliation_services()


def get_reconciliation_service_by_name_or_url(project_id,name):
    return refine.RefineProject(refine.RefineServer(),project_id).get_reconciliation_service_by_name_or_url(name)


def reconcile(project_id,column,service,reconciliation_type=None,reconciliation_config=None):
    return refine.RefineProject(refine.RefineServer(),project_id).reconcile(column,service,reconciliation_type,reconciliation_config)


def get_operations(project_id):
    return refine.RefineProject(refine.RefineServer(),project_id).get_operations()


def main():
    print('main')


if __name__=='__main__':
    main()