#!/usr/bin/env python

import logging
import pprint
import argparse
import yaml
import re
import sys
import difflib
import os
from clang.cindex import Index
from clang.cindex import CompilationDatabase
from clang.cindex import CursorKind


class Rule(object):
    def __init__(self, clang_kind_str, parent_kind=None, help="", pattern_str='^.*$'):
        self.clang_kind_str = clang_kind_str
        self.parent_kind = parent_kind
        self.help = help
        self.pattern_str = pattern_str
        self.pattern = re.compile(pattern_str)


user_kind_map = {}

user_kind_map["StructName"] = Rule("struct_decl",
                                   "Structure delcaration name, for e.g. in 'struct MyStruct' "
                                   "MyStruct is the StructName")

user_kind_map["UnionName"] = Rule("union_decl",
                                  "Union delcaration name, for e.g. in 'union MyUnion' MyUnion "
                                  "is the UnionName")

user_kind_map["ClassName"] = Rule("class_decl",
                                  "Class delcaration name, "
                                  "for e.g. in 'class MyClass' MyClass is the ClassName")

user_kind_map["EnumName"] = Rule("enum_decl",
                                 "Enum delcaration name, "
                                 "for e.g. in 'enum MyEnum' MyEnum is the EnumName")

user_kind_map["ClassMemberVariable"] = Rule("field_decl",
                                            CursorKind.CLASS_DECL,
                                            "Member variable declartion in a class ")

user_kind_map["StructMemberVariable"] = Rule("field_decl",
                                             CursorKind.STRUCT_DECL,
                                             "Member variable declartion in a struct ")

user_kind_map["UnionMemberVariable"] = Rule("field_decl",
                                            CursorKind.UNION_DECL,
                                            "Member variable declartion in a union ")

user_kind_map["EnumConstantName"] = Rule("enum_constant_decl",
                                         "Enum constant name ")

user_kind_map["FunctionName"] = Rule("function_decl",
                                     "Function name ")

user_kind_map["VariableName"] = Rule("var_decl",
                                     "Variable name ")

user_kind_map["ParameterName"] = Rule("parm_decl",
                                      "Parameter name ")

user_kind_map["TypedefName"] = Rule("typedef_decl",
                                    "Typedef name ")

user_kind_map["CppMethod"] = Rule("cxx_method",
                                  "Cpp Method name ")

# Clang cursor kind to ncc Defined cursor map
cursor_kind_map = {}
cursor_kind_map["struct_decl"] = ["StructName"]
cursor_kind_map["class_decl"] = ["ClassName"]
cursor_kind_map["enum_decl"] = ["EnumName"]
cursor_kind_map["union_decl"] = ["UnionName"]
cursor_kind_map["field_decl"] = ["ClassMemberVariable", "StructMemberVariable",
                                 "UnionMemberVariable"]
cursor_kind_map["enum_constant_decl"] = ["EnumConstantName"]
cursor_kind_map["function_decl"] = ["FunctionName"]
cursor_kind_map["var_decl"] = ["VariableName"]
cursor_kind_map["parm_decl"] = ["ParameterName"]
cursor_kind_map["typedef_decl"] = ["TypedefName"]
cursor_kind_map["cxx_method"] = ["CppMethod"]

SpecialKind = {CursorKind.STRUCT_DECL: 1, CursorKind.CLASS_DECL: 1}


class KindStack(object):
    def __init__(self):
        self.stack = []

    def pop(self):
        return self.stack.pop()

    def push(self, kind):
        self.stack.append(kind)

    def peek(self):
        if len(self.stack) > 0:
            return self.stack[-1]
        return None


class Report(object):
    @staticmethod
    def log(line, column, severity, message):
        print('[{:<7}]# [{}:{}] {}'.format(severity, line, column, message))


class Options:
    def __init__(self):
        self.args = None
        self._style_file = 'ncc.style'
        self._db_dir = None

        self.parser = argparse.ArgumentParser(
            prog="ncc.py",
            description="ncc is a development tool to help programmers "
            "write C/C++ code that adheres to a some naming conventions. It automates the "
            "process of checking C code to spare humans of this boring "
            "(but important) task. This makes it ideal for projects that want "
            "to enforce a coding standard.")

        self.parser.add_argument('-r', '--recurse', action='store_true', dest="recurse",
                                 help="Read all files under each directory, recursively")

        self.parser.add_argument('-s', '--style', dest="style_file",
                                 help="Read rules from the specified file. If the user does not"
                                 "provide a style file ncc will use ncc.style file from the"
                                 "present working directory.")

        self.parser.add_argument('-b', '--dbdir', dest='cdbdir', help="Build path is used to "
                                 "read a `compile_commands.json` compile command database")

        self.parser.add_argument('-d', '--dump', dest='dump', help="Build path is used to "
                                 "read a `compile_commands.json` compile command database")

        self.parser.add_argument("path", metavar="FILE", nargs="+", type=str,
                                 help="Path of file or directory")

    def parse_cmd_line(self):
        self.args = self.parser.parse_args()

        if self.args.cdbdir:
            self._db_dir = self.args.cdbdir

        if self.args.style_file:
            self._style_file = self.args.style_file

        if not os.path.exists(self._style_file):
            sys.stderr.write("Style file '{}' not found!\n".format(self._style_file))
            sys.exit(1)

        if self.args.dump:
            with open(self._style_file) as stylefile:
                r = yaml.safe_load(stylefile)
                pp.pprint(r)

    def next_file(self):
        for filename in self.args.path:
            yield filename


class RulesDb(object):
    def __init__(self, style_file=None, db_dir=None):
        self.__compile_db = None
        self.__rule_db = {}
        self.__clang_db = {}

        if db_dir:
            try:
                self.__compile_db = CompilationDatabase.fromDirectory(db_dir)
            except Exception as e:
                sys.exit(1)

        self.build_rules_db(style_file)

    def build_rules_db(self, style_file):
        if style_file is not None:
            with open(style_file) as stylefile:
                style_rules = yaml.safe_load(stylefile)

            try:
                cursor_kinds = {kind.name.lower(): kind for kind in CursorKind.get_all_kinds()}

                for (user_kind, pattern_str) in style_rules.items():
                    clang_kind_str = user_kind_map[user_kind].clang_kind_str
                    clang_kind = cursor_kinds[clang_kind_str]
                    if clang_kind:
                        self.__rule_db[user_kind] = user_kind_map[user_kind]
                        self.__rule_db[user_kind].pattern_str = pattern_str
                        self.__rule_db[user_kind].pattern = re.compile(pattern_str)
                        self.__clang_db[clang_kind] = cursor_kind_map[clang_kind_str]

            except KeyError as e:
                sys.stderr.write('{} is not a valid C/C++ construct name\n'.format(e.message))
                fixit = difflib.get_close_matches(e.message, cursor_kinds.keys(), n=1, cutoff=0.8)
                if fixit:
                    sys.stderr.write('Did you mean CursorKind: {}\n'.format(fixit[0]))
                sys.exit(1)
        else:
            self.__rule_db = user_kind_map

    def get_compile_commands(self, filename):
        if self.__compile_db:
            return self.__compile_db.getCompileCommands(filename)
        return None

    def is_rule_enabled(self, kind):
        if self.__clang_db.get(kind):
            return True
        return False

    def get_user_kinds(self, kind):
        return self.__clang_db.get(kind)

    def get_rule(self, user_kind):
        return self.__rule_db.get(user_kind)


class Validator(object):
    def __init__(self, rule_db):
        self.rule_db = rule_db

    def validate(self, filename):
        commands = self.rule_db.get_compile_commands(filename)
        index = Index.create()
        unit = index.parse(filename, args=commands)
        cursor = unit.cursor

        k_stack = KindStack()
        return self.check(cursor, k_stack, filename)

    def check(self, node, k_stack, filename):
        errors = 0
        for child in node.get_children():
            if self.is_local(child, filename):
                errors += self.match_pattern(child, self.get_rule(child, k_stack))
                if child.kind in SpecialKind:
                    k_stack.push(child.kind)
                    errors += self.check(child, k_stack, filename)
                    k_stack.pop()
                else:
                    errors += self.check(child, k_stack, filename)

        return errors

    def get_rule(self, node, k_stack):
        if not self.rule_db.is_rule_enabled(node.kind):
            return None

        user_kinds = self.rule_db.get_user_kinds(node.kind)
        if len(user_kinds) == 1:
            return self.rule_db.get_rule(user_kinds[0])

        for kind in user_kinds:
            rule = self.rule_db.get_rule(kind)
            if rule.parent_kind == k_stack.peek():
                return rule

    def match_pattern(self, node, rule):
        if not rule:
            return 0

        res = rule.pattern.match(node.spelling)
        if not res:
            self.notify_error(node, rule.pattern_str)
            return 1
        return 0

    """ Returns True is node belongs to the file being validated and not an include file """
    def is_local(self, node, filename):
        if node.location.file and node.location.file.name in filename:
            return True
        return False

    def notify_error(self, node, pattern_str):
        fmt = '{}:{}:{}: "{}" does not match "{}" associated with {}\n'
        msg = fmt.format(node.location.file.name, node.location.line, node.location.column,
                         node.displayname, pattern_str,
                         node.kind.name.lower())
        sys.stderr.write(msg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s',
                        filename='log.txt', filemode='w')

    pp = pprint.PrettyPrinter(indent=2)

    """ Parse all command line arguments and validate """
    op = Options()
    op.parse_cmd_line()

    """ Creating the rules database """
    rules_db = RulesDb(op._style_file, op._db_dir)

    """ Check the source code against the configured rules """
    v = Validator(rules_db)
    for filename in op.next_file():
        if not os.path.exists(filename):
            sys.stderr.write("File '{}' does not exist\n".format(filename))
        elif os.path.isfile(filename):
            print("Validating {}".format(filename))
            v.validate(filename)
        elif os.path.isdir(filename):
            if op.args.recurse:
                # Get all files recursively and validate
                print("Recursing directory {}".format(filename))
                for (root, subdirs, subfiles) in os.walk(filename):
                    for subfile in subfiles:
                        path = root + '/' + subfile
                        print("Validating {}".format(path))
                        v.validate(path)
            else:
                # Validate all the files in the directory
                for subfile in os.listdir(filename):
                    path = filename + '/' + subfile
                    if os.path.isfile(path):
                        print("Validating {}".format(path))
                        v.validate(path)
