import lettuce_bunch.plugins.base
import lettuce_bunch.reports as reports
import os
from jinja2 import Template
from os.path import join, abspath, dirname, exists
from urllib import pathname2url
from jinja2 import FileSystemLoader
from jinja2.environment import Environment
from shutil import copytree, copy
from datetime import datetime
import yaml
import anyjson

PLUGIN_PAGE_TEMPLATE = "bootstrap/layouts/checklist.html"
PLUGIN_SITE_INDEX_TEMPLATE = "bootstrap/layouts/index.html"

class HtmlSite(object):
    STATIC = 'static'
    TEMPLATES = 'templates'
    #INDEX_EJS = join(STATIC, 'js', '')

    def __init__(self, root=None, dst=None):
        self.root = root if root is not None else self.bootstrap_package_root()
        self.dst = root if dst is None else dst

    @classmethod
    def bootstrap_package_root(cls):
        return dirname(abspath(reports.__file__))

    @classmethod
    def denormalize_path(cls, path):
        if os.altsep is not None:
            path  = path.replace(os.sep, os.altsep)
        return path

    @classmethod
    def normalize_path(cls, path):
        if os.altsep is not None:
            path  = path.replace(os.altsep, os.sep)
        return path

    def __get_item_location(self, relative_path):
        return join(self.root, relative_path)


    def __get_bootstrap_static_url(self):
        return 'file:' + pathname2url(self.__get_item_location(HtmlSite.STATIC)) + "/"

    def __get_bootstrap_templates_root(self):
        return self.denormalize_path(self.__get_item_location(HtmlSite.TEMPLATES))

    def __get_templates_item(self, item_relative_path):
        return self.denormalize_path(join(self.__get_bootstrap_templates_root(), item_relative_path))

    @classmethod
    def write_html_result(cls, html, dst):
        with open(dst, 'w') as f:
            f.write(html)

    def __static_files(self):
        return join(self.dst, HtmlSite.STATIC)

    def __check_static_deployed(self):
        if not exists(self.__static_files()):
            copytree(self.__get_item_location(HtmlSite.STATIC), self.__static_files())

    def __relative_url_for_statics(self):
        return './' + HtmlSite.STATIC + '/'

    def __report_filename(self, dt):
        return 'report-%s.html' % dt.strftime("%y-%m-%dT%H-%M-%S-%f")

    def generate(self, page_template, index_template, vars):
        self.__check_static_deployed()
        html = self.render(page_template, vars, self.__relative_url_for_statics())
        dt = datetime.now()
        report_filename = self.__report_filename(dt)
        dst_file = join(self.dst, report_filename)
        self.write_html_result(html, dst_file)
        self.__update_json(report_filename, vars['name'], dt, vars['description'])
        self.__check_index(index_template, vars)

    def __index_filename(self):
        return join(self.dst, 'index.html')

    def __index_ejs(self):
        return join(self.dst, 'index.ejs')

    def __json_data_file(self):
        return join(self.dst, 'data.json')

    def __read_json(self):
        json_data = {'bunches' : []}
        if exists(self.__json_data_file()):
            with open(self.__json_data_file(), 'r') as f:
                json_data = anyjson.deserialize(f.read())

        return json_data

    def __write_json(self, data):
        with open(self.__json_data_file(), 'w') as f:
            f.write(anyjson.serialize(data))

    def __update_json(self, report_filename, name, date, description):
        data = self.__read_json()
        bunches = data['bunches']
        bunches.append({   'page'  : './' + report_filename,
                        'name'  : name,
                        'date'  : date.isoformat(),
                        'description' : description})
        self.__write_json(data)

    def render(self, template_location, vars, static_url):
        internal = dict({'STATIC_URL': static_url})
        vars.update(internal)
        template_location = self.denormalize_path(template_location)
        env = Environment()
        env.loader = FileSystemLoader(self.__get_bootstrap_templates_root())
        tmpl = env.get_template(template_location)
        html = tmpl.render(**vars)
        return html

    def __check_index(self, index_template, vars):
        if not exists(self.__index_filename()):
            index_html = self.render(index_template, vars, self.__relative_url_for_statics())
            self.write_html_result(index_html, self.__index_filename())


class OutputPlugin(lettuce_bunch.plugins.base.BaseOutputPlugin):
    def __init__(self, **kw):
        self.bootstrap = kw['bootstrap'] if 'bootstrap' in kw else None

        super(OutputPlugin,self).__init__(**kw)

    def __get_common_props(self, dict, item):
        common_attrs = ['started', 'finished', 'time', 'result']
        for attr in common_attrs:
            rez = item.find(attr)
            dict[attr] = rez.text if rez is not None else ""

    def __get_item_text(self, item, path):
        rez = item.find(path)
        return rez.text if rez is not None else ""

    def __get_prop_text(self, item, prop_name):
        return self.__get_item_text(item, 'properties/' + prop_name)

    def __parse_xml_list(self, xml_list):
        items = []
        rez = xml_list.findall('item/itemvalue')
        if rez:
            items.extend(rez)
        return items

    def __parse_xml_dict(self, xml_dict):
        rez_dict = dict()
        items = xml_dict.findall('item')
        for item in items:
            rez_dict[item.find('key')] = item.find('value')

        return rez_dict


    def __parse_hashes(self, step_xml):
        rez = step_xml.findall('properties/hashes')
        hashes = []
        for item in rez:
            hashes.extend(map(self.__parse_xml_dict, self.__parse_xml_list(item)))

        return hashes

    def __parse_steps(self, steps_xml):
        steps_list = []
        for step in steps_xml:
            step_props = dict()
            self.__get_common_props(step_props, step)
            step_props['name'] = self.__get_prop_text(step, 'original_sentence')
            step_props['hashes'] = self.__parse_hashes(step)
            steps_list.append(step_props)

        return steps_list

    def __parse_outlines(self, outlines_xml):
        outlines_list = []
        for outline in outlines_xml:
            outline_props = dict()
            self.__get_common_props(outline_props , outline)
            outlines_list.append(outline_props)
        return outlines_list

    def __parse_scenarios(self, scenarios_xml):
        scenario_list = []
        for scenario in scenarios_xml:
            scenario_props = dict()
            scenario_props['steps'] = self.__parse_steps(scenario.iterfind("steps/step"))
            scenario_props['outlines'] = self.__parse_outlines(scenario.iterfind("outlines/outline"))
            self.__get_common_props(scenario_props, scenario)
            scenario_props['name']= self.__get_prop_text(scenario, 'name')
            scenario_list.append(scenario_props)

        return scenario_list

    def __parse_features(self, features_xml):
        featured_list = []
        for feature_item in features_xml:
            feature_props = dict()
            feature_props['scenarios'] = self.__parse_scenarios(feature_item.iterfind("scenarios/scenario"))
            self.__get_common_props(feature_props, feature_item)
            feature_props['name'] = self.__get_prop_text(feature_item, 'name')
            feature_props['description'] = self.__get_prop_text(feature_item, 'description')

            featured_list.append(feature_props)

        return featured_list

    def __ensure_dst_exists(self):
        if not exists(self.dst_dir):
            os.mkdir(self.dst_dir)

    def transform(self, et, details):
        features_list = self.__parse_features(et.iterfind("feature"))
        data = {'name' : details.name, 'description' : details.description, 'features' : features_list}
        self.__ensure_dst_exists()
        site = HtmlSite(self.bootstrap, dst=self.dst_dir)
        #debug
        with open(join(self.dst_dir, 'dump.yaml'), 'w') as f:
            f.write(yaml.dump(data, default_flow_style=False))

        site.generate(PLUGIN_PAGE_TEMPLATE, PLUGIN_SITE_INDEX_TEMPLATE, data)


        


