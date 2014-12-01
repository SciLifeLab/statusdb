#!/usr/bin/env python
from uuid import uuid4
from datetime import datetime

def find_or_make_key(key):
    if not key:
        key = uuid4().hex
    return key

def save_couchdb_obj(db, obj, add_time_log=True):
    """Updates ocr creates the object obj in database db."""
    dbobj = db.get(obj['_id'])
    time_log = datetime.utcnow().isoformat() + "Z"
    if dbobj is None:
        if add_time_log:
            obj["creation_time"] = time_log
            obj["modification_time"] = time_log
        db.save(obj)
        return 'created'
    else:
        obj["_rev"] = dbobj.get("_rev")
        if add_time_log:
            obj["modification_time"] = time_log
            dbobj["modification_time"] = time_log
            obj["creation_time"] = dbobj["creation_time"]
        if not comp_obj(obj, dbobj):
            db.save(obj)
            return 'uppdated'
    return 'not uppdated'

def comp_obj(obj, dbobj):
    ####temporary
    if 'entity_type' in dbobj and dbobj['entity_type']=='project_summary':
        obj=dont_load_status_if_20158_not_found(obj, dbobj)
    ###end temporary
    """compares the two dictionaries obj and dbobj"""
    if len(obj) == len(dbobj):
        for key in obj.keys():
            try:
                if obj[key] != dbobj[key]:
                    return False
            except KeyError:
                return False
        return True
    else:
        return False

def dont_load_status_if_20158_not_found(obj, dbobj):
    """compares the two dictionaries obj and dbobj"""
    if obj.has_key('samples') and dbobj.has_key('samples'):
        keys = list(set(obj['samples'].keys() + dbobj['samples'].keys()))
        for key in keys:
            if obj['samples'].has_key(key) and dbobj['samples'].has_key(key):
                if obj['samples'][key].has_key('status'):
                    if obj['samples'][key]['status'] == 'doc_not_found':
                        if dbobj['samples'][key].has_key('status'):
                            obj['samples'][key]['status'] = dbobj['samples'][key]['status']
                if obj['samples'][key].has_key('m_reads_sequenced'):
                    if obj['samples'][key]['m_reads_sequenced'] == 'doc_not_found':
                        if dbobj['samples'][key].has_key('m_reads_sequenced'):
                            obj['samples'][key]['m_reads_sequenced'] = dbobj['samples'][key]['m_reads_sequenced']
            try:
                if (obj['samples'][key]['status'] == 'doc_not_found') or (obj['samples'][key]['status'] == None):
                    obj['samples'][key].pop('status')
            except: pass
            try:
                if (obj['samples'][key]['m_reads_sequenced'] == 'doc_not_found') or (obj['samples'][key]['m_reads_sequenced'] == None):
                    obj['samples'][key].pop('m_reads_sequenced')
            except: pass
    return obj

def find_proj_from_view(proj_db, project_name):
    view = proj_db.view('project/project_name')
    for proj in view:
        if proj.key == project_name:
            return proj.value
    return None

def find_proj_from_samp(proj_db, sample_name):
    view = proj_db.view('samples/sample_project_name')
    for samp in view:
        if samp.key == sample_name:
            return samp.value
    return None

def find_samp_from_view(samp_db, proj_name):
    view = samp_db.view('names/id_to_proj')
    samps = {}
    for doc in view:
        if (doc.value[0] == proj_name) or (doc.value[0] == proj_name.lower()):
            samps[doc.key] = doc.value[1:3]
    return samps

def find_flowcell_from_view(flowcell_db, flowcell_name):
    view = flowcell_db.view('names/id_to_name')
    for doc in view:
        if doc.value:
            id = doc.value.split('_')[1]
            if (id == flowcell_name):
                return doc.key

def find_sample_run_id_from_view(samp_db,sample_run):
    view = samp_db.view('names/name_to_id')
    for row in view[sample_run]:
        return row.value
    return None