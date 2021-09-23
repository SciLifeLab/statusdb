"""Database backend for connecting to statusdb"""
import re
import collections
from uuid import uuid4
from datetime import datetime
from statusdb.db import Couch
from statusdb.db.utils import save_couchdb_obj
from statusdb.tools.log import minimal_logger
from statusdb.tools.misc import query_yes_no, merge

LOG = minimal_logger(__name__)

# Regular expressions for general use
re_project_id = "^(P[0-9]{3,})"
re_project_id_nr = "^P([0-9]{3,})"

def utc_time():
    """Make an utc_time with appended 'Z'"""
    return str(datetime.utcnow()) + 'Z'

# http://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
# FIX ME: make override work
def _update(d, u, override=True):
    """Update values of a nested dictionary of varying depth"""
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = _update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d

def _return_extensive_match_result(name_map, barcode_name, force=False):
    """Wrap return value for extensive matching"""
    if query_yes_no("found mapping '{} : {}' (barcode_name:project_sample_name); do you want to use this project_sample_name?".format(barcode_name, name_map["sample_name"]), default="no", force=force):
        return name_map
    else:
        return None

def _match_barcode_name_to_project_sample(barcode_name, project_samples, extensive_matching=False, force=False):
    """Take a barcode name and map it to a list of project sample names.

    :param barcode_name: barcode name as it appears in sample sheet
    :param project_samples: dictionary of project samples as obtained from statusdb project_summary
    :param extensive_matching: perform extensive matching of barcode to project sample names
    :param force: override interactive queries. NB: not called from get_project_sample.

    :returns: dictionary with keys project sample name and project sample or None
    """
    if barcode_name in list(project_samples.keys()):
        return {'sample_name':barcode_name, 'project_sample':project_samples[barcode_name]}
    for project_sample_name in list(project_samples.keys()):
        # Look for cases where barcode name is formatted in a way that does not conform to convention
        # NB: only do this interactively!!!
        if not re.search(re_project_id_nr, barcode_name):
            if not extensive_matching:
                return None
            # Project id could be project number without a P, i.e. XXX_XXX_indexXX
            sample_id = re.search("(\d+_)?(\d+)_?([A-Z])?_",barcode_name)
            # Fall back if no hit
            if not sample_id:
                LOG.warn("No regular expression match for barcode name {}; implement new case".format(barcode_name))
                return None
            (prj_id, smp_id, _) = sample_id.groups()
            if not prj_id:
                prj_id=""
            if str(smp_id) == str(project_sample_name):
                return _return_extensive_match_result({'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}, barcode_name, force=force)
            elif str("P{}_{}".format(prj_id.rstrip("_"), smp_id)) == str(project_sample_name):
                return _return_extensive_match_result({'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}, barcode_name, force=force)

            # Sometimes barcode name is of format XX_indexXX, where the number is the sample number
            m = re.search("(_index[0-9]+)", barcode_name)
            if not m:
                index = ""
            else:
                index = m.group(1)
                sample_id = re.search("([A-Za-z0-9\_]+)(\_index[0-9]+)?", barcode_name.replace(index, ""))
                if str(sample_id.group(1)) == str(project_sample_name):
                    return _return_extensive_match_result({'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}, barcode_name, force=force)
                if str(sample_id.group(1)) == str(project_samples[project_sample_name].get("customer_name", None)):
                    return _return_extensive_match_result({'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}, barcode_name, force=force)
                # customer well names contain a 0, as in 11A07; run names don't always
                # FIXME: a function should convert customer name to standard forms in cases like these
                if str(sample_id.group(1)) == str(project_samples[project_sample_name].get("customer_name", "").replace("0", "")):
                    return _return_extensive_match_result({'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}, barcode_name, force=force)
        else:
            prj_id = barcode_name.split("_")[0]
            # Matches project id naming convention PXXX_
            # Look for case barcode: PXXX_XXX[BCDEF]_indexXX, project_sample_name: PXXX_XXX
            if str(barcode_name).startswith(str(project_sample_name)):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}
            elif str(barcode_name).startswith(str(project_sample_name).rstrip("F")):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}
            elif str(barcode_name).startswith(str(project_sample_name).rstrip("B")):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}
            elif str(barcode_name).startswith(str(project_sample_name).rstrip("C")):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}
            elif str(barcode_name).startswith(str(project_sample_name).rstrip("D")):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}
            elif str(barcode_name).startswith(str(project_sample_name).rstrip("E")):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}

            # Look for cases barcode: PXXX_XX[BCDEF]_indexXX matching to project_sample_name: XX_indexXX
            elif str(barcode_name.replace("{}_".format(prj_id), "")).startswith(str(project_sample_name)):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}
            elif str(barcode_name.replace("{}_".format(prj_id), "")).startswith(str(project_sample_name).rstrip("F")):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}
            elif str(barcode_name.replace("{}_".format(prj_id), "")).startswith(str(project_sample_name).rstrip("B")):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}
            elif str(barcode_name.replace("{}_".format(prj_id), "")).startswith(str(project_sample_name).rstrip("C")):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}
            elif str(barcode_name.replace("{}_".format(prj_id), "")).startswith(str(project_sample_name).rstrip("D")):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}
            elif str(barcode_name.replace("{}_".format(prj_id), "")).startswith(str(project_sample_name).rstrip("E")):
                return {'sample_name':project_sample_name, 'project_sample':project_samples[project_sample_name]}
    return None

# Updating function for object comparison
def update_fn(cls, db, obj, viewname = "names/id_to_name", key="name"):
    """Compare object with object in db if present.

    :param cls: calling class
    :param db: couch database
    :param obj: database object to save

    :returns: database object to save and database id if present
    """
    t_utc = utc_time()
    def equal(a, b):
        a_keys = [str(x) for x in list(a.keys()) if x not in ["_id", "_rev", "creation_time", "modification_time"]]
        b_keys = [str(x) for x in list(b.keys()) if x not in ["_id", "_rev", "creation_time", "modification_time"]]
        keys = list(set(a_keys + b_keys))
        return {k:a.get(k, None) for k in keys} == {k:b.get(k, None) for k in keys}

    view = db.view(viewname)
    d_view = {k.value:k for k in view}
    dbid =  d_view.get(obj[key], None)
    dbobj = None

    if dbid:
        dbobj = db.get(dbid.id, None)
    if dbobj is None:
        obj["creation_time"] = t_utc
        return (obj, dbid)
    if equal(obj, dbobj):
        return (None, dbid)
    else:
        # Merge the newly created object with the one found in the database, replacing
        # the information found in the database for the new one if found the same key
        merge(obj, dbobj)
        # We need the original times and id from the DB object though
        obj["creation_time"] = dbobj.get("creation_time")
        obj["modification_time"] = t_utc
        obj["_rev"] = dbobj.get("_rev")
        obj["_id"] = dbobj.get("_id")
        return (obj, dbid)

##############################
# Documents
##############################
class StatusDocument(dict):
    """Generic status document class"""
    _entity_type = "status_document"
    _fields = []
    _dict_fields = []
    _list_fields = []
    def __init__(self, **kw):
        self["_id"] = kw.get("_id", uuid4().hex)
        self["entity_type"] = self._entity_type
        self["name"] = kw.get("name", None)
        self["creation_time"] = kw.get("creation_time", utc_time())
        self["modification_time"] = kw.get("modification_time", utc_time())
        for f in self._fields:
            self[f] = kw.get(f, None)
        for f in self._dict_fields:
            self[f] = kw.get(f, {})
        for f in self._list_fields:
            self[f] = kw.get(f, {})
        self = _update(self, kw)

    def __repr__(self):
        return "<{} {}>".format(self["entity_type"], self["name"])

class ProjectSummaryDocument(StatusDocument):
    """project summary document"""
    _entity_type = "project_summary"
    _fields = ["application", "customer_reference", "min_m_reads_per_sample_ordered",
               "no_of_samples", "project_id", "project_name", "source"]
    _dict_fields = ["samples"]
    def __init__(self, **kw):
        StatusDocument.__init__(self, **kw)

    def __repr__(self):
        return "<{} {}>".format(self["entity_type"], self["project_name"])

class FlowcellRunMetricsDocument(StatusDocument):
    """Flowcell level class for holding qc data."""
    _entity_type = "flowcell_run_metrics"
    _fields = ["name"]
    _dict_fields = ["run_info_yaml", "illumina", "samplesheet_csv"]
    def __init__(self, fc_date=None, fc_name=None, **kw):
        StatusDocument.__init__(self, **kw)
        self._lanes = [1,2,3,4,5,6,7,8]
        self["lanes"] = {str(k):{"lane":str(k), "filter_metrics":{}, "bc_metrics":{}} for k in self._lanes}
        if fc_date and fc_name:
            self["name"] = "{}_{}".format(fc_date, fc_name)

class SampleRunMetricsDocument(StatusDocument):
    """Sample-level class for holding run metrics data"""
    _entity_type = "sample_run_metrics"
    _fields =["barcode_id", "barcode_name", "barcode_type", "bc_count", "date",
              "flowcell", "lane", "sample_prj", "sequence", "barcode_type",
              "genomes_filter_out", "project_sample_name", "project_id"]
    _dict_fields = ["fastqc", "fastq_scr", "picard_metrics", "bcbb_checkpoints"]
    def __init__(self, **kw):
        StatusDocument.__init__(self, **kw)
        self["name"] = "{}_{}_{}_{}".format(self["lane"], self["date"], self["flowcell"], self["sequence"])
        if self["barcode_name"]:
            self.set_project_id()

    def set_project_id(self, value=None):
        """Get corresponding project id for a project name.

        :param value: if not provided will try to identify project based on barcode name
        """
        if value:
            self["project_id"] = value
            return
        m = re.search(re_project_id, self["barcode_name"])
        if m:
            self["project_id"] = m.group(1)
        return

class AnalysisDocument(StatusDocument):
    """Project level document for holding analysis data."""
    _entity_type = "bp_analysis"
    _fields = ["project_name"]
    _dict_fields = ["samples"]
    def __init__(self, **kw):
        StatusDocument.__init__(self, **kw)

##############################
# Connections
##############################
class SampleRunMetricsConnection(Couch):
    _doc_type = SampleRunMetricsDocument
    _update_fn = update_fn
    def __init__(self, dbname="samples", **kwargs):
        super(SampleRunMetricsConnection, self).__init__(**kwargs)
        self.db = self.con[dbname]
        self.name_view = {k.key:k.id for k in self.db.view("names/name", reduce=False)}
        self.name_fc_view = {k.key:k for k in self.db.view("names/name_fc", reduce=False)}
        self.name_proj_view = {k.key:k for k in self.db.view("names/name_proj", reduce=False)}
        self.name_fc_proj_view = {k.key:k for k in self.db.view("names/name_fc_proj", reduce=False)}

    def set_db(self, dbname):
        """Make sure we don't change db from samples"""
        pass

    def get_sample_ids(self, fc_id=None, sample_prj=None):
        """Retrieve sample ids subset by fc_id and/or sample_prj

        :param fc_id: flowcell id
        :param sample_prj: sample project name

        :returns sample_ids: list of couchdb sample ids
        """
        self.log.debug("retrieving sample ids subset by flowcell '{}' and sample_prj '{}'".format(fc_id, sample_prj))
        fc_sample_ids = [self.name_fc_view[k].id for k in list(self.name_fc_view.keys()) if self.name_fc_view[k].value == fc_id] if fc_id else []
        prj_sample_ids = [self.name_proj_view[k].id for k in list(self.name_proj_view.keys()) if self.name_proj_view[k].value == sample_prj] if sample_prj else []
        # | -> union, & -> intersection
        if len(fc_sample_ids) > 0 and len(prj_sample_ids) > 0:
            sample_ids = list(set(fc_sample_ids) & set(prj_sample_ids))
        else:
            sample_ids = list(set(fc_sample_ids) | set(prj_sample_ids))
        # Set to empty list if we actually had supplied a flowcell id and project id but one of them is non-existent
        if fc_id and sample_prj:
            if len(fc_sample_ids)==0:
                sample_ids = []
                self.log.warn("No such flowcell '{}' for project '{}'".format(fc_id, sample_prj))
            elif len(prj_sample_ids)==0:
                sample_ids = []
                self.log.warn("No such project '{}' for flowcell '{}'".format(sample_prj, fc_id))

        self.log.debug("Number of samples: {}, number of fc samples: {}, number of project samples: {}".format(len(sample_ids), len(fc_sample_ids), len(prj_sample_ids)))
        return sample_ids

    def get_samples(self, fc_id=None, sample_prj=None):
        """Retrieve samples subset by fc_id and/or sample_prj

        :param fc_id: flowcell id
        :param sample_prj: sample project name

        :returns samples: list of sample_run_metrics documents
        """
        self.log.debug("retrieving samples subset by flowcell '{}' and sample_prj '{}'".format(fc_id, sample_prj))
        sample_ids = self.get_sample_ids(fc_id, sample_prj)
        inv_view = {v:k for k,v in self.name_view.items()}
        sample_names = [inv_view[x] for x in sample_ids]
        return [self.get_entry(x) for x in sample_names]

    def get_project_sample(self, prj_sample_name, sample_prj=None, fc_id=None):
        """Retrieve all documents for a project sample based on the project_sample_name field,
        possibly subset by sample_prj and fc_id

        :param prj_sample_name: project sample name
        :param sample_prj: Name of the project
        :param fc_id: Flowcell id

        :returns samples: list of sample_run_metrics documents
        """

        return [s for s in self.get_samples(fc_id,sample_prj) if s.get("project_sample_name","") == prj_sample_name]

class FlowcellRunMetricsConnection(Couch):
    _doc_type = FlowcellRunMetricsDocument
    _update_fn = update_fn
    def __init__(self, dbname="flowcells", **kwargs):
        super(FlowcellRunMetricsConnection, self).__init__(**kwargs)
        self.db = self.con[dbname]
        self.name_view = {k.key:k.id for k in self.db.view("names/name", reduce=False)}
        self.storage_status_view = {k.key:k.value for k in self.db.view("info/storage_status")}
        self.id_view = {k.key:k.value for k in self.db.view("info/id")}
        self.stat_view = {k.key:k.value for k in self.db.view("names/Barcode_lane_stat", reduce=False)}

    def set_db(self):
        """Make sure we don't change db from flowcells"""
        pass

    def get_barcode_lane_statistics(self, project_id, sample_id, flowcell, lane):
	"""Get Mean Quality Score (PF) and % of >= Q30 Bases (PF) for
        project_id, sample_id, flow_cell, lane. In the current
        implementation a unique key is made consisting of
        project-sample-lane. Relies entirely on assumption that all
        project names are formatted as J__Doe_00_01 in
        Demultiplex_stats.htm.
        """
        if flowcell not in list(self.stat_view.keys()):
            return None, None
        stats = self.stat_view.get(flowcell)
        stats_d = {"{}-{}-{}".format(item.get("Project", None).replace("__", "."),
                                     item.get("Sample ID", None),
                                     item.get("Lane", None)):item for item in stats}
        sample_data = stats_d.get("{}-{}-{}".format(project_id, sample_id, lane), None)
        if not sample_data:
            return None, None
        return sample_data.get('Mean Quality Score (PF)', None), sample_data.get('% of >= Q30 Bases (PF)', None)

    def get_phix_error_rate(self, name, lane):
        """Get phix error rate. Returns -1 if error rate could not be determined"""
        fc = self.get_entry(name)
        phix_r = []

        # Get the error rate for non-index reads and add them
        summary = fc.get("illumina",{}).get("Summary",{})
        for read in list(summary.values()):
            if read.get("ReadType","").strip() != "(Index)":
                r = float(read.get(lane,{}).get("ErrRatePhiX","-1"))
                # Only use the value if error rate is >0.0
                if r > 0:
                    phix_r.append(r)

        # If no results were found using the "old" structure, try the LIMS-parsed structure
        if len(phix_r) == 0:
            summary = fc.get("illumina",{}).get("run_summary",{})
            data = summary.get(lane,{})
            phix_r = [float(v) for k,v in data.items() if k.startswith("% Error Rate") and float(v) > 0]

        # Return -1 if the error rate could not be determined
        if len(phix_r) == 0:
            return -1

        return sum(phix_r)/len(phix_r)

    def get_instrument(self, name):
        """Get instrument id"""
        fc = self.get_entry(name)
        if not fc:
            return None
        instrument = fc.get('RunInfo', {}).get('Instrument', None)
        if not instrument:
            instrument = fc.get('RunParameters', {}).get('Setup', {}).get('ScannerID', None)
        return instrument

    def get_run_mode(self, name):
        """Get run mode"""
        fc = self.get_entry(name)
        if not fc:
            return None
        run_mode = fc.get('RunParameters', {}).get('Setup', {}).get('RunMode', None)
        return run_mode

    def is_paired_end(self, name):
        """Get paired end status"""
        fc = self.get_entry(name)
        if not fc:
            return None
        reads = fc.get('RunInfo', {}).get('Reads', [])
        return len([read for read in reads if read.get('IsIndexedRead','N') == 'N']) == 2

    def get_storage_status(self, status):
        """Get all runs with the specified storage status.
        """
        self.log.info("Fetching all Flowcells with storage status \"{}\"".format(status))
        return {run: info for run, info in self.storage_status_view.items() if info.get("storage_status") == status}

    def set_storage_status(self, doc_id, status):
        """Sets the run storage status.
        """
        db_run = self.db.get(doc_id)
        if not db_run:
            self.log.error("Document with id {} not found, could not update the " \
                           "storage status")
        else:
            self.log.info("Updating storage status of run {} from {} to {}".format(
                            db_run.get('RunInfo').get('Id'), db_run.get('storage_status'), status))
            db_run['storage_status'] = status
            save_couchdb_obj(self.db, db_run)

class ProjectSummaryConnection(Couch):
    _doc_type = ProjectSummaryDocument
    _update_fn = update_fn
    def __init__(self, dbname="projects", **kwargs):
        super(ProjectSummaryConnection, self).__init__(**kwargs)
        self.db = self.con[dbname]
        self.name_view = {k.key:k.id for k in self.db.view("project/project_name", reduce=False)}
        self.id_view = {k.key:k.id for k in self.db.view("project/project_id", reduce=False)}

    def set_db(self, dbname):
        """Make sure we don't change db from projects"""
        pass

    def get_project_sample(self, project_name, barcode_name=None, extensive_matching=False):
        """Get project sample name for a SampleRunMetrics barcode_name.

        :param project_name: the project name
        :param barcode_name: the barcode name of a sample run
        :param extensive_matching: do extensive matching of barcode names

        :returns: dict(sample_name:project sample name, project_sample:project sample dict) or None
        """
        if not barcode_name:
            return None
        project = self.get_entry(project_name)
        if not project:
            return None
        project_samples = project.get('samples', None)
        return _match_barcode_name_to_project_sample(barcode_name, project_samples, extensive_matching)

    def _get_sample_run_metrics(self, v):
        if v.get('library_prep', None):
            library_preps = v.get('library_prep')
            return {k:v for kk in list(library_preps.keys()) for k, v in library_preps[kk]['sample_run_metrics'].items()} if library_preps else None
        else:
            return v.get('sample_run_metrics', None)

    def get_ordered_amount(self, project_name, rounded=True, dec=1, samples={}):
        """Get (rounded) ordered amount of reads in millions.

        :param project_name: project name
        :param rounded: <boolean>
        :param dec: <integer>, number of decimal places

        :returns: ordered amount of reads if present, None otherwise
        """
        try:
            amount = list(samples.values())[0]["details"]["reads_min"]
        except (TypeError, KeyError):
            amount = self.get_entry(project_name, 'min_m_reads_per_sample_ordered')
        finally:
            return amount

    def get_latest_library_prep(self, project_name):
        """Get mapping from project name to sample_run_metrics for
        latest library prep.

        :param project_name: project name
        """
        project = self.get_entry(project_name)
        if not project:
            return None
        project_samples = project.get('samples', None)
        map_d = {}
        for project_sample_name,sample in project_samples.items():
            if sample.get('library_prep', None):
                library_preps = sample.get('library_prep')
                lkeys = list(library_preps.keys())
                lkeys.sort(reverse=True)
                map_d[project_sample_name] = {k:kk for kk in lkeys[0] for k, v in library_preps[kk].get('sample_run_metrics', {}).items()} if library_preps else None
            else:
                self.log.warn("No library_prep information for project sample {}".format(project_sample_name))
        return map_d

    def get_info_source(self, project_name):
        """Returns the source of information for the project.

        The projects started after July 1st 2013 should have LIMS as source.

        :param projec_name: Project name
        :returns: The source of information for the project.
        """
        project = self.get_entry(project_name)
        return project.get('source', None)


class AnalysisConnection(Couch):
    _doc_type = AnalysisDocument
    _update_fn = update_fn
    def __init__(self, dbname="analysis", **kwargs):
        super(AnalysisConnection, self).__init__(**kwargs)
        self.db = self.con[dbname]
