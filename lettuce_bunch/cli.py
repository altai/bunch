#!/usr/bin/env python

import sys
import os
from optparse import OptionParser
from lettuce_bunch.core import SerialBunchRunner, Bunch
from lettuce_bunch import version
from lettuce_bunch.plugins import plugins_list
from lettuce_bunch.plugins.base import parse_plugin_params


def main():

    def derive_base_dir(path):
        if os.path.isabs(path):
            return path
        return os.path.abspath(path)

    parser = OptionParser(usage="lettuce_bunch [OPTION]... BUNCH_DIR... RESULT_DIR",
                          version=version)
    parser.add_option("-c", "--config", action="store", type="string",
                      dest="config", default='config.yaml', metavar="FILE",
                      help="YAML config file")
    parser.add_option("-b", "--bunch-concurency",  action="store", type="string",
                      dest="concurrency", default='serial',
                      help="This option indicates test execution parallelism", metavar="CONCURRENCY_TYPE")
    parser.add_option("-e", "--environment",  action="store", type="string",
                      dest="environment",
                      help="This option indicates type of test fixtures intended for environment NAME", metavar="NAME")
    parser.add_option("-o", "--output-plugin",  action="store", type="choice",
        default=None,
        choices=plugins_list(),
        help="Output plugin for test results", metavar="PLUGIN")
    parser.add_option("-p", "--plugin-params",
        action="callback",
        callback=parse_plugin_params,
        type="string",
        default=None,
        help='Semicolon separated list of parameters to output plugin: "param1=val1;param2=val2;..."', metavar="PARAMS")

    (options, args) = parser.parse_args()

    if len(args) <= 1:  parser.print_help(); sys.exit(2)
    output_dir_arg = args[-1]
    bunch_dir_args = args[:-1]


    config_file_name = derive_base_dir(options.config)
    concurrency = options.concurrency
    output_dir = derive_base_dir(output_dir_arg)
    bunch_dirs = map(derive_base_dir, bunch_dir_args)

    # Options are parsed let's personalize test scenarios
    bunch_list = []
    for item in bunch_dirs:
        bunch = Bunch(item, output_dir, config_file_name)
        bunch.deploy()
        bunch.personalize()
        bunch_list.append(bunch)

    def filter_args_for_lettuce(arg):
        if arg in parser._long_opt  or arg in parser._short_opt:
            return False

        for opt in parser._long_opt:
            if str(arg).startswith(opt):
                return False

        for opt in parser._short_opt:
            if str(arg).startswith(opt):
                return False

        if arg in [options.config, options.concurrency, options.environment]:
            return False

        if arg in bunch_dir_args:
            return False

        if arg == output_dir_arg:
                return False

        if arg == "--with-xunit" or str(arg).startswith("--xunit-file"):
            return False

        return True

    args = filter(filter_args_for_lettuce, sys.argv)
    none_failed = SerialBunchRunner(bunch_list, args,
        env_name=options.environment,
        plugin=options.output_plugin,
        plugin_params=options.plugin_params
    ).run()

    if not none_failed:
        sys.exit(2)



if __name__ == '__main__':
    main()


  