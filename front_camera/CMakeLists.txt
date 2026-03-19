cmake_minimum_required(VERSION 3.5)
project(my_build VERSION 2.0.0)

## Project Options
option(BUILD_EXAMPLES "Build examples" ON)

## Set compiler to use c++ 17 features
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Threads REQUIRED)

include_directories(
    /home/unitree/unitree_sdk2/install/include
#     /usr/local/include
)

add_executable(front_camera_test src/front_camera_test.cpp)
add_library(front_camera SHARED src/front_camera.cpp)

add_library(ddsc SHARED IMPORTED GLOBAL)
set_target_properties(ddsc PROPERTIES
        IMPORTED_LOCATION /home/unitree/unitree_sdk2/install/lib/libddsc.so)
        # IMPORTED_LOCATION /usr/local/lib/libddsc.so)
set_target_properties(ddsc PROPERTIES IMPORTED_NO_SONAME TRUE)
target_link_libraries(ddsc INTERFACE Threads::Threads)

add_library(ddscxx SHARED IMPORTED GLOBAL)
set_target_properties(ddscxx PROPERTIES
        IMPORTED_LOCATION /home/unitree/unitree_sdk2/install/lib/libddscxx.so)
        # IMPORTED_LOCATION /usr/local/lib/libddscxx.so)
set_target_properties(ddscxx PROPERTIES IMPORTED_NO_SONAME TRUE)
target_link_libraries(ddscxx INTERFACE Threads::Threads)
target_include_directories(ddscxx INTERFACE
        $<BUILD_INTERFACE:/home/unitree/unitree_sdk2/install/include/ddscxx>
        # $<BUILD_INTERFACE:/usr/local/include/ddscxx>
        )

add_library(unitree_sdk2 STATIC IMPORTED GLOBAL)
set_target_properties(unitree_sdk2 PROPERTIES
        IMPORTED_LOCATION /home/unitree/unitree_sdk2/install/lib/libunitree_sdk2.a)

target_link_libraries(front_camera_test unitree_sdk2 ddscxx ddsc)
target_link_libraries(front_camera unitree_sdk2 ddscxx ddsc)