# -*- coding: utf-8 -*-

# Built-in
import sys
import os
# import itertools as itt
import copy
import warnings
from abc import ABCMeta, abstractmethod
if sys.version[0] == '3':
    import inspect
else:
    # Python 2 back-porting
    import funcsigs as inspect

# Common
import numpy as np
# import scipy.interpolate as scpinterp
# import matplotlib.pyplot as plt
# from matplotlib.tri import Triangulation as mplTri


# tofu
from tofu import __version__ as __version__
import tofu.pathfile as tfpf
import tofu.utils as utils
try:
    import tofu.data._comp as _comp
    import tofu.data._plot as _plot
    import tofu.data._def as _def
    import tofu.data._physics as _physics
except Exception:
    from . import _comp as _comp
    from . import _plot as _plot
    from . import _def as _def
    from . import _physics as _physics

__all__ = ['DataHolder']#, 'Plasma0D']

_SAVEPATH = os.path.abspath('./')


_INTERPT = 'zero'



#############################################
#############################################
#       Abstract Parent class
#############################################
#############################################



class DataHolder(utils.ToFuObject):
    """ A generic class for handling data

    Provides methods for:
        - introspection
        - plateaux finding
        - visualization

    """
    # Fixed (class-wise) dictionary of default properties
    _ddef = {'Id':{'include':['Mod', 'Cls',
                              'Name', 'version']}}
    _dparams = {'origin':(str, 'unknown'),
                'dim':   (str, 'unknown'),
                'quant': (str, 'unknown'),
                'name':  (str, 'unknown'),
                'units': (str, 'a.u.')}

    # Does not exist before Python 3.6 !!!
    def __init_subclass__(cls, **kwdargs):
        # Python 2
        super(DataHolder, cls).__init_subclass__(**kwdargs)
        # Python 3
        #super().__init_subclass__(**kwdargs)
        cls._ddef = copy.deepcopy(DataHolder._ddef)
        #cls._dplot = copy.deepcopy(Struct._dplot)
        #cls._set_color_ddef(cls._color)


    def __init__(self, dref=None, ddata=None,
                 Id=None, Name=None,
                 fromdict=None, SavePath=os.path.abspath('./'),
                 SavePath_Include=tfpf.defInclude):

        # To replace __init_subclass__ for Python 2
        if sys.version[0] == '2':
            self._dstrip = utils.ToFuObjectBase._dstrip.copy()
            self.__class__._strip_init()

        # Create a dplot at instance level
        #self._dplot = copy.deepcopy(self.__class__._dplot)

        kwdargs = locals()
        del kwdargs['self']
        # super()
        super(DataHolder, self).__init__(**kwdargs)

    def _reset(self):
        # Run by the parent class __init__()
        # super()
        super(DataHolder, self)._reset()
        self._dgroup = dict.fromkeys(self._get_keys_dgroup())
        self._dref = dict.fromkeys(self._get_keys_dref())
        self._ddata = dict.fromkeys(self._get_keys_ddata())

    @classmethod
    def _checkformat_inputs_Id(cls, Id=None, Name=None,
                               include=None, **kwdargs):
        if Id is not None:
            assert isinstance(Id, utils.ID)
            Name = Id.Name
        assert isinstance(Name, str), Name
        if include is None:
            include = cls._ddef['Id']['include']
        kwdargs.update({'Name':Name, 'include':include})
        return kwdargs

    ###########
    # Get largs
    ###########

    @staticmethod
    def _get_largs_dref():
        largs = ['dref']
        return largs

    @staticmethod
    def _get_largs_ddata():
        largs = ['ddata']
        return largs


    ###########
    # Get check and format inputs
    ###########

    #---------------------
    # Methods for checking and formatting inputs
    #---------------------

    def _extract_known_params(self, key, dd):
        # Check no reserved key is used
        lkout = ['group', 'depend', 'ref', 'refs', 'groups',
                 'lref', 'ldata']
        lkind = [kk in dd.keys() for kk in lkout]
        if any(lkind):
            msg = "The following keys are reserved for internal use:\n"
            msg += "    %s\n"%str(lkout)
            msg += "  => Please do not use them !"
            raise Exception(msg)

        dparams = {kk:vv for kk, vv in dd.items() if kk != 'data'}
        dparams.update({kk: dd.get(kk, vv[1]) for kk, vv in self._dparams.items()})
        for kk, vv in dparams.items():
            if not (vv is None or isinstance(vv, self._dparams[kk][0])):
                msg = "A parameter for %s has the wrong type:\n"%key
                msg += "    - Provided: type(%s) = %s\n"%(kk, str(type(vv)))
                msg += "    - Expected %s"%str(self._dparams[kk][0])
                raise Exception(msg)
        return dparams


    def _checkformat_dref(self, dref):
        c0 = isinstance(dref, dict)
        c0 = c0 and  all([isinstance(kk, str) for kk in dref.keys()])
        if not c0:
            msg = "Provided dref must be dict !\n"
            msg += "All its keys must be str !"
            raise Exception(msg)

        for kk, vv in dref.items():
            c0 = isinstance(vv, dict)
            c0 = c0 and 'group' in vv.keys() and isinstance(vv['group'], str)
            c0 = c0 and 'data' in vv.keys()
            if not c0:
                msg = "dref must contain dict with at least the keys:\n"
                msg += "    - 'group': a str indicating the group of refs\n"
                msg += "    - 'data': a 1d array containing the data"
                raise Exception(msg)

            if vv['group'] not in self._dgroup.keys():
                self._dgroup[vv['group']] = {}

            if kk in self._ddata.keys():
                msg = "key '%s' already used !\n"%kk
                msg += "  => each key must be unique !"
                raise Exception(msg)

            data = vv['data']
            if not isinstance(data, np.ndarray):
                if isinstance(data, dict):
                    size = '?'
                elif issubclass(data.__class__, ToFuObject):
                    size = '?'
                else:
                    try:
                        data = np.atleast_1d(data).ravel()
                        size = data.size
                    except:
                        msg = "Could not convert dref[%s]['data'] to array"%kk
                        raise Exception(msg)
            else:
                if data.ndim != 1:
                    data = np.atleast_1d(data).ravel()
                size = data.size

            dref[kk] = {'size':size, 'group':vv['group']}

            dparams = self._extract_known_params(kk, vv)
            self._ddata[kk] = {'data':data, 'ref':(kk,),
                               'shape':(size,), **dparams}

    def _checkformat_ddata(self, ddata):
        c0 = isinstance(ddata, dict)
        c0 = c0 and  all([isinstance(kk, str) for kk in ddata.keys()])
        if not c0:
            msg = "Provided ddata must be dict !\n"
            msg += "All its keys must be str !"
            raise Exception(msg)

        # Start check on each key
        for kk, vv in ddata.items():

            # Check value is a dict with proper keys
            c0 = isinstance(vv, dict)
            c0 = c0 and 'ref' in vv.keys() and isinstance(vv['ref'], tuple)
            c0 = c0 and 'data' in vv.keys()
            if not c0:
                msg = "ddata must contain dict with at least the keys:\n"
                msg += "    - 'ref': a str indicating the ref(s) dependencies\n"
                msg += "    - 'data': a 1d array containing the data"
                raise Exception(msg)

            # Check key unicity
            if kk in self._ddata.keys():
                msg = "key '%s' already used !\n"%kk
                msg += "  => each key must be unique !"
                raise Exception(msg)

            # Extract data and shape
            data = vv['data']
            if not isinstance(data, np.ndarray):
                try:
                    data = np.asarray(data)
                    shape = data.shape
                except:
                    assert type(data) in [list, tuple]
                    shape = (len(data), '?')
            else:
                data = np.atleast_1d(np.squeeze(data))
                shape = data.shape

            # Check proper ref (existence and shape / size)
            for ii, rr in enumerate(vv['ref']):
                if rr not in self._dref.keys():
                    msg = "ddata[%s] depends on an unknown ref !\n"%kk
                    msg += "    - ddata[%s]['ref'] = %s\n"%(kk, rr)
                    msg += "  => %s not in self.dref !\n"%rr
                    msg += "  => self.add_ref( %s ) first !"%rr
                    raise Exception(msg)
            shaperef = (self._dref[rr]['size'] for rr in vv['ref'])
            if not shape == shaperef:
                msg = "Inconsistency between data shape and ref size !\n"
                msg += "    - ddata[%s]['data'] shape: %s\n"%(kk, str(shape))
                msg += "    - sizes of refs: %s"%(str(shaperef))
                raise Exception(msg)

            # Extract params and set self._ddata
            dparams = self._extract_known_params(kk, vv)
            self._ddata[kk] = {'data':data, 'ref':vv['ref'],
                               'shape':shape,
                               **dparams}


    def _complement_dgrouprefdata(self):

        # --------------
        # ddata
        for k0, v0 in self._ddata.items():

            # Check all ref are in dref
            lrefout = [ii for ii in v0['ref'] if ii not in self._dref.keys()]
            if len(lrefout) != 0:
                msg = "ddata[%s]['ref'] has keys not in dref:\n"%k0
                msg += "    - " + "\n    - ".join(lrefout)
                raise Exception(msg)

            # set group
            groups = (self._dref[rr]['group'] for rr in v0['ref'])
            assert all([gg in self._dgroup.keys() for gg in groups])
            self._ddata[k0]['group'] = groups

        # --------------
        # dref
        for k0 in self._dref.keys():
            self._dref[k0]['ldata'] = [kk for kk, vv in self._ddata.items()
                                       if k0 in vv['ref']]
            assert self._dref[k0]['group'] in self._dgroup.keys()

        # --------------
        # dgroup
        for gg, vg in self._dgroup.items():
            lref = [rr for rr, vv in self._dref.items()
                    if vv['group'] == gg]
            ldata = [dd for dd in self._ddata.keys()
                     if any([dd in self._dref[vref]['ldata']
                             for vref in lref])]
            #assert vg['depend'] in lidindref
            self._dgroup[gg]['lref'] = lref
            self._dgroup[gg]['ldata'] = ldata



    ###########
    # Get keys of dictionnaries
    ###########

    @staticmethod
    def _get_keys_dgroup():
        lk = ['lref', 'ldata']
        return lk

    @staticmethod
    def _get_keys_dref():
        lk = ['group', 'size', 'ldata']
        return lk

    @staticmethod
    def _get_keys_ddata():
        lk = ['data', 'ref', 'shape', 'group']
        return lk

    ###########
    # _init
    ###########

    def _init(self, dref=None, ddata=None, **kwargs):
        kwdargs = {'dref':dref, 'ddata':ddata, **kwargs}
        largs = self._get_largs_dref()
        kwddref = self._extract_kwdargs(kwdargs, largs)
        self._set_dref(**kwddref, complement=False)
        largs = self._get_largs_ddata()
        kwddata = self._extract_kwdargs(kwdargs, largs)
        self._set_ddata(**kwddata)
        self._dstrip['strip'] = 0


    ###########
    # set dictionaries
    ###########

    def _set_dref(self, dref, complement=True):
        self._checkformat_dref(dref)
        if complement:
            self._complement_dgrouprefdata()

    def _set_ddata(self, ddata):
        self._checkformat_ddata(ddata)
        self._complement_dgrouprefdata()

    def add_ref(self, key, data=None, group=None, **kwdargs):
        self._set_dref({key:{'data':data, 'group':group, **kwdargs}})

    def remove_ref(self, key):
        assert key in self._dref.keys()
        lkdata = []
        del self._dref[key]
        for kk in lkdata:
            del self._ddata[kk]
        self._complement_dgrouprefdata()

    def add_data(self, key, data=None, ref=None, **kwdargs):
        self._set_ddata({key: {'data':data, 'ref':ref, **kwdargs}})

    def remove_data(self, key, propagate=True):
        if key in self._dref.keys():
            self.remove_ref(key)
        else:
            assert key in self._ddata.keys()
            if propagate:
                # Check if associated ref shall be removed too
                lref = self._ddata[key]['ref']
                for kref in lref:
                    # Remove if key was the only associated data
                    if self._dref[kref]['ldata'] == [key]:
                        del self._dref[kref]
            del self._ddata[key]


    ###########
    # strip dictionaries
    ###########

    def _strip_ddata(self, strip=0, verb=0):
        pass

    ###########
    # _strip and get/from dict
    ###########

    @classmethod
    def _strip_init(cls):
        cls._dstrip['allowed'] = [0,1]
        nMax = max(cls._dstrip['allowed'])
        doc = """
                 1: None
                 """
        doc = utils.ToFuObjectBase.strip.__doc__.format(doc,nMax)
        if sys.version[0] == '2':
            cls.strip.__func__.__doc__ = doc
        else:
            cls.strip.__doc__ = doc

    def strip(self, strip=0, verb=True):
        # super()
        super(DataHolder, self).strip(strip=strip, verb=verb)

    def _strip(self, strip=0, verb=True):
        self._strip_ddata(strip=strip, verb=verb)

    def _to_dict(self):
        dout = {'dgroup':{'dict':self._dgroup, 'lexcept':None},
                'dref':{'dict':self._dref, 'lexcept':None},
                'ddata':{'dict':self._ddata, 'lexcept':None}}
        return dout

    def _from_dict(self, fd):
        self._dgroup.update(**fd['dgroup'])
        self._dref.update(**fd['dref'])
        self._ddata.update(**fd['ddata'])
        self._complement_dgrouprefdata()


    ###########
    # properties
    ###########

    @property
    def dgroup(self):
        return self._dgroup
    @property
    def dref(self):
        return self._dref
    @property
    def ddata(self):
        return self._ddata

    #---------------------
    # Read-only for internal use
    #---------------------

    # Replace with select !!!
    def _get_ldata(self, dim=None, quant=None, name=None,
                   units=None, origin=None,
                   indref=None, group=None, log='all', return_key=True):
        assert log in ['all','any','raw']
        lid = np.array(list(self._ddata.keys()))
        ind = np.ones((7,len(lid)),dtype=bool)
        if dim is not None:
            ind[0,:] = [self._ddata[id_]['dim'] == dim for id_ in lid]
        if quant is not None:
            ind[1,:] = [self._ddata[id_]['quant'] == quant for id_ in lid]
        if name is not None:
            ind[2,:] = [self._ddata[id_]['name'] == name for id_ in lid]
        if units is not None:
            ind[3,:] = [self._ddata[id_]['units'] == units for id_ in lid]
        if origin is not None:
            ind[4,:] = [self._ddata[id_]['origin'] == origin for id_ in lid]
        if indref is not None:
            ind[5,:] = [depend in self._ddata[id_]['depend'] for id_ in lid]
        if group is not None:
            ind[6,:] = [group in self._ddata[id_]['lgroup'] for id_ in lid]

        if log == 'all':
            ind = np.all(ind, axis=0)
        elif log == 'any':
            ind = np.any(ind, axis=0)

        if return_key:
            if np.any(ind):
                out = lid[ind.nonzero()[0]]
            else:
                out = np.array([],dtype=int)
        else:
            out = ind, lid
        return out

    def _get_keyingroup(self, str_, group=None, msgstr=None, raise_=False):

        if str_ in self._ddata.keys():
            lg = self._ddata[str_]['lgroup']
            if group is None or group in lg:
                return str_, None
            else:
                msg = "Required data key does not have matching group:\n"
                msg += "    - ddata[%s]['lgroup'] = %s"%(str_, lg)
                msg += "    - Expected group:  %s"%group
                if raise_:
                    raise Exception(msg)

        ind, akeys = self._get_ldata(dim=str_, quant=str_, name=str_, units=str_,
                                     origin=str_, group=group, log='raw',
                                     return_key=False)
        # Remove indref and group
        ind = ind[:5,:] & ind[-1,:]

        # Any perfect match ?
        nind = np.sum(ind, axis=1)
        sol = (nind == 1).nonzero()[0]
        key, msg = None, None
        if sol.size > 0:
            if np.unique(sol).size == 1:
                indkey = ind[sol[0],:].nonzero()[0]
                key = akeys[indkey][0]
            else:
                lstr = "[dim,quant,name,units,origin]"
                msg = "Several possible unique matches in %s for %s"(lstr,str_)
        else:
            lstr = "[dim,quant,name,units,origin]"
            msg = "No unique match in %s for %s in group %s"%(lstr,str_,group)

        if msg is not None:
            msg += "\n\nRequested %s could not be identified !\n"%msgstr
            msg += "Please provide a valid (unique) key/name/quant/dim:\n\n"
            msg += self.get_summary(verb=False, return_='msg')
            if raise_:
                raise Exception(msg)
        return key, msg


    #---------------------
    # Methods for showing data
    #---------------------

    def get_summary(self, sep='  ', line='-', just='l',
                    table_sep=None, verb=True, return_=False):
        """ Summary description of the object content """
        # # Make sure the data is accessible
        # msg = "The data is not accessible because self.strip(2) was used !"
        # assert self._dstrip['strip']<2, msg

        # -----------------------
        # Build for ddata
        col0 = ['group key', 'nb. indref']
        ar0 = [(k0, len(v0['lindref'])) for k0,v0 in self._dgroup.items()]

        # -----------------------
        # Build for ddata
        col1 = ['indref key', 'group', 'size']
        ar1 = [(k0, v0['group'], v0['size']) for k0,v0 in self._dindref.items()]

        # -----------------------
        # Build for ddata
        col2 = ['data key', 'origin', 'dim', 'quant',
                'name', 'units', 'shape', 'depend', 'lgroup']
        ar2 = []
        for k0,v0 in self._ddata.items():
            if type(v0['data']) is np.ndarray:
                shape = str(v0['data'].shape)
            else:
                shape = v0['data'].__class__.__name__
            lu = [k0, v0['origin'], v0['dim'], v0['quant'], v0['name'],
                  v0['units'], shape,
                  str(v0['depend']), str(v0['lgroup'])]
            ar2.append(lu)

        return self._get_summary([ar0,ar1,ar2], [col0, col1, col2],
                                  sep=sep, line=line, table_sep=table_sep,
                                  verb=verb, return_=return_)


    #---------------------
    # Methods for adding ref / quantities
    #---------------------

    def add_ref(self, key=None, data=None, group=None,
                dim=None, quant=None, units=None, origin=None, name=None):
        """ Add a reference """
        assert type(key) is str and key not in self._ddata.keys()
        assert type(data) in [np.ndarray, dict]
        out = self._extract_dnd({key:{'dim':dim, 'quant':quant, 'name':name,
                                 'units':units, 'origin':origin}}, key)
        dim, quant, origin, name, units = out
        assert group in self._dgroup.keys()
        if type(data) is np.ndarray:
            size = data.shape[0]
        else:
            assert data['ftype'] in [0,1]
            size = data['nnodes'] if data['ftype'] == 1 else data['nfaces']

        self._dindref[key] = {'group':group, 'size':size, 'ldata':[key]}

        self._ddata[key] = {'data':data,
                            'dim':dim, 'quant':quant, 'units':units,
                            'origin':origin, 'name':name,
                            'depend':(key,), 'lgroup':[group]}
        self._complement()

    def add_quantity(self, key=None, data=None, depend=None,
                     dim=None, quant=None, units=None,
                     origin=None, name=None):
        """ Add a quantity """
        c0 = type(key) is str and key not in self._ddata.keys()
        if not c0:
            msg = "key must be a str not already in self.ddata.keys()!\n"
            msg += "    - Provided: %s"%str(key)
            raise Exception(msg)
        if type(data) not in [np.ndarray, dict]:
            msg = "data must be either:\n"
            msg += "    - np.ndarray\n"
            msg += "    - dict (mesh)\n"
            msg += "\n    Provided: %s"%str(type(data))
            raise Exception(msg)
        out = self._extract_dnd({key:{'dim':dim, 'quant':quant, 'name':name,
                                 'units':units, 'origin':origin}}, key)
        dim, quant, origin, name, units = out
        assert type(depend) in [list,str,tuple]
        if type(depend) is str:
            depend = (depend,)
        for ii in range(0,len(depend)):
            assert depend[ii] in self._dindref.keys()
        lgroup = [self._dindref[dd]['group'] for dd in depend]
        self._ddata[key] = {'data':data,
                            'dim':dim, 'quant':quant, 'units':units,
                            'origin':origin, 'name':name,
                            'depend':tuple(depend), 'lgroup':lgroup}
        self._complement()


    #---------------------
    # Method for getting time of a quantity
    #---------------------

    def get_time(self, key):
        """ Return the time vector associated to a chosen quantity (identified
        by its key)"""

        if key not in self._ddata.keys():
            msg = "Provided key not in self.ddata.keys() !\n"
            msg += "    - Provided: %s\n"%str(key)
            msg += "    - Available: %s\n"%str(self._ddata.keys())
            raise Exception(msg)

        indref = self._ddata[key]['depend'][0]
        t = [kk for kk in self._dindref[indref]['ldata']
             if (self._ddata[kk]['depend'] == (indref,)
                 and self._ddata[kk]['quant'] == 't')]
        if len(t) != 1:
            msg = "No / several macthing time vectors were identified:\n"
            msg += "    - Provided: %s\n"%key
            msg += "    - Found: %s"%str(t)
            raise Exception(msg)
        return t[0]


    def get_time_common(self, lkeys, choose=None):
        """ Return the common time vector to several quantities

        If they do not have a common time vector, a reference one is choosen
        according to criterion choose
        """
        # Check all data have time-dependency
        dout = {kk: {'t':self.get_time(kk)} for kk in lkeys}
        dtu = dict.fromkeys(set([vv['t'] for vv in dout.values()]))
        for kt in dtu.keys():
            dtu[kt] = {'ldata':[kk for kk in lkeys if dout[kk]['t'] == kt]}
        if len(dtu) == 1:
            tref = list(dtu.keys())[0]
        else:
            lt, lres = zip(*[(kt,np.mean(np.diff(self._ddata[kt]['data'])))
                             for kt in dtu.keys()])
            if choose is None:
                choose  = 'min'
            if choose == 'min':
                tref = lt[np.argmin(lres)]
        return dout, dtu, tref

    @staticmethod
    def _get_time_common_arrays(dins, choose=None):
        dout = dict.fromkeys(dins.keys())
        dtu = {}
        for k, v in dins.items():
            c0 = type(k) is str
            c0 = c0 and all([ss in v.keys() for ss in ['val','t']])
            c0 = c0 and all([type(v[ss]) is np.ndarray for ss in ['val','t']])
            c0 = c0 and v['t'].size in v['val'].shape
            if not c0:
                msg = "dins must be a dict of the form (at least):\n"
                msg += "    dins[%s] = {'val': np.ndarray,\n"%str(k)
                msg += "                't':   np.ndarray}\n"
                msg += "Provided: %s"%str(dins)
                raise Exception(msg)

            kt, already = id(v['t']), True
            if kt not in dtu.keys():
                lisclose = [kk for kk, vv in dtu.items()
                            if (vv['val'].shape == v['t'].shape
                                and np.allclose(vv['val'],v['t']))]
                assert len(lisclose) <= 1
                if len(lisclose) == 1:
                    kt = lisclose[0]
                else:
                    already = False
                    dtu[kt] = {'val':np.atleast_1d(v['t']).ravel(),
                               'ldata':[k]}
            if already:
                dtu[kt]['ldata'].append(k)
            assert dtu[kt]['val'].size == v['val'].shape[0]
            dout[k] = {'val':v['val'], 't':kt}

        if len(dtu) == 1:
            tref = list(dtu.keys())[0]
        else:
            lt, lres = zip(*[(kt,np.mean(np.diff(dtu[kt]['val'])))
                             for kt in dtu.keys()])
            if choose is None:
                choose  = 'min'
            if choose == 'min':
                tref = lt[np.argmin(lres)]
        return dout, dtu, tref

    def _interp_on_common_time(self, lkeys,
                               choose='min', interp_t=None, t=None,
                               fill_value=np.nan):
        """ Return a dict of time-interpolated data """
        dout, dtu, tref = self.get_time_common(lkeys)
        if type(t) is np.ndarray:
            tref = np.atleast_1d(t).ravel()
            tr = tref
            ltu = dtu.keys()
        else:
            if type(t) is str:
                tref = t
            tr = self._ddata[tref]['data']
            ltu = set(dtu.keys())
            if tref in dtu.keys():
                ltu = ltu.difference([tref])

        if interp_t is None:
            interp_t = _INTERPT

        # Interpolate
        for tt in ltu:
            for kk in dtu[tt]['ldata']:
                dout[kk]['val'] = scpinterp.interp1d(self._ddata[tt]['data'],
                                                     self._ddata[kk]['data'],
                                                     kind=interp_t, axis=0,
                                                     bounds_error=False,
                                                     fill_value=fill_value)(tr)

        if type(tref) is not np.ndarray and tref in dtu.keys():
            for kk in dtu[tref]['ldata']:
                 dout[kk]['val'] = self._ddata[kk]['data']

        return dout, tref

    def _interp_on_common_time_arrays(self, dins,
                                      choose='min', interp_t=None, t=None,
                                      fill_value=np.nan):
        """ Return a dict of time-interpolated data """
        dout, dtu, tref = self._get_time_common_arrays(dins)
        if type(t) is np.ndarray:
            tref = np.atleast_1d(t).ravel()
            tr = tref
            ltu = dtu.keys()
        else:
            if type(t) is str:
                assert t in dout.keys()
                tref = dout[t]['t']
            tr = dtu[tref]['val']
            ltu = set(dtu.keys()).difference([tref])

        if interp_t is None:
            interp_t = _INTERPT

        # Interpolate
        for tt in ltu:
            for kk in dtu[tt]['ldata']:
                dout[kk]['val'] = scpinterp.interp1d(dtu[tt]['val'],
                                                     dout[kk]['val'],
                                                     kind=interp_t, axis=0,
                                                     bounds_error=False,
                                                     fill_value=fill_value)(tr)
        return dout, tref

    def interp_t(self, dkeys,
                 choose='min', interp_t=None, t=None,
                 fill_value=np.nan):
        # Check inputs
        assert type(dkeys) in [list,dict]
        if type(dkeys) is list:
            dkeys = {kk:{'val':kk} for kk in dkeys}
        lc = [(type(kk) is str
               and type(vv) is dict
               and type(vv.get('val',None)) in [str,np.ndarray])
              for kk,vv in dkeys.items()]
        assert all(lc), str(dkeys)

        # Separate by type
        dk0 = dict([(kk,vv) for kk,vv in dkeys.items()
                    if type(vv['val']) is str])
        dk1 = dict([(kk,vv) for kk,vv in dkeys.items()
                    if type(vv['val']) is np.ndarray])
        assert len(dkeys) == len(dk0) + len(dk1), str(dk0) + '\n' + str(dk1)


        if len(dk0) == len(dkeys):
            lk = [v['val'] for v in dk0.values()]
            dout, tref = self._interp_on_common_time(lk, choose=choose,
                                                     t=t, interp_t=interp_t,
                                                     fill_value=fill_value)
            dout = {kk:{'val':dout[vv['val']]['val'], 't':dout[vv['val']]['t']}
                    for kk,vv in dk0.items()}
        elif len(dk1) == len(dkeys):
            dout, tref = self._interp_on_common_time_arrays(dk1, choose=choose,
                                                            t=t, interp_t=interp_t,
                                                            fill_value=fill_value)

        else:
            lk = [v['val'] for v in dk0.values()]
            if type(t) is np.ndarray:
                dout, tref =  self._interp_on_common_time(lk, choose=choose,
                                                       t=t, interp_t=interp_t,
                                                       fill_value=fill_value)
                dout1, _   = self._interp_on_common_time_arrays(dk1, choose=choose,
                                                              t=t, interp_t=interp_t,
                                                              fill_value=fill_value)
            else:
                dout0, dtu0, tref0 = self.get_time_common(lk,
                                                          choose=choose)
                dout1, dtu1, tref1 = self._get_time_common_arrays(dk1,
                                                                  choose=choose)
                if type(t) is str:
                    lc = [t in dtu0.keys(), t in dout1.keys()]
                    if not any(lc):
                        msg = "if t is str, it must refer to a valid key:\n"
                        msg += "    - %s\n"%str(dtu0.keys())
                        msg += "    - %s\n"%str(dout1.keys())
                        msg += "Provided: %s"%t
                        raise Exception(msg)
                    if lc[0]:
                        t0, t1 = t, self._ddata[t]['data']
                    else:
                        t0, t1 = dtu1[dout1[t]['t']]['val'], t
                    tref = t
                else:
                    if choose is None:
                        choose = 'min'
                    if choose == 'min':
                        t0 = self._ddata[tref0]['data']
                        t1 = dtu1[tref1]['val']
                        dt0 = np.mean(np.diff(t0))
                        dt1 = np.mean(np.diff(t1))
                        if dt0 < dt1:
                            t0, t1, tref = tref0, t0, tref0
                        else:
                            t0, t1, tref = t1, tref1, tref1

                dout, tref =  self._interp_on_common_time(lk, choose=choose,
                                                          t=t0, interp_t=interp_t,
                                                          fill_value=fill_value)
                dout = {kk:{'val':dout[vv['val']]['val'],
                            't':dout[vv['val']]['t']}
                        for kk,vv in dk0.items()}
                dout1, _   = self._interp_on_common_time_arrays(dk1, choose=choose,
                                                                t=t1, interp_t=interp_t,
                                                                fill_value=fill_value)
            dout.update(dout1)

        return dout, tref

    #---------------------
    # Methods for computing additional plasma quantities
    #---------------------


    def _fill_dins(self, dins):
        for k in dins.keys():
            if type(dins[k]['val']) is str:
                assert dins[k]['val'] in self._ddata.keys()
            else:
                dins[k]['val'] = np.atleast_1d(dins[k]['val'])
                assert dins[k]['t'] is not None
                dins[k]['t'] = np.atleast_1d(dins[k]['t']).ravel()
                assert dins[k]['t'].size == dins[k]['val'].shape[0]
        return dins

    @staticmethod
    def _checkformat_shapes(dins):
        shape = None
        for k in dins.keys():
            dins[k]['shape'] = dins[k]['val'].shape
            if shape is None:
                shape = dins[k]['shape']
            if dins[k]['shape'] != shape:
                if dins[k]['val'].ndim > len(shape):
                    shape = dins[k]['shape']

        # Check shape consistency for broadcasting
        assert len(shape) in [1,2]
        if len(shape) == 1:
            for k in dins.keys():
                assert dins[k]['shape'][0] in [1,shape[0]]
                if dins[k]['shape'][0] < shape[0]:
                    dins[k]['val'] = np.full((shape[0],), dins[k]['val'][0])
                    dins[k]['shape'] = dins[k]['val'].shape

        elif len(shape) == 2:
            for k in dins.keys():
                if len(dins[k]['shape']) == 1:
                    if dins[k]['shape'][0] not in [1]+list(shape):
                        msg = "Non-conform shape for dins[%s]:\n"%k
                        msg += "    - Expected: (%s,...) or (1,)\n"%str(shape[0])
                        msg += "    - Provided: %s"%str(dins[k]['shape'])
                        raise Exception(msg)
                    if dins[k]['shape'][0] == 1:
                        dins[k]['val'] = dins[k]['val'][None,:]
                    elif dins[k]['shape'][0] == shape[0]:
                        dins[k]['val'] = dins[k]['val'][:,None]
                    else:
                        dins[k]['val'] = dins[k]['val'][None,:]
                else:
                    assert dins[k]['shape'] == shape
                dins[k]['shape'] = dins[k]['val'].shape
        return dins



    def compute_bremzeff(self, Te=None, ne=None, zeff=None, lamb=None,
                         tTe=None, tne=None, tzeff=None, t=None,
                         interp_t=None):
        """ Return the bremsstrahlung spectral radiance at lamb

        The plasma conditions are set by:
            - Te   (eV)
            - ne   (/m3)
            - zeff (adim.)

        The wavelength is set by the diagnostics
            - lamb (m)

        The vol. spectral emis. is returned in ph / (s.m3.sr.m)

        The computation requires an intermediate : gff(Te, zeff)
        """
        dins = {'Te':{'val':Te, 't':tTe},
                'ne':{'val':ne, 't':tne},
                'zeff':{'val':zeff, 't':tzeff}}
        lc = [vv['val'] is None for vv in dins.values()]
        if any(lc):
            msg = "All fields should be provided:\n"
            msg += "    - %s"%str(dins.keys())
            raise Exception(msg)
        dins = self._fill_dins(dins)
        dins, t = self.interp_t(dins, t=t, interp_t=interp_t)
        lamb = np.atleast_1d(lamb)
        dins['lamb'] = {'val':lamb}
        dins = self._checkformat_shapes(dins)

        val, units = _physics.compute_bremzeff(dins['Te']['val'],
                                               dins['ne']['val'],
                                               dins['zeff']['val'],
                                               dins['lamb']['val'])
        return val, t, units

    def compute_fanglev(self, BR=None, BPhi=None, BZ=None,
                        ne=None, lamb=None, t=None, interp_t=None,
                        tBR=None, tBPhi=None, tBZ=None, tne=None):
        """ Return the vector faraday angle at lamb

        The plasma conditions are set by:
            - BR    (T) , array of R component of B
            - BRPhi (T) , array of phi component of B
            - BZ    (T) , array of Z component of B
            - ne    (/m3)

        The wavelength is set by the diagnostics
            - lamb (m)

        The vector faraday angle is returned in T / m
        """
        dins = {'BR':  {'val':BR,   't':tBR},
                'BPhi':{'val':BPhi, 't':tBPhi},
                'BZ':  {'val':BZ,   't':tBZ},
                'ne':  {'val':ne,   't':tne}}
        dins = self._fill_dins(dins)
        dins, t = self.interp_t(dins, t=t, interp_t=interp_t)
        lamb = np.atleast_1d(lamb)
        dins['lamb'] = {'val':lamb}
        dins = self._checkformat_shapes(dins)

        val, units = _physics.compute_fangle(BR=dins['BR']['val'],
                                             BPhi=dins['BPhi']['val'],
                                             BZ=dins['BZ']['val'],
                                             ne=dins['ne']['val'],
                                             lamb=dins['lamb']['val'])
        return val, t, units



    #---------------------
    # Methods for interpolation
    #---------------------


    def _get_quantrefkeys(self, qq, ref1d=None, ref2d=None):

        # Get relevant lists
        kq, msg = self._get_keyingroup(qq, 'mesh', msgstr='quant', raise_=False)
        if kq is not None:
            k1d, k2d = None, None
        else:
            kq, msg = self._get_keyingroup(qq, 'radius', msgstr='quant', raise_=True)
            if ref1d is None and ref2d is None:
                msg = "quant %s needs refs (1d and 2d) for interpolation\n"%qq
                msg += "  => ref1d and ref2d cannot be both None !"
                raise Exception(msg)
            if ref1d is None:
                ref1d = ref2d
            k1d, msg = self._get_keyingroup(ref1d, 'radius',
                                            msgstr='ref1d', raise_=False)
            if k1d is None:
                msg += "\n\nInterpolation of %s:\n"%qq
                msg += "  ref could not be identified among 1d quantities\n"
                msg += "    - ref1d : %s"%ref1d
                raise Exception(msg)
            if ref2d is None:
                ref2d = ref1d
            k2d, msg = self._get_keyingroup(ref2d, 'mesh',
                                            msgstr='ref2d', raise_=False)
            if k2d is None:
                msg += "\n\nInterpolation of %s:\n"
                msg += "  ref could not be identified among 2d quantities\n"
                msg += "    - ref2d: %s"%ref2d
                raise Exception(msg)

            q1d, q2d = self._ddata[k1d]['quant'], self._ddata[k2d]['quant']
            if q1d != q2d:
                msg = "ref1d and ref2d must be of the same quantity !\n"
                msg += "    - ref1d (%s):   %s\n"%(ref1d, q1d)
                msg += "    - ref2d (%s):   %s"%(ref2d, q2d)
                raise Exception(msg)

        return kq, k1d, k2d


    def _get_indtmult(self, idquant=None, idref1d=None, idref2d=None):

        # Get time vectors and bins
        idtq = self._ddata[idquant]['depend'][0]
        tq = self._ddata[idtq]['data']
        tbinq = 0.5*(tq[1:]+tq[:-1])
        if idref1d is not None:
            idtr1 = self._ddata[idref1d]['depend'][0]
            tr1 = self._ddata[idtr1]['data']
            tbinr1 = 0.5*(tr1[1:]+tr1[:-1])
        if idref2d is not None and idref2d != idref1d:
            idtr2 = self._ddata[idref2d]['depend'][0]
            tr2 = self._ddata[idtr2]['data']
            tbinr2 = 0.5*(tr2[1:]+tr2[:-1])

        # Get tbinall and tall
        if idref1d is None:
            tbinall = tbinq
            tall = tq
        else:
            if idref2d is None:
                tbinall = np.unique(np.r_[tbinq,tbinr1])
            else:
                tbinall = np.unique(np.r_[tbinq,tbinr1,tbinr2])
            tall = np.r_[tbinall[0] - 0.5*(tbinall[1]-tbinall[0]),
                         0.5*(tbinall[1:]+tbinall[:-1]),
                         tbinall[-1] + 0.5*(tbinall[-1]-tbinall[-2])]

        # Get indtqr1r2 (tall with respect to tq, tr1, tr2)
        indtq, indtr1, indtr2 = None, None, None
        indtq = np.digitize(tall, tbinq)
        if idref1d is None:
            assert np.all(indtq == np.arange(0,tall.size))
        if idref1d is not None:
            indtr1 = np.digitize(tall, tbinr1)
        if idref2d is not None:
            indtr2 = np.digitize(tall, tbinr2)

        ntall = tall.size
        return tall, tbinall, ntall, indtq, indtr1, indtr2

    @staticmethod
    def _get_indtu(t=None, tall=None, tbinall=None,
                   idref1d=None, idref2d=None,
                   indtr1=None, indtr2=None):
        # Get indt (t with respect to tbinall)
        indt, indtu = None, None
        if t is not None:
            indt = np.digitize(t, tbinall)
            indtu = np.unique(indt)

            # Update
            tall = tall[indtu]
            if idref1d is not None:
                assert indtr1 is not None
                indtr1 = indtr1[indtu]
            if idref2d is not None:
                assert indtr2 is not None
                indtr2 = indtr2[indtu]
        ntall = tall.size
        return tall, ntall, indt, indtu, indtr1, indtr2

    def get_tcommon(self, lq, prefer='finer'):
        """ Check if common t, else choose according to prefer

        By default, prefer the finer time resolution

        """
        if type(lq) is str:
            lq = [lq]
        t = []
        for qq in lq:
            ltr = [kk for kk in self._ddata[qq]['depend']
                   if self._dindref[kk]['group'] == 'time']
            assert len(ltr) <= 1
            if len(ltr) > 0 and ltr[0] not in t:
                t.append(ltr[0])
        assert len(t) >= 1
        if len(t) > 1:
            dt = [np.nanmean(np.diff(self._ddata[tt]['data'])) for tt in t]
            if prefer == 'finer':
                ind = np.argmin(dt)
            else:
                ind = np.argmax(dt)
        else:
            ind = 0
        return t[ind], t

    def _get_tcom(self, idquant=None, idref1d=None,
                  idref2d=None, idq2dR=None):
        if idquant is not None:
            out = self._get_indtmult(idquant=idquant,
                                     idref1d=idref1d, idref2d=idref2d)
        else:
            out = self._get_indtmult(idquant=idq2dR)
        return out


    def _get_finterp(self,
                     idquant=None, idref1d=None, idref2d=None,
                     idq2dR=None, idq2dPhi=None, idq2dZ=None,
                     interp_t='nearest', interp_space=None,
                     fill_value=np.nan, ani=False, Type=None):

        # Get idmesh
        if idquant is not None:
            if idref1d is None:
                lidmesh = [qq for qq in self._ddata[idquant]['depend']
                           if self._dindref[qq]['group'] == 'mesh']
            else:
                lidmesh = [qq for qq in self._ddata[idref2d]['depend']
                           if self._dindref[qq]['group'] == 'mesh']
        else:
            assert idq2dR is not None
            lidmesh = [qq for qq in self._ddata[idq2dR]['depend']
                       if self._dindref[qq]['group'] == 'mesh']
        assert len(lidmesh) == 1
        idmesh = lidmesh[0]

        # Get mesh
        mpltri = self._ddata[idmesh]['data']['mpltri']
        trifind = mpltri.get_trifinder()

        # Get common time indices
        if interp_t == 'nearest':
             out = self._get_tcom(idquant,idref1d, idref2d, idq2dR)
             tall, tbinall, ntall, indtq, indtr1, indtr2= out

        # # Prepare output

        # Interpolate
        # Note : Maybe consider using scipy.LinearNDInterpolator ?
        if idquant is not None:
            vquant = self._ddata[idquant]['data']
            if self._ddata[idmesh]['data']['ntri'] > 1:
                vquant = np.repeat(vquant,
                                   self._ddata[idmesh]['data']['ntri'], axis=0)
        else:
            vq2dR   = self._ddata[idq2dR]['data']
            vq2dPhi = self._ddata[idq2dPhi]['data']
            vq2dZ   = self._ddata[idq2dZ]['data']

        if interp_space is None:
            interp_space = self._ddata[idmesh]['data']['ftype']

        # get interpolation function
        if ani:
            # Assuming same mesh and time vector for all 3 components
            func = _comp.get_finterp_ani(self, idq2dR, idq2dPhi, idq2dZ,
                                         interp_t=interp_t,
                                         interp_space=interp_space,
                                         fill_value=fill_value,
                                         idmesh=idmesh, vq2dR=vq2dR,
                                         vq2dZ=vq2dZ, vq2dPhi=vq2dPhi,
                                         tall=tall, tbinall=tbinall,
                                         ntall=ntall,
                                         indtq=indtq, trifind=trifind,
                                         Type=Type, mpltri=mpltri)
        else:
            func = _comp.get_finterp_isotropic(self, idquant, idref1d, idref2d,
                                               interp_t=interp_t,
                                               interp_space=interp_space,
                                               fill_value=fill_value,
                                               idmesh=idmesh, vquant=vquant,
                                               tall=tall, tbinall=tbinall,
                                               ntall=ntall, mpltri=mpltri,
                                               indtq=indtq, indtr1=indtr1,
                                               indtr2=indtr2, trifind=trifind)


        return func


    def _checkformat_qr12RPZ(self, quant=None, ref1d=None, ref2d=None,
                             q2dR=None, q2dPhi=None, q2dZ=None):
        lc0 = [quant is None, ref1d is None, ref2d is None]
        lc1 = [q2dR is None, q2dPhi is None, q2dZ is None]
        if np.sum([all(lc0), all(lc1)]) != 1:
            msg = "Please provide either (xor):\n"
            msg += "    - a scalar field (isotropic emissivity):\n"
            msg += "        quant : scalar quantity to interpolate\n"
            msg += "                if quant is 1d, intermediate reference\n"
            msg += "                fields are necessary for 2d interpolation\n"
            msg += "        ref1d : 1d reference field on which to interpolate\n"
            msg += "        ref2d : 2d reference field on which to interpolate\n"
            msg += "    - a vector (R,Phi,Z) field (anisotropic emissivity):\n"
            msg += "        q2dR :  R component of the vector field\n"
            msg += "        q2dPhi: R component of the vector field\n"
            msg += "        q2dZ :  Z component of the vector field\n"
            msg += "        => all components have teh same time and mesh !\n"
            raise Exception(msg)

        # Check requested quant is available in 2d or 1d
        if all(lc1):
            idquant, idref1d, idref2d = self._get_quantrefkeys(quant, ref1d, ref2d)
            idq2dR, idq2dPhi, idq2dZ = None, None, None
            ani = False
        else:
            idq2dR, msg   = self._get_keyingroup(q2dR, 'mesh', msgstr='quant',
                                              raise_=True)
            idq2dPhi, msg = self._get_keyingroup(q2dPhi, 'mesh', msgstr='quant',
                                              raise_=True)
            idq2dZ, msg   = self._get_keyingroup(q2dZ, 'mesh', msgstr='quant',
                                              raise_=True)
            idquant, idref1d, idref2d = None, None, None
            ani = True
        return idquant, idref1d, idref2d, idq2dR, idq2dPhi, idq2dZ, ani


    def get_finterp2d(self, quant=None, ref1d=None, ref2d=None,
                      q2dR=None, q2dPhi=None, q2dZ=None,
                      interp_t=None, interp_space=None,
                      fill_value=np.nan, Type=None):
        """ Return the function interpolating (X,Y,Z) pts on a 1d/2d profile

        Can be used as input for tf.geom.CamLOS1D/2D.calc_signal()

        """
        # Check inputs
        msg = "Only 'nearest' available so far for interp_t!"
        assert interp_t == 'nearest', msg
        out = self._checkformat_qr12RPZ(quant=quant, ref1d=ref1d, ref2d=ref2d,
                                        q2dR=q2dR, q2dPhi=q2dPhi, q2dZ=q2dZ)
        idquant, idref1d, idref2d, idq2dR, idq2dPhi, idq2dZ, ani = out


        # Interpolation (including time broadcasting)
        func = self._get_finterp(idquant=idquant, idref1d=idref1d,
                                 idref2d=idref2d, idq2dR=idq2dR,
                                 idq2dPhi=idq2dPhi, idq2dZ=idq2dZ,
                                 interp_t=interp_t, interp_space=interp_space,
                                 fill_value=fill_value, ani=ani, Type=Type)
        return func


    def interp_pts2profile(self, pts=None, vect=None, t=None,
                           quant=None, ref1d=None, ref2d=None,
                           q2dR=None, q2dPhi=None, q2dZ=None,
                           interp_t=None, interp_space=None,
                           fill_value=np.nan, Type=None):
        """ Return the value of the desired profiles_1d quantity

        For the desired inputs points (pts):
            - pts are in (R,Z) coordinates
            - space interpolation is linear on the 1d profiles
        At the desired input times (t):
            - using a nearest-neighbourg approach for time

        """
        # Check inputs
        # msg = "Only 'nearest' available so far for interp_t!"
        # assert interp_t == 'nearest', msg

        # Check requested quant is available in 2d or 1d
        out = self._checkformat_qr12RPZ(quant=quant, ref1d=ref1d, ref2d=ref2d,
                                        q2dR=q2dR, q2dPhi=q2dPhi, q2dZ=q2dZ)
        idquant, idref1d, idref2d, idq2dR, idq2dPhi, idq2dZ, ani = out

        # Check the pts is (2,...) array of floats
        if pts is None:
            if ani:
                idmesh = [id_ for id_ in self._ddata[idq2dR]['depend']
                          if self._dindref[id_]['group'] == 'mesh'][0]
            else:
                if idref1d is None:
                    idmesh = [id_ for id_ in self._ddata[idquant]['depend']
                              if self._dindref[id_]['group'] == 'mesh'][0]
                else:
                    idmesh = [id_ for id_ in self._ddata[idref2d]['depend']
                              if self._dindref[id_]['group'] == 'mesh'][0]
            pts = self.dmesh[idmesh]['data']['nodes']
            pts = np.array([pts[:,0], np.zeros((pts.shape[0],)), pts[:,1]])

        pts = np.atleast_2d(pts)
        if pts.shape[0] != 3:
            msg = "pts must be np.ndarray of (X,Y,Z) points coordinates\n"
            msg += "Can be multi-dimensional, but the 1st dimension is (X,Y,Z)\n"
            msg += "    - Expected shape : (3,...)\n"
            msg += "    - Provided shape : %s"%str(pts.shape)
            raise Exception(msg)

        # Check t
        lc = [t is None, type(t) is str, type(t) is np.ndarray]
        assert any(lc)
        if lc[1]:
            assert t in self._ddata.keys()
            t = self._ddata[t]['data']

        # Interpolation (including time broadcasting)
        # this is the second slowest step (~0.08 s)
        func = self._get_finterp(idquant=idquant, idref1d=idref1d, idref2d=idref2d,
                                 idq2dR=idq2dR, idq2dPhi=idq2dPhi, idq2dZ=idq2dZ,
                                 interp_t=interp_t, interp_space=interp_space,
                                 fill_value=fill_value, ani=ani, Type=Type)

        # This is the slowest step (~1.8 s)
        val, t = func(pts, vect=vect, t=t)
        return val, t


    def calc_signal_from_Cam(self, cam, t=None,
                             quant=None, ref1d=None, ref2d=None,
                             q2dR=None, q2dPhi=None, q2dZ=None,
                             Brightness=True, interp_t=None,
                             interp_space=None, fill_value=np.nan,
                             res=0.005, DL=None, resMode='abs', method='sum',
                             ind=None, out=object, plot=True, dataname=None,
                             fs=None, dmargin=None, wintit=None, invert=True,
                             units=None, draw=True, connect=True):

        if 'Cam' not in cam.__class__.__name__:
            msg = "Arg cam must be tofu Camera instance (CamLOS1D, CamLOS2D...)"
            raise Exception(msg)

        return cam.calc_signal_from_Plasma2D(self, t=t,
                                             quant=quant, ref1d=ref1d, ref2d=ref2d,
                                             q2dR=q2dR, q2dPhi=q2dPhi,
                                             q2dZ=q2dZ,
                                             Brightness=Brightness,
                                             interp_t=interp_t,
                                             interp_space=interp_space,
                                             fill_value=fill_value, res=res,
                                             DL=DL, resMode=resMode,
                                             method=method, ind=ind, out=out,
                                             pot=plot, dataname=dataname,
                                             fs=fs, dmargin=dmargin,
                                             wintit=wintit, invert=intert,
                                             units=units, draw=draw,
                                             connect=connect)


    #---------------------
    # Methods for getting data
    #---------------------

    def get_dextra(self, dextra=None):
        lc = [dextra is None, dextra == 'all', type(dextra) is dict,
              type(dextra) is str, type(dextra) is list]
        assert any(lc)
        if dextra is None:
            dextra = {}

        if dextra == 'all':
            dextra = [k for k in self._dgroup['time']['ldata']
                      if (self._ddata[k]['lgroup'] == ['time']
                          and k not in self._dindref.keys())]

        if type(dextra) is str:
            dextra = [dextra]

        # get data
        if type(dextra) is list:
            for ii in range(0,len(dextra)):
                if type(dextra[ii]) is tuple:
                    ee, cc = dextra[ii]
                else:
                    ee, cc = dextra[ii], None
                ee, msg = self._get_keyingroup(ee, 'time', raise_=True)
                if self._ddata[ee]['lgroup'] != ['time']:
                    msg = "time-only dependent signals allowed in dextra!\n"
                    msg += "    - %s : %s"%(ee,str(self._ddata[ee]['lgroup']))
                    raise Exception(msg)
                idt = self._ddata[ee]['depend'][0]
                key = 'data' if self._ddata[ee]['data'].ndim == 1 else 'data2D'
                dd = {key: self._ddata[ee]['data'],
                      't': self._ddata[idt]['data'],
                      'label': self._ddata[ee]['name'],
                      'units': self._ddata[ee]['units']}
                if cc is not None:
                    dd['c'] = cc
                dextra[ii] = (ee, dd)
            dextra = dict(dextra)
        return dextra

    def get_Data(self, lquant, X=None, ref1d=None, ref2d=None,
                 remap=False, res=0.01, interp_space=None, dextra=None):

        try:
            import tofu.data as tfd
        except Exception:
            from .. import data as tfd

        # Check and format input
        assert type(lquant) in [str,list]
        if type(lquant) is str:
            lquant = [lquant]
        nquant = len(lquant)

        # Get X if common
        c0 = type(X) is str
        c1 = type(X) is list and (len(X) == 1 or len(X) == nquant)
        if not (c0 or c1):
            msg = "X must be specified, either as :\n"
            msg += "    - a str (name or quant)\n"
            msg += "    - a list of str\n"
            msg += "    Provided: %s"%str(X)
            raise Exception(msg)
        if c1 and len(X) == 1:
            X = X[0]

        if type(X) is str:
            idX, msg = self._get_keyingroup(X, 'radius', msgstr='X', raise_=True)

        # prepare remap pts
        if remap:
            assert self.config is not None
            refS = list(self.config.dStruct['dObj']['Ves'].values())[0]
            ptsRZ, x1, x2, extent = refS.get_sampleCross(res, mode='imshow')
            dmap = {'t':None, 'data2D':None, 'extent':extent}
            if ref is None and X in self._lquantboth:
                ref = X

        # Define Data
        dcommon = dict(Exp=self.Id.Exp, shot=self.Id.shot,
                       Diag='profiles1d', config=self.config)

        # dextra
        dextra = self.get_dextra(dextra)

        # Get output
        lout = [None for qq in lquant]
        for ii in range(0,nquant):
            qq = lquant[ii]
            if remap:
                # Check requested quant is available in 2d or 1d
                idq, idrefd1, idref2d = self._get_quantrefkeys(qq, ref1d, ref2d)
            else:
                idq, msg = self._get_keyingroup(qq, 'radius',
                                                msgstr='quant', raise_=True)
            if idq not in self._dgroup['radius']['ldata']:
                msg = "Only 1d quantities can be turned into tf.data.Data !\n"
                msg += "    - %s is not a radius-dependent quantity"%qq
                raise Exception(msg)
            idt = self._ddata[idq]['depend'][0]

            if type(X) is list:
                idX, msg = self._get_keyingroup(X[ii], 'radius',
                                                msgstr='X', raise_=True)

            dlabels = {'data':{'name': self._ddata[idq]['name'],
                               'units': self._ddata[idq]['units']},
                       'X':{'name': self._ddata[idX]['name'],
                            'units': self._ddata[idX]['units']},
                       't':{'name': self._ddata[idt]['name'],
                            'units': self._ddata[idt]['units']}}

            dextra_ = dict(dextra)
            if remap:
                dmapii = dict(dmap)
                val, tii = self.interp_pts2profile(qq, ptsRZ=ptsRZ, ref=ref,
                                                   interp_space=interp_space)
                dmapii['data2D'], dmapii['t'] = val, tii
                dextra_['map'] = dmapii
            lout[ii] = DataCam1D(Name = qq,
                                 data = self._ddata[idq]['data'],
                                 t = self._ddata[idt]['data'],
                                 X = self._ddata[idX]['data'],
                                 dextra = dextra_, dlabels=dlabels, **dcommon)
        if nquant == 1:
            lout = lout[0]
        return lout


    #---------------------
    # Methods for plotting data
    #---------------------

    def plot(self, lquant, X=None,
             ref1d=None, ref2d=None,
             remap=False, res=0.01, interp_space=None,
             sharex=False, bck=True):
        lDat = self.get_Data(lquant, X=X, remap=remap,
                             ref1d=ref1d, ref2d=ref2d,
                             res=res, interp_space=interp_space)
        if type(lDat) is list:
            kh = lDat[0].plot_combine(lDat[1:], sharex=sharex, bck=bck)
        else:
            kh = lDat.plot(bck=bck)
        return kh

    def plot_combine(self, lquant, lData=None, X=None,
                     ref1d=None, ref2d=None,
                     remap=False, res=0.01, interp_space=None,
                     sharex=False, bck=True):
        """ plot combining several quantities from the Plasma2D itself and
        optional extra list of Data instances """
        lDat = self.get_Data(lquant, X=X, remap=remap,
                             ref1d=ref1d, ref2d=ref2d,
                             res=res, interp_space=interp_space)
        if lData is not None:
            if type(lDat) is list:
                lData = lDat[1:] + lData
            else:
                lData = lDat[1:] + [lData]
        kh = lDat[0].plot_combine(lData, sharex=sharex, bck=bck)
        return kh
