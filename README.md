## ncc
C/C++ Naming convention checker

## Status
Work In Progress

## Requirements

* python2
* python-clang
* python-yaml

## Usage

For standalone files, with default compiler invocation:

    cncc --style=styles/ncc.style examples/test.cpp

## Style Defintion

Style for c/c++ constructs are defined by regular expresssions. For e.g the below rules say that
a struct can have any character, a class name should begin with 'C', and a class member variable
should begin with m_

    StructName: '^.*$'
    ClassName: '^C.*$'
    ClassMemberVariable: '^m_.*$'
    FunctionName: '^[A-Z].*$'
    Namespace: '^.*$'

## License

Copyright © 2018 Nithin Nellikunnu

Distributed under the MIT License (MIT).


## Thank You
Daniel J. Hofmann
