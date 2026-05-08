cmake_minimum_required(VERSION 3.16)
project(frankenstein-engine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(LLAMA_ROOT "/home/nxyme/llama.cpp")
set(LLAMA_BUILD_DIR "${LLAMA_ROOT}/build")
set(LLAMA_INCLUDE_DIR "${LLAMA_ROOT}/include")
set(LLAMA_GGML_INCLUDE_DIR "${LLAMA_ROOT}/ggml/include")
set(LLAMA_COMMON_DIR "${LLAMA_ROOT}/common")
set(LLAMA_BIN_DIR "${LLAMA_BUILD_DIR}/bin")
set(LLAMA_VENDOR_DIR "${LLAMA_ROOT}/vendor")

include_directories(
    ${LLAMA_INCLUDE_DIR}
    ${LLAMA_GGML_INCLUDE_DIR}
    ${LLAMA_COMMON_DIR}
    ${LLAMA_VENDOR_DIR}
)

link_directories(
    ${LLAMA_BIN_DIR}
    ${LLAMA_BUILD_DIR}/common
    ${LLAMA_BUILD_DIR}/vendor/cpp-httplib
)

# Find httplib library
set(HTTPLIB_PATH "/home/nxyme/llama.cpp/build/vendor/cpp-httplib/libcpp-httplib.a")

add_executable(frankenstein-engine engine.cpp)

target_link_libraries(frankenstein-engine PRIVATE 
    common
    llama
    ggml
    ggml-base
    ggml-cpu
    ggml-cuda
    pthread
    m
    ${HTTPLIB_PATH}
    ssl
    crypto
)

target_compile_options(frankenstein-engine PRIVATE -O3 -march=native -fPIC)