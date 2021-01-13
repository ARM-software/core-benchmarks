"""Generate and write source files which compile into a benchmark. """
import os
import re
import math
from collections import deque, defaultdict
from frontend.code_generator import user_callgraph
from typing import Set, Dict, Collection, Deque


class SourceGenerator:
    """Generate and write source files which compile into a benchmark.

        Typical usage example:

        sg = SourceGenerator('/tmp/generated/', callgraph)
        sg.write_files()
    """

    def __init__(self,
                 output_directory: str,
                 callgraph: user_callgraph.Callgraph,
                 header_file: str = 'headers.h',
                 main_file: str = 'main.c',
                 benchmark_name: str = 'benchmark') -> None:
        self.output_dir: str = output_directory
        self.callgraph: user_callgraph.Callgraph = callgraph
        self.header_file: str = header_file
        self.main_file: str = main_file
        self.benchmark_name: str = benchmark_name

    def write_files(self, num_files: int = None) -> None:
        '''Create all source files

        Args:
            num_files: Number of C files to write functions to. Value of None
              let's the program decide
        '''
        self.write_main()
        self.write_headers()
        function_files = self.write_functions(num_files)
        self.write_makefile(function_files)

    def write_main(self) -> None:
        template = self._build_main_template()
        main_path = self.append_path_to_output_dir(self.main_file)
        with open(main_path, 'w') as f:
            f.write(template)

    def _build_main_template(self) -> str:
        header = self.get_header_import_string()
        vars_def = self.callgraph.format_vars_definition()
        function_call = self.callgraph.function_call_signature_for(
            self.callgraph.entry_point)
        variable = 'loops'
        arg_template = self._build_arg_template(variable)
        template = (f'#include <unistd.h>\n'
                    f'#include <stdio.h>\n'
                    f'#include <stdlib.h>\n'
                    f'{header}\n\n'
                    f'{vars_def}\n'
                    'int main(int argc, char **argv) {\n'
                    f'unsigned long {variable} = 1;\n'
                    f'{arg_template}\n'
                    f'for (int i = 0; i < {variable}; i++)'
                    ' {\n'
                    f'{function_call}();\n'
                    '}\n'
                    '}\n')
        return template

    def get_header_import_string(self) -> str:
        return f'#include "{self.header_file}"'

    def _build_arg_template(self, variable) -> str:
        template = (
            'int c;\n'
            'while ((c = getopt(argc, argv, "l:")) != -1) {\n'
            'switch (c) {\n'
            "case 'l':\n"
            f'{variable} = strtoul(optarg, NULL, 0);\n'
            'break;\n'
            'default:\n'
            'printf("Invalid argument provided. Valid arguments: -l\\n");\n'
            'exit(1);\n'
            '}\n'
            '}')
        return template

    def append_path_to_output_dir(self, path) -> str:
        return os.path.join(self.output_dir, path)

    def write_headers(self) -> None:
        header_path = self.append_path_to_output_dir(self.header_file)
        with open(header_path, 'w') as f:
            f.write(self.callgraph.format_vars_declaration())
            f.write(self.callgraph.format_headers())

    def write_functions(self, num_files: int = None) -> Collection[str]:
        ''' Creates files containing function definitions.

        Files are expected to start with headers followed by functions
        definitions.

        e.g.
            #include <headers.h>

            function_2() {...}
            function_3() {...}
        '''
        grouper = FileFunctionMapper(self.callgraph)
        file_to_function_name_mapping = \
            grouper.create_file_to_functions_mapping( num_files)
        for function_file, functions in file_to_function_name_mapping.items():
            self.write_header_import_to_new_file(function_file)
            for function_name in functions:
                self.write_function_to_existing_file(function_name,
                                                     function_file)
        return file_to_function_name_mapping.keys()

    def write_header_import_to_new_file(self, path) -> None:
        path = self.append_path_to_output_dir(path)
        if os.path.exists(path):
            raise RuntimeError(f'{path} already exists')
        header = self.get_header_import_string()
        with open(path, 'w') as f:
            f.write(f'{header}\n\n')

    def write_function_to_existing_file(self, function_name: int,
                                        path: str) -> None:
        path = self.append_path_to_output_dir(path)
        string = self.callgraph.format_function(function_name)
        with open(path, 'a') as f:
            f.write(string + '\n')

    def write_makefile(self, function_files: Collection[str]) -> None:
        makefile_path = self.append_path_to_output_dir('Makefile')
        with open(makefile_path, 'w') as f:
            dependencies = self.get_object_files_to_c_files_mapping(
                function_files)
            prefetch_ifdef = ('ifdef ENABLE_PREFETCH\n'
                              '\tDENABLE_PREFETCH = -DENABLE_CODE_PREFETCH\n'
                              'endif\n\n')
            cflags = ['$(DENABLE_PREFETCH)', '-O0']
            cflags_str = ' '.join(cflags)
            obj_files = ' '.join(dependencies.keys())
            string = (
                f'{prefetch_ifdef}'
                f'{self.benchmark_name}: {obj_files}\n'
                f'\t$(CC) -o {self.benchmark_name} {obj_files} {cflags_str}\n'
                '\n')
            for obj_file, c_file in dependencies.items():
                string += f'{obj_file}: {c_file}\n'
                string += f'\t$(CC) -c -o {obj_file} {c_file} {cflags_str}\n\n'
            string += f'clean:\n\trm *.o {self.benchmark_name}\n'
            f.write(string)

    def get_object_files_to_c_files_mapping(
            self, c_files: Collection[str]) -> Dict[str, str]:
        result = {}
        for func_file in c_files:
            obj_file = re.sub(r'\.c', r'.o', func_file)
            result[obj_file] = func_file
        result['main.o'] = 'main.c'
        return result


class FileFunctionMapper:
    """Maps filenames to groups of functions.

    Filenames are not created or written to.
    """

    def __init__(self, callgraph):
        self.function_files = set()
        self.callgraph = callgraph

    def create_file_to_functions_mapping(self,
                                         num_files: int = None
                                        ) -> Dict[str, Set[int]]:
        ''' Create a file name to set of functions mapping

        Args:
            num_files: ideal number of files to split functions across
        '''
        result = self._group_functions_by_control_flow()
        if num_files:
            result = self._split_function_groups(num_files, result)
        return result

    def _group_functions_by_control_flow(self) -> Dict[str, Set[int]]:
        ''' Group functions that call each other and assign them a file name

        Returns:
            A dict mapping file names to a set of function names
        '''

        visited_functions = set()
        function_to_file_mapping = {}
        file_to_function_mapping: Dict[str, Set[int]] = defaultdict(set)
        to_visit = deque(self.callgraph.functions.keys())
        while to_visit:
            function_name = to_visit.popleft()
            if function_name in visited_functions:
                continue
            visited_functions.add(function_name)
            if function_name not in function_to_file_mapping:
                function_to_file_mapping[
                    function_name] = self._next_function_file()
            function_file = function_to_file_mapping[function_name]
            file_to_function_mapping[function_file].add(function_name)
            for target in self.callgraph.direct_call_targets_for_function(
                    function_name):
                if (target in self.callgraph.functions and
                        target not in visited_functions):
                    function_to_file_mapping[target] = function_file
                    to_visit.appendleft(target)
        return file_to_function_mapping

    def _next_function_file(self):
        current_len = len(self.function_files)
        new_file = f'{current_len}.c'
        self.function_files.add(new_file)
        return new_file

    def _split_function_groups(
            self, splits: int,
            file_to_function_mapping: Dict[str,
                                           Set[int]]) -> Dict[str, Set[int]]:
        functions_per_split = math.ceil(len(self.callgraph.functions) / splits)
        self._clear_function_files()
        current_function_file = self._next_function_file()
        result: Dict[str, Set[int]] = defaultdict(set)

        current_function_count = 0
        functions_groups: Deque[Collection[int]] = deque(
            file_to_function_mapping.values())
        while functions_groups:
            functions = functions_groups.popleft()
            if current_function_count + len(functions) <= functions_per_split:
                current_function_count += len(functions)
                for function_name in functions:
                    result[current_function_file].add(function_name)
            else:
                functions_list = list(functions)
                first_functions_list = functions_list[:functions_per_split]
                second_functions_list = functions_list[functions_per_split:]
                for function_name in first_functions_list:
                    result[current_function_file].add(function_name)
                current_function_file = self._next_function_file()
                current_function_count = 0
                functions_groups.appendleft(second_functions_list)
        return result

    def _clear_function_files(self):
        self.function_files = set()
