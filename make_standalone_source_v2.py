#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1])

def remove_braced_block(text: str, marker: str) -> str:
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"marker not found: {marker}")
    brace = text.find("{", start)
    if brace < 0:
        raise RuntimeError(f"opening brace not found: {marker}")
    depth = 0
    i = brace
    in_str = False
    esc = False
    while i < len(text):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    while end < len(text) and text[end] in " \t\r\n":
                        end += 1
                    return text[:start] + text[end:]
        i += 1
    raise RuntimeError(f"unterminated block: {marker}")

# Standalone header: no Python/pybind dependency at target runtime.
(root / "lib" / "library.h").write_text(r"""#ifndef EXI_CONVERTER_LIBRARY_H
#define EXI_CONVERTER_LIBRARY_H

#include <cstdint>
#include <string>
#include <vector>

class ExiCodec {
public:
    ExiCodec();
    std::string decode(const std::vector<uint8_t>& byte_stream, std::string ns);
    std::vector<uint8_t> encode(const std::string& json_str, const std::string& ns);
};

#endif
""", encoding="utf-8")

# Upstream converter_tool/main.cpp relied on library.h indirectly bringing
# iostream/stdexcept. Our standalone header intentionally does not do that,
# so add the direct standard-library includes required by main.cpp.
main_path = root / "converter_tool" / "main.cpp"
maincpp = main_path.read_text(encoding="utf-8")
needed = "#include <iostream>\n#include <stdexcept>\n#include <string>\n"
if "#include <iostream>" not in maincpp:
    maincpp = needed + maincpp
main_path.write_text(maincpp, encoding="utf-8")

libcpp_path = root / "lib" / "library.cpp"
libcpp = libcpp_path.read_text(encoding="utf-8")

# Remove pybind headers.
lines = []
for line in libcpp.splitlines(True):
    if "pybind11/" in line:
        continue
    lines.append(line)
libcpp = "".join(lines)

# Remove Python module registration and Python-only wrappers.
libcpp = remove_braced_block(libcpp, "PYBIND11_MODULE(")
libcpp = remove_braced_block(libcpp, "pybind11::bytes ExiCodec::py_encode(")
libcpp = remove_braced_block(libcpp, "std::string ExiCodec::py_decode(")
libcpp_path.write_text(libcpp, encoding="utf-8")

# Replace upstream CMake with a target-runtime-Python-free standalone build.
(root / "CMakeLists.txt").write_text(r"""cmake_minimum_required(VERSION 3.10)
project(vsecc_exi_converter_standalone CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE OFF)

find_package(Python3 COMPONENTS Interpreter REQUIRED)

set(GENERATED_FILES_DIR ${CMAKE_BINARY_DIR}/generated)
file(MAKE_DIRECTORY ${GENERATED_FILES_DIR})

file(GLOB_RECURSE XSD_FILES ${PROJECT_SOURCE_DIR}/schemas/*.xsd)
file(GLOB_RECURSE GENERATOR_FILES ${PROJECT_SOURCE_DIR}/code_generator/*.py)

set(GENERATED_SOURCES)

macro(add_code_generator PROTOCOL_NAME SCHEMA_FILE)
    set(_srcs
        ${GENERATED_FILES_DIR}/${PROTOCOL_NAME}/enum_types.cpp
        ${GENERATED_FILES_DIR}/${PROTOCOL_NAME}/complex_types.cpp
        ${GENERATED_FILES_DIR}/${PROTOCOL_NAME}/body_message.cpp
    )
    set(_hdrs
        ${GENERATED_FILES_DIR}/${PROTOCOL_NAME}/enum_types.h
        ${GENERATED_FILES_DIR}/${PROTOCOL_NAME}/complex_types.h
        ${GENERATED_FILES_DIR}/${PROTOCOL_NAME}/body_message.h
    )
    add_custom_command(
        OUTPUT ${_srcs} ${_hdrs}
        COMMAND ${CMAKE_COMMAND} -E make_directory ${GENERATED_FILES_DIR}/${PROTOCOL_NAME}
        COMMAND ${Python3_EXECUTABLE}
            ${PROJECT_SOURCE_DIR}/code_generator/main.py
            --namespace=${PROTOCOL_NAME}
            --output_path=${GENERATED_FILES_DIR}/${PROTOCOL_NAME}/
            --schema_file=${PROJECT_SOURCE_DIR}/schemas/${SCHEMA_FILE}
        DEPENDS ${XSD_FILES} ${GENERATOR_FILES}
        VERBATIM
    )
    list(APPEND GENERATED_SOURCES ${_srcs})
endmacro()

add_code_generator(din_spec din_spec/V2G_CI_MsgDef.xsd)
add_code_generator(iso15118_2 iso15118_2/V2G_CI_MsgDef.xsd)
add_code_generator(app_protocol V2G_CI_AppProtocol.xsd)

file(GLOB_RECURSE BASE_SOURCES ${PROJECT_SOURCE_DIR}/lib/base/*.cpp)
file(GLOB_RECURSE TC_SOURCES ${PROJECT_SOURCE_DIR}/lib/type_conversion/*.cpp)

add_executable(converter_tool
    ${PROJECT_SOURCE_DIR}/converter_tool/main.cpp
    ${PROJECT_SOURCE_DIR}/lib/library.cpp
    ${BASE_SOURCES}
    ${TC_SOURCES}
    ${GENERATED_SOURCES}
)

target_include_directories(converter_tool PRIVATE
    ${PROJECT_SOURCE_DIR}/lib
    ${GENERATED_FILES_DIR}
)

target_compile_options(converter_tool PRIVATE -Os)
target_link_options(converter_tool PRIVATE -static)
""", encoding="utf-8")

print("Standalone source patch V2 applied")
