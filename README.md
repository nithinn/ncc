## ncc

C/C++ Naming convention checker (ncc)

ncc is a development tool to help programmers write C/C++ code that adheres to
a some naming conventions. It automates the process of checking C/C++ code to
spare humans of this boring (but important) task. This makes it ideal for
projects that want to enforce a coding standard.

## Status
Work In Progress

## Requirements

* python2
* python-clang
* python-yaml

## Usage

    ncc.py [OPTIONS...] FILE [FILE ...]

For standalone files:

    ncc.py --style=styles/ncc.style examples/test.cpp

For recursing through a directory structure:

    ncc.py --style=styles/ncc.style --recurse examples

For detailed description of all options:

    ncc.py --help

## Style Defintion

Style for c/c++ constructs are defined by regular expresssions. For e.g the below rules say that
a struct can have any character, a class name should begin with 'C', and a class member variable
should begin with m_

    StructName: '^.*$'
    ClassName: '^C.*$'
    ClassMemberVariable: '^m_.*$'
    FunctionName: '^[A-Z].*$'
    Namespace: '^.*$'

## Sample Output

    examples/test.h:5:7: "Test" does not match "^C.*$" associated with ClassName
    examples/test.hpp:12:9: "t" does not match "^m_.*$" associated with ClassMemberVariable
    Total number of errors = 2

## License

Copyright © 2018 Nithin Nellikunnu

Distributed under the MIT License (MIT).

## Thank You
Daniel J. Hofmann
