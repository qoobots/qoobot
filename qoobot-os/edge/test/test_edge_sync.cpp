#include "test_common.h"
#include "qooedge/edge_sync.h"
#include <thread>
#include <chrono>
#include <atomic>

using namespace qooedge;

TEST(edge_sync_init) {
    auto sync = createEdgeSync();
    CHECK(sync->initialize("https://cloud.qoobot.io/api/sync", "device-001"));
    return true;
}

TEST(edge_sync_set_sync_policy) {
    auto sync = createEdgeSync();
    sync->initialize("https://cloud.qoobot.io/api/sync", "device-001");

    // 设置为 FULL 策略
    sync->setSyncPolicy(SyncStrategy::FULL);
    return true;
}

TEST(edge_sync_set_network_constraints) {
    auto sync = createEdgeSync();
    sync->initialize("https://cloud.qoobot.io/api/sync", "device-001");

    // 仅 WiFi + 仅充电时同步
    sync->setNetworkConstraints(true, true);
    return true;
}

TEST(edge_sync_set_sync_interval) {
    auto sync = createEdgeSync();
    sync->initialize("https://cloud.qoobot.io/api/sync", "device-001");

    sync->setSyncInterval(600);
    return true;
}

TEST(edge_sync_start_and_get_active_syncs) {
    auto sync = createEdgeSync();
    sync->initialize("https://cloud.qoobot.io/api/sync", "device-001");

    SyncTask task;
    task.sync_id = "sync-test-001";
    task.resource_path = "/models/yolo_v8.qoomodel";
    task.direction = SyncDirection::DOWNLOAD;
    task.strategy = SyncStrategy::INCREMENTAL;
    task.data_size_bytes = 1024 * 1024;  // 1 MB
    task.checksum = "abc123";

    sync->startSync(task, nullptr);

    // 等待同步开始
    std::this_thread::sleep_for(std::chrono::milliseconds(50));

    auto active = sync->getActiveSyncs();
    CHECK_EQ(active.size(), 1u);
    CHECK_EQ(active[0].sync_id, "sync-test-001");

    return true;
}

TEST(edge_sync_start_with_callback) {
    auto sync = createEdgeSync();
    sync->initialize("https://cloud.qoobot.io/api/sync", "device-001");

    SyncTask task;
    task.sync_id = "sync-cb-001";
    task.resource_path = "/maps/floor1.bin";
    task.direction = SyncDirection::UPLOAD;
    task.strategy = SyncStrategy::FULL;
    task.data_size_bytes = 512 * 1024;  // 512 KB
    task.checksum = "def456";

    std::atomic<int> callback_count{0};
    double last_progress = -1.0;
    sync->startSync(task, [&](const SyncProgress& progress) {
        callback_count++;
        last_progress = progress.progress;
    });

    // 等待同步完成 (simulateSync 约 10*100ms = 1s)
    std::this_thread::sleep_for(std::chrono::milliseconds(1500));

    CHECK(callback_count > 0);
    CHECK(last_progress >= 0.0);
    CHECK(last_progress <= 1.0);

    // 同步完成后应从活跃列表中移除
    auto active = sync->getActiveSyncs();
    CHECK_EQ(active.size(), 0u);

    return true;
}

TEST(edge_sync_cancel_sync) {
    auto sync = createEdgeSync();
    sync->initialize("https://cloud.qoobot.io/api/sync", "device-001");

    SyncTask task;
    task.sync_id = "sync-cancel-001";
    task.resource_path = "/logs/robot.log";
    task.direction = SyncDirection::UPLOAD;
    task.strategy = SyncStrategy::LAZY;
    task.data_size_bytes = 10 * 1024 * 1024;  // 10 MB (慢)
    task.checksum = "ghi789";

    sync->startSync(task, nullptr);

    // 短暂等待后取消
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    sync->cancelSync("sync-cancel-001");

    // 等待模拟线程检查取消标志
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    return true;
}

TEST(edge_sync_check_for_update_new_resource) {
    auto sync = createEdgeSync();
    sync->initialize("https://cloud.qoobot.io/api/sync", "device-001");

    // 新资源（本地不存在）应该需要更新
    bool has_update = sync->checkForUpdate("/models/new_model.qoomodel");
    CHECK(has_update);

    return true;
}

TEST(edge_sync_resource_version_after_sync) {
    auto sync = createEdgeSync();
    sync->initialize("https://cloud.qoobot.io/api/sync", "device-001");

    // 初始无版本
    auto version_before = sync->getResourceVersion("/models/versioned.qoomodel");
    CHECK(version_before.empty());

    SyncTask task;
    task.sync_id = "sync-version-001";
    task.resource_path = "/models/versioned.qoomodel";
    task.direction = SyncDirection::DOWNLOAD;
    task.strategy = SyncStrategy::FULL;
    task.data_size_bytes = 2048;
    task.checksum = "v2.0.0";

    sync->startSync(task, nullptr);

    // 等待同步完成
    std::this_thread::sleep_for(std::chrono::milliseconds(1500));

    // 同步完成后版本号应为 checksum
    auto version_after = sync->getResourceVersion("/models/versioned.qoomodel");
    CHECK_EQ(version_after, "v2.0.0");

    // 检查更新应返回 false（版本一致）
    bool has_update = sync->checkForUpdate("/models/versioned.qoomodel");
    CHECK(!has_update);

    return true;
}

TEST(edge_sync_force_sync_now) {
    auto sync = createEdgeSync();
    sync->initialize("https://cloud.qoobot.io/api/sync", "device-001");

    // 先注册资源版本
    SyncTask task;
    task.sync_id = "sync-pre-001";
    task.resource_path = "/config/policy.yaml";
    task.direction = SyncDirection::DOWNLOAD;
    task.strategy = SyncStrategy::INCREMENTAL;
    task.data_size_bytes = 4096;
    task.checksum = "v1.0";

    sync->startSync(task, nullptr);
    std::this_thread::sleep_for(std::chrono::milliseconds(1500));

    // 确认版本已注册
    auto version = sync->getResourceVersion("/config/policy.yaml");
    CHECK_EQ(version, "v1.0");

    // 验证 forceSyncNow 不会崩溃
    sync->forceSyncNow();

    return true;
}

TEST(edge_sync_multiple_concurrent_syncs) {
    auto sync = createEdgeSync();
    sync->initialize("https://cloud.qoobot.io/api/sync", "device-001");

    // 启动多个并发同步
    for (int i = 0; i < 3; i++) {
        SyncTask task;
        task.sync_id = "sync-multi-" + std::to_string(i);
        task.resource_path = "/data/file_" + std::to_string(i) + ".bin";
        task.direction = i % 2 == 0 ? SyncDirection::DOWNLOAD : SyncDirection::UPLOAD;
        task.strategy = static_cast<SyncStrategy>(i % 4);
        task.data_size_bytes = 1024 * (i + 1);
        task.checksum = "chk" + std::to_string(i);

        sync->startSync(task, nullptr);
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    // 应该有 3 个活跃同步
    auto active = sync->getActiveSyncs();
    CHECK_EQ(active.size(), 3u);

    return true;
}
