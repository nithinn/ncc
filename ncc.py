#!/usr/bin/env python

import logging
import pprint
import argparse
import yaml
import re
import sys
import difflib
from clang.cindex import Index
from clang.cindex import CompilationDatabase
from clang.cindex import CursorKind


class Rule(object):
    def __init__(self, kind, clang_kind, help, pattern='^.*$', cxx_construct=None):
        self._kind = kind
        self._clang_kind = clang_kind
        self._help = help
        self._pattern = pattern
        self._cxx_construct = cxx_construct


default_rule_db = {}

default_rule_db["StructName"] = Rule("StructName",
                                     "struct_decl",
                                     "Structure delcaration name, for e.g. in 'struct MyStruct' "
                                     "MyStruct is the StructName")

default_rule_db["UnionName"] = Rule("UnionName", "union_decl", "Union delcaration name, "
                                    "for e.g. in 'union MyUnion' MyUnion is the UnionName")
default_rule_db["ClassName"] = Rule("ClassName", "class_decl", "Class delcaration name, "
                                    "for e.g. in 'class MyClass' MyClass is the ClassName")
default_rule_db["EnumName"] = Rule("EnumName", "enum_decl", "Enum delcaration name, "
                                   "for e.g. in 'enum MyEnum' MyEnum is the EnumName")
default_rule_db["ClassMemberVariable"] = Rule("ClassMemberVariable", "field_decl",
                                              "Member variable declartion in a class ",
                                              "^.*$", "class")
default_rule_db["StructMemberVariable"] = Rule("StructMemberVariable", "field_decl",
                                               "Member variable declartion in a struct ",
                                               "^.*$", "struct")

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
        self._file_index = -1
        self._style_file = 'ncc.style'
        self._has_files = True
        self._db_dir = None

        self.parser = argparse.ArgumentParser(
            prog="ccheckstyle.py",
            description="ccheckstyle is a development tool to help programmers "
            "write C code that adheres to a coding standard. It automates the "
            "process of checking C code to spare humans of this boring "
            "(but important) task. This makes it ideal for projects that want "
            "to enforce a coding standard.")

        self.parser.add_argument("--recurse", action='store_true', dest="recurse",
                                 help="Read all files under each directory, recursively")

        self.parser.add_argument("--style", dest="style_file",
                                 help="Read rules from the specified file")

        self.parser.add_argument('--dbdir', dest='cdbdir', help="Build path is used to "
                                 "read a `compile_commands.json` compile command database")

        self.parser.add_argument('--dump', dest='dump', help="Build path is used to "
                                 "read a `compile_commands.json` compile command database")

        self.parser.add_argument("path", metavar="FILE", nargs="+", type=str,
                                 help="Path of file or directory")

    def parse_cmd_line(self):
        self.args = self.parser.parse_args()

        if self.args.cdbdir:
            self._db_dir = self.args.cdbdir

        if self.args.style_file:
            self._style_file = self.args.style_file

        if self.args.dump:
            with open(self._style_file) as stylefile:
                r = yaml.safe_load(stylefile)
                pp.pprint(r)

    def print_args(self):
        print("recurse      : {}".format(self.args.recurse))
        print("paths        : {}".format(self.args.path))
        print("style_file   : {}".format(self.args.style_file))
        print("cdbdir       : {}".format(self.args.cdbdir))
        print("dump         : {}".format(self.args.dump))

    def has_next_file(self):
        return self._has_files

    def next_file(self):
        self._file_index += 1
        if self._file_index < len(self.args.path):
            return self.args.path[self._file_index]
        else:
            self._has_files = False
            return None


class RulesDb(object):
    def __init__(self, style_file=None, db_dir=None):
        self._compile_db = None
        self._rule_db = {}

        if db_dir:
            try:
                self._compile_db = CompilationDatabase.fromDirectory(db_dir)
            except Exception as e:
                sys.exit(1)

        self.build_rules_db(style_file)

    def build_rules_db(self, style_file):
        if style_file is not None:
            with open(style_file) as stylefile:
                style_rules = yaml.safe_load(stylefile)

            try:
                cursor_kinds = {kind.name.lower(): kind for kind in CursorKind.get_all_kinds()}

                # for (kind, pattern) in style_rules.items():
                #     if cursor_kinds[default_rule_db[kind]._clang_kind]:
                #         self._rule_db[kind] = default_rule_db[kind]
                #         self._rule_db[kind]._pattern = re.compile(pattern)
                self._rule_db = {cursor_kinds[kind]: re.compile(pattern)
                                 for (kind, pattern) in style_rules.items()}

            except KeyError as e:
                sys.stderr.write('{} is not a valid C/C++ construct name\n'.format(e.message))
                fixit = difflib.get_close_matches(e.message, cursor_kinds.keys(), n=1, cutoff=0.8)
                if fixit:
                    sys.stderr.write('Did you mean CursorKind: {}\n'.format(fixit[0]))
                sys.exit(1)
        else:
            self._rule_db = default_rule_db


class Validator(object):
    def __init__(self, rule_db, compile_db):
        self._rule_db = rule_db
        self._compile_db = compile_db
        self.k_stack = KindStack()

    def validate(self, filename):
        commands = None
        if self._compile_db is not None:
            commands = self._compile_db.getCompileCommands(filename)

        index = Index.create()
        unit = index.parse(filename, args=commands)
        cursor = unit.cursor

        return self.check(cursor, filename)

    def match_pattern(self, node):
        if self.do_check(node) and self.is_invalid(node):
            self.notify_error(node)
            return 1
        return 0

    def check(self, node, filename):
        errors = 0
        for child in node.get_children():
            if self.is_local(child, filename):
                errors += self.match_pattern(child)
                if child.kind in SpecialKind:
                    self.k_stack.push(child.kind)
                    errors += self.check(child, filename)
                    self.k_stack.pop()
                else:
                    errors += self.check(child, filename)

        return errors

    """ Returns True is pattern in available for the Cursor kind """
    def do_check(self, node):
        if self._rule_db.get(node.kind):
            return True
        return False

    """ Returns True is node belongs to the file being validated and not an include file """
    def is_local(self, node, filename):
        if node.location.file and node.location.file.name in filename:
            return True
        return False

    """ Returns true if pattern does not match the c/c++ construct """
    def is_invalid(self, node):
        return not self._rule_db[node.kind].match(node.spelling)

    def notify_error(self, node):
        fmt = '{}:{}:{}: "{}" does not match "{}" associated with {}\n'
        msg = fmt.format(node.location.file.name, node.location.line, node.location.column,
                         node.displayname, self._rule_db[node.kind].pattern,
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
    v = Validator(rules_db._rule_db, rules_db._compile_db)
    while op.has_next_file():
        filename = op.next_file()
        if filename is not None:
            v.validate(filename)
