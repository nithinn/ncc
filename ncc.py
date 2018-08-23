#!/usr/bin/env python

import logging
import pprint
import argparse
import yaml
import re
import sys
import difflib
import os
from collections import defaultdict
from clang.cindex import Index
from clang.cindex import CompilationDatabase
from clang.cindex import CursorKind


# Clang cursor kind to ncc Defined cursor map
cursor_kind_map = defaultdict(list)
SpecialKind = {CursorKind.STRUCT_DECL: 1, CursorKind.CLASS_DECL: 1}


class Rule(object):
    def __init__(self, clang_kind_str, parent_kind=None,
                 pattern_str='^.*$'):
        self.clang_kind_str = clang_kind_str
        self.parent_kind = parent_kind
        self.pattern_str = pattern_str
        self.pattern = re.compile(pattern_str)


default_rules_db = {}

default_rules_db["StructName"] = Rule("struct_decl")

default_rules_db["UnionName"] = Rule("union_decl")

default_rules_db["ClassName"] = Rule("class_decl")

default_rules_db["EnumName"] = Rule("enum_decl")

default_rules_db["ClassMemberVariable"] = Rule("field_decl",
                                               CursorKind.CLASS_DECL)

default_rules_db["StructMemberVariable"] = Rule("field_decl",
                                                CursorKind.STRUCT_DECL)

default_rules_db["UnionMemberVariable"] = Rule("field_decl",
                                               CursorKind.UNION_DECL)

default_rules_db["EnumConstantName"] = Rule("enum_constant_decl")

default_rules_db["FunctionName"] = Rule("function_decl")

default_rules_db["VariableName"] = Rule("var_decl")

default_rules_db["ParameterName"] = Rule("parm_decl")

default_rules_db["TypedefName"] = Rule("typedef_decl")

default_rules_db["CppMethod"] = Rule("cxx_method")

default_rules_db["Namespace"] = Rule("namespace")

default_rules_db["ConversionFunction"] = Rule("conversion_function")

default_rules_db["TemplateTypeParameter"] = Rule("template_type_parameter")

default_rules_db["TemplateNonTypeParameter"] = Rule("template_non_type_parameter")

default_rules_db["TemplateTemplateParameter"] = Rule("template_template_parameter")

default_rules_db["FunctionTemplate"] = Rule("function_template")

default_rules_db["ClassTemplate"] = Rule("class_template")

default_rules_db["ClassTemplatePartialSpecialization"] = Rule(
    "class_template_partial_specialization")

# default_rules_db["NamespaceAlias"] = Rule()
# default_rules_db["UsingDirective"] = Rule()
# default_rules_db["UsingDeclaration"] = Rule()
# default_rules_db["TypeAliasDecl"] = Rule()
# default_rules_db["CxxAccessSpecDecl"] = Rule()
# default_rules_db["TypeRef"] = Rule()
# default_rules_db["CxxBaseSpecifier"] = Rule()
# default_rules_db["TemplateRef"] = Rule()
# default_rules_db["NamespaceRef"] = Rule()
# default_rules_db["MemberRef"] = Rule()
# default_rules_db["LabelRef"] = Rule()
# default_rules_db["OverloadedDeclRef"] = Rule()
# default_rules_db["VariableRef"] = Rule()
# default_rules_db["InvalidFile"] = Rule()
# default_rules_db["NoDeclFound"] = Rule()
# default_rules_db["NotImplemented"] = Rule()
# default_rules_db["InvalidCode"] = Rule()
# default_rules_db["UnexposedExpr"] = Rule()
# default_rules_db["DeclRefExpr"] = Rule()
# default_rules_db["MemberRefExpr"] = Rule()
# default_rules_db["CallExpr"] = Rule()
# default_rules_db["BlockExpr"] = Rule()
# default_rules_db["IntegerLiteral"] = Rule()
# default_rules_db["FloatingLiteral"] = Rule()
# default_rules_db["ImaginaryLiteral"] = Rule()
# default_rules_db["StringLiteral"] = Rule()
# default_rules_db["CharacterLiteral"] = Rule()
# default_rules_db["ParenExpr"] = Rule()
# default_rules_db["UnaryOperator"] = Rule()
# default_rules_db["ArraySubscriptExpr"] = Rule()
# default_rules_db["BinaryOperator"] = Rule()
# default_rules_db["CompoundAssignmentOperator"] = Rule()
# default_rules_db["ConditionalOperator"] = Rule()
# default_rules_db["CstyleCastExpr"] = Rule()
# default_rules_db["CompoundLiteralExpr"] = Rule()
# default_rules_db["InitListExpr"] = Rule()
# default_rules_db["AddrLabelExpr"] = Rule()
# default_rules_db["Stmtexpr"] = Rule()
# default_rules_db["GenericSelectionExpr"] = Rule()
# default_rules_db["GnuNullExpr"] = Rule()
# default_rules_db["CxxStaticCastExpr"] = Rule()
# default_rules_db["CxxDynamicCastExpr"] = Rule()
# default_rules_db["CxxReinterpretCastExpr"] = Rule()
# default_rules_db["CxxConstCastExpr"] = Rule()
# default_rules_db["CxxFunctionalCastExpr"] = Rule()
# default_rules_db["CxxTypeidExpr"] = Rule()
# default_rules_db["CxxBoolLiteralExpr"] = Rule()
# default_rules_db["CxxNullPtrLiteralExpr"] = Rule()
# default_rules_db["CxxThisExpr"] = Rule()
# default_rules_db["CxxThrowExpr"] = Rule()
# default_rules_db["CxxNewExpr"] = Rule()
# default_rules_db["CxxDeleteExpr"] = Rule()
# default_rules_db["CxxUnaryExpr"] = Rule()
# default_rules_db["PackExpansionExpr"] = Rule()
# default_rules_db["SizeOfPackExpr"] = Rule()
# default_rules_db["LambdaExpr"] = Rule()
# default_rules_db["ObjBoolLiteralExpr"] = Rule()
# default_rules_db["ObjSelfExpr"] = Rule()
# default_rules_db["UnexposedStmt"] = Rule()
# default_rules_db["LabelStmt"] = Rule()
# default_rules_db["CompoundStmt"] = Rule()
# default_rules_db["CaseStmt"] = Rule()
# default_rules_db["DefaultStmt"] = Rule()
# default_rules_db["IfStmt"] = Rule()
# default_rules_db["SwitchStmt"] = Rule()
# default_rules_db["WhileStmt"] = Rule()
# default_rules_db["DoStmt"] = Rule()
# default_rules_db["ForStmt"] = Rule()
# default_rules_db["GotoStmt"] = Rule()
# default_rules_db["IndirectGotoStmt"] = Rule()
# default_rules_db["ContinueStmt"] = Rule()
# default_rules_db["BreakStmt"] = Rule()
# default_rules_db["ReturnStmt"] = Rule()
# default_rules_db["AsmStmt"] = Rule()
# default_rules_db["CxxCatchStmt"] = Rule()
# default_rules_db["CxxTryStmt"] = Rule()
# default_rules_db["CxxForRangeStmt"] = Rule()
# default_rules_db["MsAsmStmt"] = Rule()
# default_rules_db["NullStmt"] = Rule()
# default_rules_db["DeclStmt"] = Rule()
# default_rules_db["TranslationUnit"] = Rule()
# default_rules_db["UnexposedAttr"] = Rule()
# default_rules_db["CxxFinalAttr"] = Rule()
# default_rules_db["CxxOverrideAttr"] = Rule()
# default_rules_db["AnnotateAttr"] = Rule()
# default_rules_db["AsmLabelAttr"] = Rule()
# default_rules_db["PackedAttr"] = Rule()
# default_rules_db["PureAttr"] = Rule()
# default_rules_db["ConstAttr"] = Rule()
# default_rules_db["NoduplicateAttr"] = Rule()
# default_rules_db["PreprocessingDirective"] = Rule()
# default_rules_db["MacroDefinition"] = Rule()
# default_rules_db["MacroInstantiation"] = Rule()
# default_rules_db["InclusionDirective"] = Rule()


class AstNodeStack(object):
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

        self.parser.add_argument('-o', '--output', dest='output', help="output file name where"
                                 "naming convenction vialoations will be stored")

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

        self.build_cursor_kind_map()
        self.build_rules_db(style_file)

    def build_rules_db(self, style_file):
        if style_file is not None:
            with open(style_file) as stylefile:
                style_rules = yaml.safe_load(stylefile)

            try:
                cursor_kinds = {kind.name.lower(): kind for kind in CursorKind.get_all_kinds()}

                for (user_kind, pattern_str) in style_rules.items():
                    clang_kind_str = default_rules_db[user_kind].clang_kind_str
                    clang_kind = cursor_kinds[clang_kind_str]
                    if clang_kind:
                        self.__rule_db[user_kind] = default_rules_db[user_kind]
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
            self.__rule_db = default_rules_db

    def build_cursor_kind_map(self):
        for key, value in default_rules_db.iteritems():
            cursor_kind_map[value.clang_kind_str].append(key)

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

        node_stack = AstNodeStack()
        return self.check(cursor, node_stack, filename)

    def check(self, node, node_stack, filename):
        errors = 0
        for child in node.get_children():
            if self.is_local(child, filename):

                # get the node's rule and match the pattern. Report and error if pattern
                # matching fails
                rule, user_kind = self.get_rule(child, node_stack)
                if rule and (not rule.pattern.match(child.spelling)):
                    self.notify_error(child, rule, user_kind)
                    errors += 1

                if child.kind in SpecialKind:
                    # Members struct, class, and unions must be treated differently. So whenever
                    # we encounter these types we push it into a stack. Once all its children are
                    # validated pop it out of the stack
                    node_stack.push(child.kind)
                    errors += self.check(child, node_stack, filename)
                    node_stack.pop()
                else:
                    errors += self.check(child, node_stack, filename)

        return errors

    def get_rule(self, node, node_stack):
        if not self.rule_db.is_rule_enabled(node.kind):
            return None, None

        user_kinds = self.rule_db.get_user_kinds(node.kind)
        for kind in user_kinds:
            rule = self.rule_db.get_rule(kind)
            if rule.parent_kind == node_stack.peek():
                return rule, kind

        return self.rule_db.get_rule(user_kinds[0]), user_kinds[0]

    """ Returns True is node belongs to the file being validated and not an include file """
    def is_local(self, node, filename):
        if node.location.file and node.location.file.name in filename:
            return True
        return False

    def notify_error(self, node, rule, user_kind):
        fmt = '{}:{}:{}: "{}" does not match "{}" associated with {}\n'
        msg = fmt.format(node.location.file.name, node.location.line, node.location.column,
                         node.displayname, rule.pattern_str, user_kind)
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
