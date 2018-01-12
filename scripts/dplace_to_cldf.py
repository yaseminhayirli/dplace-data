#!/usr/bin/env python
# dplase_to_cldf.py - convert all dplace datasets to cldf copying from pydplace to pycldf

from __future__ import unicode_literals

import os
import copy
import collections
try:
    from itertools import imap as map
except ImportError:
    map = map

import attr
import pycldf

import pydplace.api

SOURCE, TARGET = '..', '../cldf'

CONVERTERS = []

CLDF = 'http://cldf.clld.org/v1.0/terms.rdf#'


def register(cls):
    """Register an instance of the decorated converter class for execution.

    Args:
        cls (BaseConverter): class whose instances will be called.

    cls()(<pydplace.api.Dataset instance>) returns an (add_component_args, write_kwargs) tuple.
    """
    assert issubclass(cls, BaseConverter)
    inst = cls()
    assert callable(inst)
    CONVERTERS.append(inst)
    return cls


class BaseConverter(object):

    def skip(self, dataset):
        return False


Separator = collections.namedtuple('Separator', ['sep', 'split'])


class Converter(BaseConverter):

    def __init__(self):
        fields = attr.fields(self._source_cls)
        columns = list(self._itercols(fields, self._convert))

        def extract(s):
            return {target: trans(getattr(s, name))
                    for name, trans, target, _ in columns}

        self._extract = extract
        self._add_component_args = ([self._component] +
                                    [args for _, _, _, args in columns])

    @staticmethod
    def _itercols(fields, convert):
        for f in fields:
            name = f.name
            if name in convert:
                args = convert[name]
                if args is None:
                    continue
                elif hasattr(args, 'setdefault'):
                    target = args.setdefault('name', name)
                else:
                    target = args
                    args = {'name': target}
            else:
                args = {'name': name}
                target = name

            transform = lambda x: x
            if 'separator' in args:
                sep, split = args['separator']
                args['separator'] = sep
                if split:
                    transform = lambda x: x.split(sep)

            if 'datatype' not in args:
                args['datatype'] = 'float' if f.convert is float else 'string'

            yield name, transform, target, args

    def __call__(self, dataset):
        component = self._component.get('dc:conformsTo', self._component['url'])
        items = map(self._extract, self._iterdata(dataset))
        write_kwargs = {component: items}
        return self._add_component_args, write_kwargs


class SkipMixin(object):

    @classmethod
    def skip(cls, dataset, _sentinel=object()):
        return next(iter(cls._iterdata(dataset)), _sentinel) is _sentinel


@register
class LanguageTable(SkipMixin, Converter):

    _source_cls = pydplace.api.Society

    _iterdata = staticmethod(lambda dataset: dataset.societies)

    _component = {
        'url': 'societies.csv',
        'dc:conformsTo': 'http://cldf.clld.org/v1.0/terms.rdf#LanguageTable',
        'tableSchema': {'primaryKey': ['id']},
    }

    _convert = {
        'id': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id',
            'required': True,
        },
        'xd_id': {
            'required': True,
            'datatype': {'base': 'string', 'format': r'xd\d+'},
        },
        'pref_name_for_society': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#name',
            'required': True,
        },
        'glottocode': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#glottocode',
            'required': True,
        },
        'ORIG_name_and_ID_in_this_dataset': {
            'required': True,
        },
        'alt_names_by_society': {
            'separator': Separator(', ', split=True)
        },
        'main_focal_year': {
            'datatype': 'integer',
            'null': 'NA',
        },
        'HRAF_name_ID': {
            'datatype': {'base': 'string', 'format': r'.+ \([^)]+\)'},
        },
        'HRAF_link': {
            'datatype': {'base': 'string', 'format': r'http://.+|in process'},
        },
        'origLat': {
            'datatype': {'base': 'decimal', 'minimum': -90, 'maximum': 90},
            'required': True,
        },
        'origLong': {  # FIXME: EA/societies.csv:1279:11
            'datatype': {'base': 'decimal', 'minimum': -190, 'maximum': 180},
            'required': True,
        },
        'Lat': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#latitude',
            'datatype': {'base': 'decimal', 'minimum': -90, 'maximum': 90},
            'required': True,
        },
        'Long': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#longitude',
            'datatype': {'base': 'decimal', 'minimum': -180, 'maximum': 180},
            'required': True,
        },
        'Comment': {'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#comment'},
    }


@register
class LangugageRelatedTable(SkipMixin, Converter):

    _source_cls = pydplace.api.RelatedSocieties

    _iterdata = staticmethod(lambda dataset: dataset.society_relations)

    _component = {
        'url': 'societies_mapping.csv',
        'tableSchema': {
            'primaryKey': ['id'],
            'foreignKeys': [
                {'columnReference': 'id',
                'reference': {'resource': 'societies.csv', 'columnReference': 'id'}},
            ],
        },
    }

    _convert = {
        'id': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id',
            'required': True,
        },
        'related': {
            'separator': Separator('; ', split=False),
        },
    }


@register
class ParameterTable(Converter):

    _source_cls = pydplace.api.Variable

    _iterdata = staticmethod(lambda dataset: dataset.variables)

    _component = {
        'url': 'variables.csv',
        'dc:conformsTo': 'http://cldf.clld.org/v1.0/terms.rdf#ParameterTable',
        'tableSchema': {'primaryKey': ['id']}
    }

    _convert = {
        'id': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id',
            'required': True,
        },
        'category': {
            'separator': Separator(', ', split=False),
            'required': True,
        },
        'title': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#name',
            'required': True,
        },
        'definition': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#description',
        },
        'type': {
            'datatype': {
                'base': 'string',
                'format': r'Categorical|Ordinal|Continuous',
            },
            'required': True,
        },
        'source': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#source',
        },
        'notes': {'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#comment'},
        'codes': None,
    }


@register
class CodeTable(SkipMixin, BaseConverter):

    _iterdata = staticmethod(lambda dataset: (c for v in dataset.variables for c in v.codes))

    _component = {
        'url': 'codes.csv',
        'dc:conformsTo': 'http://cldf.clld.org/v1.0/terms.rdf#CodeTable',
        'tableSchema': {
            'primaryKey': ['var_id', 'code'],
            'foreignKeys': [
                {'columnReference': 'var_id',
                'reference': {'resource': 'variables.csv', 'columnReference': 'id'}},
            ],
        },
    }

    _convert = {
        'var_id': {
            'name': 'var_id',
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#parameterReference',
            'required': True,
        },
        'code': {
            'name': 'code',  # FIXME: MODIS/data.csv:5884:6
            'datatype': {'base': 'string', 'format': r'-?\d+(?:.\d+)?(?:E[+-]\d+)?|NA'},
            'required': True,
        },
        'description': {
            'name': 'description',
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#description',
        },
        'name': {
            'name': 'name',
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#name',
            'required': True,
        },
    }

    def __call__(self, dataset):
        codes = list(self._iterdata(dataset))
        add_component_args = ([self._component] +
                              [self._convert.get(f, f) for f in codes[0]._fields])
        component = self._component.get('dc:conformsTo', self._component['url'])
        items = (c._asdict() for c in codes)
        write_kwargs = {component: items}
        return add_component_args, write_kwargs


@register
class ValueTable(Converter):

    _source_cls = pydplace.api.Data

    _iterdata = staticmethod(lambda dataset: dataset.data)

    _component = {
        'url': 'data.csv',
        'dc:conformsTo': 'http://cldf.clld.org/v1.0/terms.rdf#ValueTable',
        'tableSchema': {
            'primaryKey': 'id',
            #'primaryKey': ['soc_id', 'sub_case', 'year', 'var_id', 'code', 'references'],
            'foreignKeys': [
                {'columnReference': 'soc_id',
                'reference': {'resource': 'societies.csv', 'columnReference': 'id'}},
                #{'columnReference': ['var_id', 'code'],
                #'reference': {'resource': 'codes.csv', 'columnReference': ['var_id', 'code']}},
            ],
        },
    }

    _extra = {
        'name': 'id',
        'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id',
        'required': True,
    }

    _convert = {
        'soc_id': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#languageReference',
            'required': True,
        },
        'sub_case': {
            'null': None,
            'required': True,
        },
        'year': {
            'datatype': {'base': 'string', 'format': r'-?\d+(?:-\d+)?|(?:NA)?'},
            'null': None,
            'required': True,
        },
        'var_id': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#parameterReference',
            'required': True,
        },
        'code': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#codeReference',
            'datatype': CodeTable._convert['code']['datatype'],
            'required': True,
        },
        'comment': {'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#comment'},
        'references': {
            'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#source',
            'separator': Separator('; ', split=False),
            'null': None,
            'required': True,
        },
    }

    def __call__(self, dataset):
        component = self._add_component_args[0]
        if LanguageTable.skip(dataset):  # drop data.csv fks to societies.csv if there is none
            component = copy.deepcopy(component)
            reduced = [f for f in component['tableSchema']['foreignKeys']
                       if f['reference']['resource'] != LanguageTable._component['url']]
            component['tableSchema']['foreignKeys'] = reduced
        add_component_args = [component, self._extra] + self._add_component_args[1:]

        def extract_add_id(d, i, _extract=self._extract):
            result = _extract(d)
            result['id'] = i
            return result

        component = self._component.get('dc:conformsTo', self._component['url'])
        items = (extract_add_id(d, i) for i, d in enumerate(self._iterdata(dataset), 1))
        write_kwargs = {component: items}
        return add_component_args, write_kwargs


def main(source_dir=SOURCE, target_dir=TARGET, converters=CONVERTERS):
    """Write pydplace.api.Datasets in ``source_dir`` to pycldf.StructureDatasets in ``target_dir``."""
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    repo = pydplace.api.Repos(source_dir)
    for source_ds in repo.datasets:
        print(source_ds)
        target_dir = os.path.join(target_dir, source_ds.id)
        target_ds = pycldf.StructureDataset.in_dir(target_dir, empty_tables=True)
        write_kwargs = {}
        for c in converters:
            if not c.skip(source_ds):
                add_args, _write_kwargs = c(source_ds)
                target_ds.add_component(*add_args)
                write_kwargs.update(_write_kwargs)
        target_ds.write(**write_kwargs)
        target_ds.validate()


if __name__ == '__main__':
    main()
