package com.qoobot.qoocommunity.academy.service;

import com.qoobot.qoocommunity.academy.domain.Certification;
import com.qoobot.qoocommunity.academy.domain.UserCertification;
import com.qoobot.qoocommunity.academy.repository.CertificationRepository;
import com.qoobot.qoocommunity.academy.repository.UserCertificationRepository;
import com.qoobot.qoocommunity.common.exception.QooCommunityException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 认证考试服务。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ExamService {

    private final CertificationRepository certificationRepository;
    private final UserCertificationRepository userCertificationRepository;

    /**
     * 获取可用认证列表
     */
    public List<Certification> getActiveCertifications() {
        return certificationRepository.findByIsActiveTrue();
    }

    /**
     * 获取认证详情
     */
    public Certification getCertification(Long id) {
        return certificationRepository.findById(id)
                .orElseThrow(() -> QooCommunityException.notFound("Certification not found"));
    }

    /**
     * 提交考试答案并评分
     */
    @Transactional
    public UserCertification submitExam(String userId, Long certId, List<Map<String, String>> answers) {
        Certification cert = certificationRepository.findById(certId)
                .orElseThrow(() -> QooCommunityException.notFound("Certification not found"));

        if (!cert.getIsActive()) {
            throw QooCommunityException.badRequest("Certification is not active");
        }

        // 检查是否已通过
        userCertificationRepository.findByUserIdAndCertificationId(userId, certId)
                .ifPresent(existing -> {
                    if (existing.getPassed()) {
                        throw QooCommunityException.badRequest("Already passed this certification");
                    }
                });

        // 简化的评分逻辑（实际应比对题目答案库）
        int score = calculateScore(answers, cert.getQuestionCount());

        UserCertification result = new UserCertification();
        result.setUserId(userId);
        result.setCertificationId(certId);
        result.setScore(score);
        result.setPassed(score >= cert.getPassScore());
        result.setIssuedAt(LocalDateTime.now());

        if (result.getPassed()) {
            result.setExpiresAt(LocalDateTime.now().plusMonths(cert.getValidityMonths()));
        }

        return userCertificationRepository.save(result);
    }

    /**
     * 简易评分（生产环境应查询题目答案库）
     */
    private int calculateScore(List<Map<String, String>> answers, int totalQuestions) {
        if (answers == null || answers.isEmpty()) return 0;
        // 生产环境：比对正确答案计算分数
        // 此处返回模拟分数
        int correct = Math.min(answers.size(), totalQuestions);
        return (int) ((double) correct / totalQuestions * 100);
    }

    /**
     * 获取用户认证记录
     */
    public List<UserCertification> getUserCertifications(String userId) {
        return userCertificationRepository.findByUserId(userId);
    }
}
