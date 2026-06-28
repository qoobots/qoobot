add_library(svc_spatial SHARED
    spatial_service.cpp
    slam/laser_slam.cpp
    slam/loop_closure.cpp
    slam/global_optimizer.cpp
    semantic/room_classifier.cpp
    semantic/object_annotator.cpp
    semantic/topological_map.cpp
)

target_link_libraries(svc_spatial PUBLIC
    qoosvc_common
    Eigen3::Eigen
)

target_include_directories(svc_spatial PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_options(svc_spatial PRIVATE
    -Wall -Wextra
)
