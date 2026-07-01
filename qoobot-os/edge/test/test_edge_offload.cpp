#include "test_common.h"
#include "qooedge/edge_offload.h"

using namespace qooedge;

TEST(edge_offload_init) {
    auto offload = createEdgeOffload();
    CHECK(offload->initialize("/etc/qooedge/offload.yaml"));
    CHECK(offload->isOfflineMode() == false);
    return true;
}

TEST(edge_offload_local_only_low_load) {
    auto offload = createEdgeOffload();
    offload->initialize("/etc/qooedge/offload.yaml");

    OffloadTask task;
    task.task_id = "test-001";
    task.priority = InferencePriority::NORMAL;
    task.deadline_ms = 500;

    NetworkBudget budget{10.0, 100.0, 0.5, 0.01, "wifi6e"};

    auto decision = offload->decide(task, 0.3, budget);
    CHECK_EQ(decision, OffloadDecision::LOCAL_ONLY);
    return true;
}

TEST(edge_offload_cloud_when_high_load) {
    auto offload = createEdgeOffload();
    offload->initialize("/etc/qooedge/offload.yaml");

    OffloadTask task;
    task.task_id = "test-002";
    task.priority = InferencePriority::NORMAL;
    task.deadline_ms = 500;

    NetworkBudget budget{5.0, 100.0, 0.5, 0.01, "wifi6e"};

    auto decision = offload->decide(task, 0.95, budget);
    CHECK_EQ(decision, OffloadDecision::CLOUD_ONLY);
    return true;
}

TEST(edge_offload_realtime_always_local) {
    auto offload = createEdgeOffload();
    offload->initialize("/etc/qooedge/offload.yaml");

    OffloadTask task;
    task.task_id = "test-003";
    task.priority = InferencePriority::REALTIME;

    NetworkBudget budget{1.0, 1000.0, 0.5, 0.0, "5g"};

    auto decision = offload->decide(task, 0.95, budget);
    CHECK_EQ(decision, OffloadDecision::LOCAL_ONLY);
    return true;
}

TEST(edge_offload_offline_mode) {
    auto offload = createEdgeOffload();
    offload->initialize("/etc/qooedge/offload.yaml");
    offload->setOfflineMode(true);
    CHECK(offload->isOfflineMode());

    OffloadTask task;
    task.task_id = "test-004";
    task.priority = InferencePriority::NORMAL;

    NetworkBudget budget{10.0, 100.0, 0.5, 0.01, "wifi6e"};

    auto decision = offload->decide(task, 0.95, budget);
    CHECK_EQ(decision, OffloadDecision::LOCAL_ONLY);
    return true;
}

TEST(edge_offload_network_budget) {
    auto offload = createEdgeOffload();
    offload->initialize("/etc/qooedge/offload.yaml");

    NetworkBudget budget{15.0, 200.0, 1.0, 0.02, "5g"};
    offload->updateNetworkBudget(budget);

    auto got = offload->getNetworkBudget();
    CHECK_CLOSE(got.rtt_ms, 15.0, 0.01);
    CHECK_CLOSE(got.bandwidth_mbps, 200.0, 0.01);

    return true;
}

TEST(edge_offload_batch_decision) {
    auto offload = createEdgeOffload();
    offload->initialize("/etc/qooedge/offload.yaml");

    std::vector<OffloadTask> tasks;
    for (int i = 0; i < 5; i++) {
        OffloadTask task;
        task.task_id = "batch-" + std::to_string(i);
        task.priority = InferencePriority::NORMAL;
        task.deadline_ms = 500;
        tasks.push_back(task);
    }

    NetworkBudget budget{10.0, 100.0, 0.5, 0.01, "wifi6e"};
    auto decisions = offload->decideBatch(tasks, 0.3, budget);

    CHECK_EQ(decisions.size(), 5u);
    return true;
}

TEST(edge_offload_decision_stats) {
    auto offload = createEdgeOffload();
    offload->initialize("/etc/qooedge/offload.yaml");

    OffloadTask task;
    task.task_id = "stats-test";
    task.priority = InferencePriority::NORMAL;
    task.deadline_ms = 500;

    NetworkBudget budget{10.0, 100.0, 0.5, 0.01, "wifi6e"};
    offload->decide(task, 0.3, budget);

    auto stats = offload->getDecisionStats();
    CHECK(stats.find("local_only") != std::string::npos);
    CHECK(stats.find("cloud_only") != std::string::npos);
    return true;
}

TEST(edge_offload_energy_budget) {
    auto offload = createEdgeOffload();
    offload->initialize("/etc/qooedge/offload.yaml");
    offload->setEnergyBudget(2.5);
    return true;
}
