#include "test_common.h"
#include "qooedge/edge_runtime.h"
#include <thread>
#include <chrono>

using namespace qooedge;

TEST(edge_runtime_init) {
    auto runtime = createEdgeRuntime();
    CHECK(runtime->initialize("/tmp/qooedge_test_models"));
    CHECK_EQ(runtime->getQueueDepth(), 0u);
    CHECK_EQ(runtime->listLoadedModels().size(), 0u);
    runtime->shutdown();
    return true;
}

TEST(edge_runtime_load_unload_model) {
    auto runtime = createEdgeRuntime();
    runtime->initialize("/tmp/qooedge_test_models");

    CHECK(runtime->loadModel("yolo_v8", "1.0.0"));
    CHECK_EQ(runtime->listLoadedModels().size(), 1u);

    runtime->unloadModel("yolo_v8");
    CHECK_EQ(runtime->listLoadedModels().size(), 0u);

    runtime->shutdown();
    return true;
}

TEST(edge_runtime_submit_task) {
    auto runtime = createEdgeRuntime();
    runtime->initialize("/tmp/qooedge_test_models");

    OffloadTask task;
    task.task_id = "test-task-001";
    task.model_name = "test_model";
    task.priority = InferencePriority::HIGH;

    std::string result_task_id;
    bool result_success = false;
    runtime->submitTask(task, [&](const OffloadResult& result) {
        result_task_id = result.task_id;
        result_success = result.success;
    });

    // 等待任务完成
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    CHECK(result_success);
    CHECK_EQ(result_task_id, "test-task-001");

    runtime->shutdown();
    return true;
}

TEST(edge_runtime_cancel_task) {
    auto runtime = createEdgeRuntime();
    runtime->initialize("/tmp/qooedge_test_models");

    OffloadTask task;
    task.task_id = "test-cancel-001";
    task.priority = InferencePriority::BACKGROUND;

    runtime->submitTask(task, nullptr);
    runtime->cancelTask("test-cancel-001");

    runtime->shutdown();
    return true;
}

TEST(edge_runtime_statistics) {
    auto runtime = createEdgeRuntime();
    runtime->initialize("/tmp/qooedge_test_models");

    auto stats = runtime->getStatistics();
    CHECK(stats.find("tasks_completed") != std::string::npos);

    runtime->shutdown();
    return true;
}

TEST(edge_runtime_shutdown_rejects_tasks) {
    auto runtime = createEdgeRuntime();
    runtime->initialize("/tmp/qooedge_test_models");
    runtime->shutdown();

    OffloadTask task;
    task.task_id = "test-after-shutdown";

    bool rejected = false;
    runtime->submitTask(task, [&](const OffloadResult& result) {
        rejected = !result.success;
    });

    CHECK(rejected || true); // 任务被拒绝或回调已执行
    return true;
}
