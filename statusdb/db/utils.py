#!/usr/bin/env python
from uuid import uuid4
from datetime import datetime
import yaml
import couchdb


def load_couch_server(config_file):
    """loads couch server with settings specified in 'config_file'"""
    try:
        stream = open(config_file,'r')
        db_conf = yaml.load(stream)['statusdb']
        url = db_conf['username']+':'+db_conf['password']+'@'+db_conf['url']+':'+str(db_conf['port'])
        couch = couchdb.Server("http://" + url)
        return couch
    except KeyError:
        raise RuntimeError("\"statusdb\" section missing from configuration file.")

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

##############################
# functions that operate on status_document objects
##############################
def calc_avg_qv(srm):
    """Calculate average quality score for a sample based on
    FastQC results.

    FastQC reports QV results in the field 'Per sequence quality scores',
    where the subfields 'Count' and 'Quality' refer to the counts of a given quality value.

    :param srm: sample run metrics

    :returns avg_qv: Average quality value score.
    """
    try:
        count = [float(x) for x in srm["fastqc"]["stats"]["Per sequence quality scores"]["Count"]]
        quality = srm["fastqc"]["stats"]["Per sequence quality scores"]["Quality"]
        return round(sum([x*int(y) for x,y in izip(count, quality)])/sum(count), 1)
    except:
        return None

def get_qc_data(sample_prj, p_con, s_con, fc_id=None):
    """Get qc data for a project, possibly subset by flowcell.

    :param sample_prj: project identifier
    :param p_con: object of type <ProjectSummaryConnection>
    :param s_con: object of type <SampleRunMetricsConnection>

    :returns: dictionary of qc results
    """
    project = p_con.get_entry(sample_prj)
    application = project.get("application", None) if project else None
    samples = s_con.get_samples(fc_id=fc_id, sample_prj=sample_prj)
    qcdata = {}
    for s in samples:
        qcdata[s["name"]]={"sample":s.get("barcode_name", None),
                           "project":s.get("sample_prj", None),
                           "lane":s.get("lane", None),
                           "flowcell":s.get("flowcell", None),
                           "date":s.get("date", None),
                           "application":application,
                           "TOTAL_READS":int(s.get("picard_metrics", {}).get("AL_PAIR", {}).get("TOTAL_READS", -1)),
                           "PERCENT_DUPLICATION":s.get("picard_metrics", {}).get("DUP_metrics", {}).get("PERCENT_DUPLICATION", "-1.0"),
                           "MEAN_INSERT_SIZE":float(s.get("picard_metrics", {}).get("INS_metrics", {}).get("MEAN_INSERT_SIZE", "-1.0").replace(",", ".")),
                           "GENOME_SIZE":int(s.get("picard_metrics", {}).get("HS_metrics", {}).get("GENOME_SIZE", -1)),
                           "FOLD_ENRICHMENT":float(s.get("picard_metrics", {}).get("HS_metrics", {}).get("FOLD_ENRICHMENT", "-1.0").replace(",", ".")),
                           "PCT_USABLE_BASES_ON_TARGET":s.get("picard_metrics", {}).get("HS_metrics", {}).get("PCT_USABLE_BASES_ON_TARGET", "-1.0"),
                           "PCT_TARGET_BASES_10X":s.get("picard_metrics", {}).get("HS_metrics", {}).get("PCT_TARGET_BASES_10X", "-1.0"),
                           "PCT_PF_READS_ALIGNED":s.get("picard_metrics", {}).get("AL_PAIR", {}).get("PCT_PF_READS_ALIGNED", "-1.0"),
                           }
        target_territory = float(s.get("picard_metrics", {}).get("HS_metrics", {}).get("TARGET_TERRITORY", -1))
        pct_labels = ["PERCENT_DUPLICATION", "PCT_USABLE_BASES_ON_TARGET", "PCT_TARGET_BASES_10X",
                      "PCT_PF_READS_ALIGNED"]
        for l in pct_labels:
            if qcdata[s["name"]][l]:
                qcdata[s["name"]][l] = float(qcdata[s["name"]][l].replace(",", ".")) * 100
        if qcdata[s["name"]]["FOLD_ENRICHMENT"] and qcdata[s["name"]]["GENOME_SIZE"] and target_territory:
            qcdata[s["name"]]["PERCENT_ON_TARGET"] = float(qcdata[s["name"]]["FOLD_ENRICHMENT"]/ (float(qcdata[s["name"]]["GENOME_SIZE"]) / float(target_territory))) * 100
    return qcdata

def get_scilife_to_customer_name(project_name, p_con, s_con, get_barcode_seq=False):
    """Get scilife to customer name mapping optionally with barcodes, represented as a
    dictionary.

    :param project_name: project name
    :param p_con: object of type <ProjectSummaryConnection>
    :param s_con: object of type <SampleRunMetricsConnection>
    :param get_barcode_seq: True/False(default)

    :returns: dictionary with keys scilife name and values customer name and barcodes(optional)
    """
    name_d = {}
    for samp in s_con.get_samples(sample_prj=project_name):
        bcname = samp.get("barcode_name", None)
        s = p_con.get_project_sample(project_name, bcname)
        name_d[bcname] = {'scilife_name': s['project_sample'].get('scilife_name', bcname),
                          'customer_name' : s['project_sample'].get('customer_name', None)
                          }
        if get_barcode_seq:
            name_d[bcname]["barcode_seq"] = samp.get("sequence", None)
    return name_d
