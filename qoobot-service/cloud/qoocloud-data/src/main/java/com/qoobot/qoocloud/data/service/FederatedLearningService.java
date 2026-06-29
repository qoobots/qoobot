package com.qoobot.qoocloud.data.service;

import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * FederatedLearningService — 联邦学习聚合服务
 * 端侧训练梯度聚合、差分隐私保护、全局模型更新
 */
@Service
public class FederatedLearningService {

    private final Map<String, TrainingRound> activeRounds = new ConcurrentHashMap<>();
    private final PrivacyFilterService privacyFilter;

    public FederatedLearningService(PrivacyFilterService privacyFilter) {
        this.privacyFilter = privacyFilter;
    }

    /**
     * Start a new federated learning round.
     */
    public String startRound(String modelName, int minParticipants, double targetEpsilon) {
        String roundId = UUID.randomUUID().toString();
        TrainingRound round = new TrainingRound();
        round.roundId = roundId;
        round.modelName = modelName;
        round.minParticipants = minParticipants;
        round.targetEpsilon = targetEpsilon;
        round.createdAt = System.currentTimeMillis();
        activeRounds.put(roundId, round);
        return roundId;
    }

    /**
     * Submit gradients from a client device.
     */
    public synchronized void submitGradients(String roundId, String deviceId,
                                               List<Double> gradients) {
        TrainingRound round = activeRounds.get(roundId);
        if (round == null) return;

        round.participantGradients.put(deviceId, gradients);
        round.participantCount++;

        // Check if we have enough participants to aggregate
        if (round.participantCount >= round.minParticipants) {
            aggregate(roundId);
        }
    }

    /**
     * Aggregate gradients using Federated Averaging (FedAvg).
     */
    public Map<String, Object> aggregate(String roundId) {
        TrainingRound round = activeRounds.get(roundId);
        if (round == null || round.participantGradients.isEmpty()) {
            return Map.of("status", "insufficient_data");
        }

        // Compute average of all participant gradients
        int numLayers = round.participantGradients.values().iterator().next().size();
        double[] aggregated = new double[numLayers];

        for (List<Double> grads : round.participantGradients.values()) {
            for (int i = 0; i < Math.min(numLayers, grads.size()); i++) {
                aggregated[i] += grads.get(i);
            }
        }

        int n = round.participantCount;
        for (int i = 0; i < numLayers; i++) {
            aggregated[i] /= n;
        }

        // Apply differential privacy
        double sensitivity = computeSensitivity(round.participantGradients.values());
        double epsilon = round.targetEpsilon;

        for (int i = 0; i < numLayers; i++) {
            aggregated[i] = privacyFilter.applyDifferentialPrivacy(
                aggregated[i], sensitivity, epsilon);
        }

        round.aggregatedGradients = aggregated;
        round.completedAt = System.currentTimeMillis();

        Map<String, Object> result = new HashMap<>();
        result.put("roundId", roundId);
        result.put("modelName", round.modelName);
        result.put("participants", n);
        result.put("gradientSize", numLayers);
        result.put("epsilon", epsilon);
        result.put("status", "completed");

        return result;
    }

    /**
     * Get the current status of a training round.
     */
    public Map<String, Object> getRoundStatus(String roundId) {
        TrainingRound round = activeRounds.get(roundId);
        if (round == null) {
            return Map.of("status", "not_found");
        }

        Map<String, Object> status = new HashMap<>();
        status.put("roundId", round.roundId);
        status.put("modelName", round.modelName);
        status.put("participantCount", round.participantCount);
        status.put("minParticipants", round.minParticipants);
        status.put("completed", round.aggregatedGradients != null);
        return status;
    }

    private double computeSensitivity(Collection<List<Double>> allGradients) {
        // L2 sensitivity: maximum change when one participant's data is removed
        double maxNorm = 0.0;
        for (List<Double> grads : allGradients) {
            double norm = 0.0;
            for (double g : grads) {
                norm += g * g;
            }
            maxNorm = Math.max(maxNorm, Math.sqrt(norm));
        }
        return maxNorm * 2.0;  // Conservative estimate
    }

    private static class TrainingRound {
        String roundId;
        String modelName;
        int minParticipants;
        double targetEpsilon;
        long createdAt;
        long completedAt;
        int participantCount = 0;
        Map<String, List<Double>> participantGradients = new HashMap<>();
        double[] aggregatedGradients;
    }
}
