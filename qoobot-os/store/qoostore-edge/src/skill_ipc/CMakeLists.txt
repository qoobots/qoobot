# skill_ipc — 技能间通信
# 职责：Intent 广播、事件订阅、数据共享 (ContentProvider)、安全 IPC (Binder 对标)

set(SKILL_IPC_SOURCES
    skill_ipc.cpp
    intent_broker.cpp
)

add_library(qoostore_skill_ipc STATIC ${SKILL_IPC_SOURCES})

target_include_directories(qoostore_skill_ipc PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(qoostore_skill_ipc PUBLIC
    qoostore_edge_common
)

# 生产环境链接 Unix Domain Socket 或 D-Bus
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_libraries(qoostore_skill_ipc PUBLIC pthread)
endif()

target_compile_features(qoostore_skill_ipc PUBLIC cxx_std_17)
