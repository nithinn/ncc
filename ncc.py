#!/usr/bin/env python

# MIT License
#
# Copyright (c) 2018 Nithin Nellikunnu (nithin.nn@gmail.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
import argparse
import yaml
import re
import sys
import difflib
import os
import fnmatch
from collections import defaultdict
from clang.cindex import Index
from clang.cindex import CompilationDatabase
from clang.cindex import CursorKind


# Clang cursor kind to ncc Defined cursor map
default_rules_db = {}
clang_to_user_map = defaultdict(list)
special_kind = {CursorKind.STRUCT_DECL: 1, CursorKind.CLASS_DECL: 1}
file_extensions = [".c", ".cpp", ".h", ".hpp"]


class Rule(object):
    def __init__(self, clang_kind, parent_kind=None, pattern_str='^.*$'):
        self.clang_kind = clang_kind
        self.parent_kind = parent_kind
        self.pattern_str = pattern_str
        self.pattern = re.compile(pattern_str)
        self.includes = []
        self.excludes = []


# All supported rules
default_rules_db["StructName"] = Rule(CursorKind.STRUCT_DECL)
default_rules_db["UnionName"] = Rule(CursorKind.UNION_DECL)
default_rules_db["ClassName"] = Rule(CursorKind.CLASS_DECL)
default_rules_db["EnumName"] = Rule(CursorKind.ENUM_DECL)
default_rules_db["ClassMemberVariable"] = Rule(CursorKind.FIELD_DECL, CursorKind.CLASS_DECL)
default_rules_db["StructMemberVariable"] = Rule(CursorKind.FIELD_DECL, CursorKind.STRUCT_DECL)
default_rules_db["UnionMemberVariable"] = Rule(CursorKind.FIELD_DECL, CursorKind.UNION_DECL)
default_rules_db["EnumConstantName"] = Rule(CursorKind.ENUM_CONSTANT_DECL)
default_rules_db["FunctionName"] = Rule(CursorKind.FUNCTION_DECL)
default_rules_db["VariableName"] = Rule(CursorKind.VAR_DECL)
default_rules_db["ParameterName"] = Rule(CursorKind.PARM_DECL)
default_rules_db["TypedefName"] = Rule(CursorKind.TYPEDEF_DECL)
default_rules_db["CppMethod"] = Rule(CursorKind.CXX_METHOD)
default_rules_db["Namespace"] = Rule(CursorKind.NAMESPACE)
default_rules_db["ConversionFunction"] = Rule(CursorKind.CONVERSION_FUNCTION)
default_rules_db["TemplateTypeParameter"] = Rule(CursorKind.TEMPLATE_TYPE_PARAMETER)
default_rules_db["TemplateNonTypeParameter"] = Rule(CursorKind.TEMPLATE_NON_TYPE_PARAMETER)
default_rules_db["TemplateTemplateParameter"] = Rule(CursorKind.TEMPLATE_TEMPLATE_PARAMETER)
default_rules_db["FunctionTemplate"] = Rule(CursorKind.FUNCTION_TEMPLATE)
default_rules_db["ClassTemplate"] = Rule(CursorKind.CLASS_TEMPLATE)
default_rules_db["ClassTemplatePartialSpecialization"] = Rule(
    CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION)
default_rules_db["NamespaceAlias"] = Rule(CursorKind.NAMESPACE_ALIAS)
default_rules_db["UsingDirective"] = Rule(CursorKind.USING_DIRECTIVE)
default_rules_db["UsingDeclaration"] = Rule(CursorKind.USING_DECLARATION)
default_rules_db["TypeAliasName"] = Rule(CursorKind.TYPE_ALIAS_DECL)
default_rules_db["ClassAccessSpecifier"] = Rule(CursorKind.CXX_ACCESS_SPEC_DECL)
default_rules_db["TypeReference"] = Rule(CursorKind.TYPE_REF)
default_rules_db["CxxBaseSpecifier"] = Rule(CursorKind.CXX_BASE_SPECIFIER)
default_rules_db["TemplateReference"] = Rule(CursorKind.TEMPLATE_REF)
default_rules_db["NamespaceReference"] = Rule(CursorKind.NAMESPACE_REF)
default_rules_db["MemberReference"] = Rule(CursorKind.MEMBER_REF)
default_rules_db["LabelReference"] = Rule(CursorKind.LABEL_REF)
default_rules_db["OverloadedDeclarationReference"] = Rule(CursorKind.OVERLOADED_DECL_REF)
default_rules_db["VariableReference"] = Rule(CursorKind.VARIABLE_REF)
default_rules_db["InvalidFile"] = Rule(CursorKind.INVALID_FILE)
default_rules_db["NoDeclarationFound"] = Rule(CursorKind.NO_DECL_FOUND)
default_rules_db["NotImplemented"] = Rule(CursorKind.NOT_IMPLEMENTED)
default_rules_db["InvalidCode"] = Rule(CursorKind.INVALID_CODE)
default_rules_db["UnexposedExpression"] = Rule(CursorKind.UNEXPOSED_EXPR)
default_rules_db["DeclarationReferenceExpression"] = Rule(CursorKind.DECL_REF_EXPR)
default_rules_db["MemberReferenceExpression"] = Rule(CursorKind.MEMBER_REF_EXPR)
default_rules_db["CallExpression"] = Rule(CursorKind.CALL_EXPR)
default_rules_db["BlockExpression"] = Rule(CursorKind.BLOCK_EXPR)
default_rules_db["IntegerLiteral"] = Rule(CursorKind.INTEGER_LITERAL)
default_rules_db["FloatingLiteral"] = Rule(CursorKind.FLOATING_LITERAL)
default_rules_db["ImaginaryLiteral"] = Rule(CursorKind.IMAGINARY_LITERAL)
default_rules_db["StringLiteral"] = Rule(CursorKind.STRING_LITERAL)
default_rules_db["CharacterLiteral"] = Rule(CursorKind.CHARACTER_LITERAL)
default_rules_db["ParenExpression"] = Rule(CursorKind.PAREN_EXPR)
default_rules_db["UnaryOperator"] = Rule(CursorKind.UNARY_OPERATOR)
default_rules_db["ArraySubscriptExpression"] = Rule(CursorKind.ARRAY_SUBSCRIPT_EXPR)
default_rules_db["BinaryOperator"] = Rule(CursorKind.BINARY_OPERATOR)
default_rules_db["CompoundAssignmentOperator"] = Rule(CursorKind.COMPOUND_ASSIGNMENT_OPERATOR)
default_rules_db["ConditionalOperator"] = Rule(CursorKind.CONDITIONAL_OPERATOR)
default_rules_db["CstyleCastExpression"] = Rule(CursorKind.CSTYLE_CAST_EXPR)
default_rules_db["CompoundLiteralExpression"] = Rule(CursorKind.COMPOUND_LITERAL_EXPR)
default_rules_db["InitListExpression"] = Rule(CursorKind.INIT_LIST_EXPR)
default_rules_db["AddrLabelExpression"] = Rule(CursorKind.ADDR_LABEL_EXPR)
default_rules_db["StatementExpression"] = Rule(CursorKind.StmtExpr)
default_rules_db["GenericSelectionExpression"] = Rule(CursorKind.GENERIC_SELECTION_EXPR)
default_rules_db["GnuNullExpression"] = Rule(CursorKind.GNU_NULL_EXPR)
default_rules_db["CxxStaticCastExpression"] = Rule(CursorKind.CXX_STATIC_CAST_EXPR)
default_rules_db["CxxDynamicCastExpression"] = Rule(CursorKind.CXX_DYNAMIC_CAST_EXPR)
default_rules_db["CxxReinterpretCastExpression"] = Rule(CursorKind.CXX_REINTERPRET_CAST_EXPR)
default_rules_db["CxxConstCastExpression"] = Rule(CursorKind.CXX_CONST_CAST_EXPR)
default_rules_db["CxxFunctionalCastExpression"] = Rule(CursorKind.CXX_FUNCTIONAL_CAST_EXPR)
default_rules_db["CxxTypeidExpression"] = Rule(CursorKind.CXX_TYPEID_EXPR)
default_rules_db["CxxBoolLiteralExpression"] = Rule(CursorKind.CXX_BOOL_LITERAL_EXPR)
default_rules_db["CxxNullPointerLiteralExpression"] = Rule(CursorKind.CXX_NULL_PTR_LITERAL_EXPR)
default_rules_db["CxxThisExpression"] = Rule(CursorKind.CXX_THIS_EXPR)
default_rules_db["CxxThrowExpression"] = Rule(CursorKind.CXX_THROW_EXPR)
default_rules_db["CxxNewExpression"] = Rule(CursorKind.CXX_NEW_EXPR)
default_rules_db["CxxDeleteExpression"] = Rule(CursorKind.CXX_DELETE_EXPR)
default_rules_db["CxxUnaryExpression"] = Rule(CursorKind.CXX_UNARY_EXPR)
default_rules_db["PackExpansionExpression"] = Rule(CursorKind.PACK_EXPANSION_EXPR)
default_rules_db["SizeOfPackExpression"] = Rule(CursorKind.SIZE_OF_PACK_EXPR)
default_rules_db["LambdaExpression"] = Rule(CursorKind.LAMBDA_EXPR)
default_rules_db["ObjectBoolLiteralExpression"] = Rule(CursorKind.OBJ_BOOL_LITERAL_EXPR)
default_rules_db["ObjectSelfExpression"] = Rule(CursorKind.OBJ_SELF_EXPR)
default_rules_db["UnexposedStatement"] = Rule(CursorKind.UNEXPOSED_STMT)
default_rules_db["LabelStatement"] = Rule(CursorKind.LABEL_STMT)
default_rules_db["CompoundStatement"] = Rule(CursorKind.COMPOUND_STMT)
default_rules_db["CaseStatement"] = Rule(CursorKind.CASE_STMT)
default_rules_db["DefaultStatement"] = Rule(CursorKind.DEFAULT_STMT)
default_rules_db["IfStatement"] = Rule(CursorKind.IF_STMT)
default_rules_db["SwitchStatement"] = Rule(CursorKind.SWITCH_STMT)
default_rules_db["WhileStatement"] = Rule(CursorKind.WHILE_STMT)
default_rules_db["DoStatement"] = Rule(CursorKind.DO_STMT)
default_rules_db["ForStatement"] = Rule(CursorKind.FOR_STMT)
default_rules_db["GotoStatement"] = Rule(CursorKind.GOTO_STMT)
default_rules_db["IndirectGotoStatement"] = Rule(CursorKind.INDIRECT_GOTO_STMT)
default_rules_db["ContinueStatement"] = Rule(CursorKind.CONTINUE_STMT)
default_rules_db["BreakStatement"] = Rule(CursorKind.BREAK_STMT)
default_rules_db["ReturnStatement"] = Rule(CursorKind.RETURN_STMT)
default_rules_db["AsmStatement"] = Rule(CursorKind.ASM_STMT)
default_rules_db["CxxCatchStatement"] = Rule(CursorKind.CXX_CATCH_STMT)
default_rules_db["CxxTryStatement"] = Rule(CursorKind.CXX_TRY_STMT)
default_rules_db["CxxForRangeStatement"] = Rule(CursorKind.CXX_FOR_RANGE_STMT)
default_rules_db["MsAsmStatement"] = Rule(CursorKind.MS_ASM_STMT)
default_rules_db["NullStatement"] = Rule(CursorKind.NULL_STMT)
default_rules_db["DeclarationStatement"] = Rule(CursorKind.DECL_STMT)
default_rules_db["TranslationUnit"] = Rule(CursorKind.TRANSLATION_UNIT)
default_rules_db["UnexposedAttribute"] = Rule(CursorKind.UNEXPOSED_ATTR)
default_rules_db["CxxFinalAttribute"] = Rule(CursorKind.CXX_FINAL_ATTR)
default_rules_db["CxxOverrideAttribute"] = Rule(CursorKind.CXX_OVERRIDE_ATTR)
default_rules_db["AnnotateAttribute"] = Rule(CursorKind.ANNOTATE_ATTR)
default_rules_db["AsmLabelAttribute"] = Rule(CursorKind.ASM_LABEL_ATTR)
default_rules_db["PackedAttribute"] = Rule(CursorKind.PACKED_ATTR)
default_rules_db["PureAttribute"] = Rule(CursorKind.PURE_ATTR)
default_rules_db["ConstAttribute"] = Rule(CursorKind.CONST_ATTR)
default_rules_db["NoduplicateAttribute"] = Rule(CursorKind.NODUPLICATE_ATTR)
default_rules_db["PreprocessingDirective"] = Rule(CursorKind.PREPROCESSING_DIRECTIVE)
default_rules_db["MacroDefinition"] = Rule(CursorKind.MACRO_DEFINITION)
default_rules_db["MacroInstantiation"] = Rule(CursorKind.MACRO_INSTANTIATION)
default_rules_db["InclusionDirective"] = Rule(CursorKind.INCLUSION_DIRECTIVE)


# Reverse lookup map. The parse identifies Clang cursor kinds, which must be mapped
# to user defined types
for key, value in default_rules_db.iteritems():
    clang_to_user_map[value.clang_kind].append(key)


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


class Options:
    def __init__(self):
        self.args = None
        self._db_dir = None
        self._style_file = None
        self.file_exclusions = None

        self.parser = argparse.ArgumentParser(
            prog="ncc.py",
            description="ncc is a development tool to help programmers "
            "write C/C++ code that adheres to adhere some naming conventions. It automates the "
            "process of checking C code to spare humans of this boring "
            "(but important) task. This makes it ideal for projects that want "
            "to enforce a coding standard.")

        self.parser.add_argument('--recurse', action='store_true', dest="recurse",
                                 help="Read all files under each directory, recursively")

        self.parser.add_argument('--style', dest="style_file",
                                 help="Read rules from the specified file. If the user does not"
                                 "provide a style file ncc will use all style rules. To print"
                                 "all style rules use --dump option")

        self.parser.add_argument('--cdbdir', dest='cdbdir', help="Build path is used to "
                                 "read a `compile_commands.json` compile command database")

        self.parser.add_argument('--dump', dest='dump', action='store_true',
                                 help="Dump all available options")

        self.parser.add_argument('--output', dest='output', help="output file name where"
                                 "naming convenction vialoations will be stored")

        self.parser.add_argument('--filetype', dest='filetype', help="File extentions type"
                                 "that are applicable for naming convection validation")

        self.parser.add_argument('--exclude', dest='exclude', nargs="+", help="Skip files "
                                 "matching the pattern specified from recursive searches. It "
                                 "matches a specified pattern according to the rules used by "
                                 "the Unix shell")

        # self.parser.add_argument('--exclude-dir', dest='exclude_dir', help="Skip the directories"
        #                          "matching the pattern specified")

        self.parser.add_argument('--path', dest='path', nargs="+",
                                 help="Path of file or directory")

    def parse_cmd_line(self):
        self.args = self.parser.parse_args()

        if self.args.cdbdir:
            self._db_dir = self.args.cdbdir

        if self.args.dump:
            self.dump_all_rules()

        if self.args.style_file:
            self._style_file = self.args.style_file
            if not os.path.exists(self._style_file):
                sys.stderr.write("Style file '{}' not found!\n".format(self._style_file))
                sys.exit(1)

    def dump_all_rules(self):
        print("----------------------------------------------------------")
        print("{:<35} | {}".format("Rule Name", "Pattern"))
        print("----------------------------------------------------------")
        for (key, value) in default_rules_db.iteritems():
            print("{:<35} : {}".format(key, value.pattern_str))


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

        if style_file:
            self.build_rules_db(style_file)
        else:
            self.__rule_db = default_rules_db
            self.__clang_db = clang_to_user_map

    def build_rules_db(self, style_file):
        with open(style_file) as stylefile:
            style_rules = yaml.safe_load(stylefile)

        for (user_kind, pattern_str) in style_rules.items():
            try:
                clang_kind = default_rules_db[user_kind].clang_kind
                if clang_kind:
                    self.__rule_db[user_kind] = default_rules_db[user_kind]
                    self.__rule_db[user_kind].pattern_str = pattern_str
                    self.__rule_db[user_kind].pattern = re.compile(pattern_str)
                    self.__clang_db[clang_kind] = clang_to_user_map[clang_kind]

            except KeyError as e:
                sys.stderr.write('{} is not a valid C/C++ construct name\n'.format(e.message))
                fixit = difflib.get_close_matches(e.message, default_rules_db.keys(),
                                                  n=1, cutoff=0.8)
                if fixit:
                    sys.stderr.write('Did you mean CursorKind: {} ?\n'.format(fixit[0]))
                sys.exit(1)
            except re.error as e:
                sys.stderr.write('"{}" pattern {} has {} \n'.
                                 format(user_kind, pattern_str, e.message))
                sys.exit(1)

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
    def __init__(self, rule_db, filename):
        self.filename = filename
        self.rule_db = rule_db
        self.node_stack = AstNodeStack()

        index = Index.create()
        commands = self.rule_db.get_compile_commands(filename)
        if commands:
            self.cursor = index.parse(filename, args=commands).cursor
        else:
            self.cursor = index.parse(filename, args=['-x', 'c++']).cursor

    def validate(self):
        return self.check(self.cursor)

    def check(self, node):
        """
        Recursively visit all nodes of the AST and match against the patter provided by
        the user. Return the total number of errors caught in the file
        """
        errors = 0
        for child in node.get_children():
            if self.is_local(child, self.filename):

                # This is the case when typedef of struct is causing double reporting of error
                # TODO: Find a better way to handle it
                parent = self.node_stack.peek()
                if (parent and parent == CursorKind.TYPEDEF_DECL and
                        child.kind == CursorKind.STRUCT_DECL):
                    return 0

                errors += self.match_pattern(child)

                # Members struct, class, and unions must be treated differently.
                # So parent ast node information is pushed in to the stack.
                # Once all its children are validated pop it out of the stack
                self.node_stack.push(child.kind)
                errors += self.check(child)
                self.node_stack.pop()

        return errors

    def match_pattern(self, node):
        """
        get the node's rule and match the pattern. Report and error if pattern
        matching fails
        """
        rule, user_kind = self.get_rule(node)
        if rule and (not rule.pattern.match(node.spelling)):
            self.notify_error(node, rule, user_kind)
            return 1
        return 0

    def get_rule(self, node):
        if not self.rule_db.is_rule_enabled(node.kind):
            return None, None

        user_kinds = self.rule_db.get_user_kinds(node.kind)
        for kind in user_kinds:
            rule = self.rule_db.get_rule(kind)
            if rule.parent_kind == self.node_stack.peek():
                return rule, kind

        return self.rule_db.get_rule(user_kinds[0]), user_kinds[0]

    def is_local(self, node, filename):
        """ Returns True is node belongs to the file being validated and not an include file """
        if node.location.file and node.location.file.name in filename:
            return True
        return False

    def notify_error(self, node, rule, user_kind):
        fmt = '{}:{}:{}: "{}" does not match "{}" associated with {}\n'
        msg = fmt.format(node.location.file.name, node.location.line, node.location.column,
                         node.displayname, rule.pattern_str, user_kind)
        sys.stderr.write(msg)


def do_validate(options, filename):
    """
    Returns true if the file should be validated
    - Check if its a c/c++ file
    - Check if the file is not excluded
    """
    path, extension = os.path.splitext(filename)
    if extension not in file_extensions:
        return False

    if options.args.exclude:
        for item in options.args.exclude:
            if fnmatch.fnmatch(filename, item):
                return False

    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s',
                        filename='log.txt', filemode='w')

    """ Parse all command line arguments and validate """
    op = Options()
    op.parse_cmd_line()

    if op.args.path is None:
        sys.exit(0)

    """ Creating the rules database """
    rules_db = RulesDb(op._style_file, op._db_dir)

    """ Check the source code against the configured rules """
    errors = 0
    for path in op.args.path:
        if os.path.isfile(path):
            if do_validate(op, path):
                v = Validator(rules_db, path)
                errors += v.validate()
        elif os.path.isdir(path):
            for (root, subdirs, files) in os.walk(path):
                for filename in files:
                    path = root + '/' + filename
                    if do_validate(op, path):
                        v = Validator(rules_db, path)
                        errors += v.validate()

                if not op.args.recurse:
                    break
        else:
            sys.stderr.write("File '{}' not found!\n".format(path))


    if errors:
        print("Total number of errors = {}".format(errors))
