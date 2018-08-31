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
special_kind = {CursorKind.STRUCT_DECL: 1, CursorKind.CLASS_DECL: 1}
file_extensions = [".c", ".cpp", ".h", ".hpp"]


class Rule(object):
    def __init__(self, clang_kind_str, parent_kind=None, pattern_str='^.*$'):
        self.clang_kind_str = clang_kind_str
        self.parent_kind = parent_kind
        self.pattern_str = pattern_str
        self.pattern = re.compile(pattern_str)


default_rules_db = {}

default_rules_db["StructName"] = Rule("struct_decl")
default_rules_db["UnionName"] = Rule("union_decl")
default_rules_db["ClassName"] = Rule("class_decl")
default_rules_db["EnumName"] = Rule("enum_decl")
default_rules_db["ClassMemberVariable"] = Rule("field_decl", CursorKind.CLASS_DECL)
default_rules_db["StructMemberVariable"] = Rule("field_decl", CursorKind.STRUCT_DECL)
default_rules_db["UnionMemberVariable"] = Rule("field_decl", CursorKind.UNION_DECL)
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
default_rules_db["NamespaceAlias"] = Rule("namespace_alias")
default_rules_db["UsingDirective"] = Rule("using_directive")
default_rules_db["UsingDeclaration"] = Rule("using_declaration")
default_rules_db["TypeAliasName"] = Rule("type_alias_decl")
default_rules_db["ClassAccessSpecifier"] = Rule("cxx_access_spec_decl")
default_rules_db["TypeReference"] = Rule("type_ref")
default_rules_db["CxxBaseSpecifier"] = Rule("cxx_base_specifier")
default_rules_db["TemplateReference"] = Rule("template_ref")
default_rules_db["NamespaceReference"] = Rule("namespace_ref")
default_rules_db["MemberReference"] = Rule("member_ref")
default_rules_db["LabelReference"] = Rule("label_ref")
default_rules_db["OverloadedDeclarationReference"] = Rule("overloaded_decl_ref")
default_rules_db["VariableReference"] = Rule("variable_ref")
default_rules_db["InvalidFile"] = Rule("invalid_file")
default_rules_db["NoDeclarationFound"] = Rule("no_decl_found")
default_rules_db["NotImplemented"] = Rule("not_implemented")
default_rules_db["InvalidCode"] = Rule("invalid_code")
default_rules_db["UnexposedExpression"] = Rule("unexposed_expr")
default_rules_db["DeclarationReferenceExpression"] = Rule("decl_ref_expr")
default_rules_db["MemberReferenceExpression"] = Rule("member_ref_expr")
default_rules_db["CallExpression"] = Rule("call_expr")
default_rules_db["BlockExpression"] = Rule("block_expr")
default_rules_db["IntegerLiteral"] = Rule("integer_literal")
default_rules_db["FloatingLiteral"] = Rule("floating_literal")
default_rules_db["ImaginaryLiteral"] = Rule("imaginary_literal")
default_rules_db["StringLiteral"] = Rule("string_literal")
default_rules_db["CharacterLiteral"] = Rule("character_literal")
default_rules_db["ParenExpression"] = Rule("paren_expr")
default_rules_db["UnaryOperator"] = Rule("unary_operator")
default_rules_db["ArraySubscriptExpression"] = Rule("array_subscript_expr")
default_rules_db["BinaryOperator"] = Rule("binary_operator")
default_rules_db["CompoundAssignmentOperator"] = Rule("compound_assignment_operator")
default_rules_db["ConditionalOperator"] = Rule("conditional_operator")
default_rules_db["CstyleCastExpression"] = Rule("cstyle_cast_expr")
default_rules_db["CompoundLiteralExpression"] = Rule("compound_literal_expr")
default_rules_db["InitListExpression"] = Rule("init_list_expr")
default_rules_db["AddrLabelExpression"] = Rule("addr_label_expr")
default_rules_db["StatementExpression"] = Rule("stmtexpr")
default_rules_db["GenericSelectionExpression"] = Rule("generic_selection_expr")
default_rules_db["GnuNullExpression"] = Rule("gnu_null_expr")
default_rules_db["CxxStaticCastExpression"] = Rule("cxx_static_cast_expr")
default_rules_db["CxxDynamicCastExpression"] = Rule("cxx_dynamic_cast_expr")
default_rules_db["CxxReinterpretCastExpression"] = Rule("cxx_reinterpret_cast_expr")
default_rules_db["CxxConstCastExpression"] = Rule("cxx_const_cast_expr")
default_rules_db["CxxFunctionalCastExpression"] = Rule("cxx_functional_cast_expr")
default_rules_db["CxxTypeidExpression"] = Rule("cxx_typeid_expr")
default_rules_db["CxxBoolLiteralExpression"] = Rule("cxx_bool_literal_expr")
default_rules_db["CxxNullPointerLiteralExpression"] = Rule("cxx_null_ptr_literal_expr")
default_rules_db["CxxThisExpression"] = Rule("cxx_this_expr")
default_rules_db["CxxThrowExpression"] = Rule("cxx_throw_expr")
default_rules_db["CxxNewExpression"] = Rule("cxx_new_expr")
default_rules_db["CxxDeleteExpression"] = Rule("cxx_delete_expr")
default_rules_db["CxxUnaryExpression"] = Rule("cxx_unary_expr")
default_rules_db["PackExpansionExpression"] = Rule("pack_expansion_expr")
default_rules_db["SizeOfPackExpression"] = Rule("size_of_pack_expr")
default_rules_db["LambdaExpression"] = Rule("lambda_expr")
default_rules_db["ObjectBoolLiteralExpression"] = Rule("obj_bool_literal_expr")
default_rules_db["ObjectSelfExpression"] = Rule("obj_self_expr")
default_rules_db["UnexposedStatement"] = Rule("unexposed_stmt")
default_rules_db["LabelStatement"] = Rule("label_stmt")
default_rules_db["CompoundStatement"] = Rule("compound_stmt")
default_rules_db["CaseStatement"] = Rule("case_stmt")
default_rules_db["DefaultStatement"] = Rule("default_stmt")
default_rules_db["IfStatement"] = Rule("if_stmt")
default_rules_db["SwitchStatement"] = Rule("switch_stmt")
default_rules_db["WhileStatement"] = Rule("while_stmt")
default_rules_db["DoStatement"] = Rule("do_stmt")
default_rules_db["ForStatement"] = Rule("for_stmt")
default_rules_db["GotoStatement"] = Rule("goto_stmt")
default_rules_db["IndirectGotoStatement"] = Rule("indirect_goto_stmt")
default_rules_db["ContinueStatement"] = Rule("continue_stmt")
default_rules_db["BreakStatement"] = Rule("break_stmt")
default_rules_db["ReturnStatement"] = Rule("return_stmt")
default_rules_db["AsmStatement"] = Rule("asm_stmt")
default_rules_db["CxxCatchStatement"] = Rule("cxx_catch_stmt")
default_rules_db["CxxTryStatement"] = Rule("cxx_try_stmt")
default_rules_db["CxxForRangeStatement"] = Rule("cxx_for_range_stmt")
default_rules_db["MsAsmStatement"] = Rule("ms_asm_stmt")
default_rules_db["NullStatement"] = Rule("null_stmt")
default_rules_db["DeclarationStatement"] = Rule("decl_stmt")
default_rules_db["TranslationUnit"] = Rule("translation_unit")
default_rules_db["UnexposedAttribute"] = Rule("unexposed_attr")
default_rules_db["CxxFinalAttribute"] = Rule("cxx_final_attr")
default_rules_db["CxxOverrideAttribute"] = Rule("cxx_override_attr")
default_rules_db["AnnotateAttribute"] = Rule("annotate_attr")
default_rules_db["AsmLabelAttribute"] = Rule("asm_label_attr")
default_rules_db["PackedAttribute"] = Rule("packed_attr")
default_rules_db["PureAttribute"] = Rule("pure_attr")
default_rules_db["ConstAttribute"] = Rule("const_attr")
default_rules_db["NoduplicateAttribute"] = Rule("noduplicate_attr")
default_rules_db["PreprocessingDirective"] = Rule("preprocessing_directive")
default_rules_db["MacroDefinition"] = Rule("macro_definition")
default_rules_db["MacroInstantiation"] = Rule("macro_instantiation")
default_rules_db["InclusionDirective"] = Rule("inclusion_directive")


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
            "write C/C++ code that adheres to adhere some naming conventions. It automates the "
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

        self.parser.add_argument('-d', '--dump', dest='dump', help="Dump all available options")

        self.parser.add_argument('-o', '--output', dest='output', help='''output file name where
                                 naming convenction vialoations will be stored''')

        self.parser.add_argument('-x', '--extension', dest='extention', help='''File extentions
                                 that are applicable for naming convection validation''')

        self.parser.add_argument("path", metavar="FILE", nargs="+", type=str,
                                 help='''Path of file or directory''')

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

            cursor_kinds = {kind.name.lower(): kind for kind in CursorKind.get_all_kinds()}

            for (user_kind, pattern_str) in style_rules.items():
                try:
                    clang_kind_str = default_rules_db[user_kind].clang_kind_str
                    clang_kind = cursor_kinds[clang_kind_str]
                    if clang_kind:
                        self.__rule_db[user_kind] = default_rules_db[user_kind]
                        self.__rule_db[user_kind].pattern_str = pattern_str
                        self.__rule_db[user_kind].pattern = re.compile(pattern_str)
                        self.__clang_db[clang_kind] = cursor_kind_map[clang_kind_str]

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

                if child.kind in special_kind:
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


def is_cxx_file(filename):
    path, extension = os.path.splitext(filename)
    if extension in file_extensions:
        return True
    return False


def validate_file(validator, filename):
    if is_cxx_file(filename):
        print("Validating {}".format(filename))
        validator.validate(filename)


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
    for path in op.next_file():
        if not os.path.exists(path):
            sys.stderr.write("File '{}' does not exist\n".format(path))
        elif os.path.isfile(path):
            validate_file(v, path)
        elif os.path.isdir(path):
            for (root, subdirs, files) in os.walk(path):
                for filename in files:
                    validate_file(v, root + '/' + filename)

                if not op.args.recurse:
                    break
