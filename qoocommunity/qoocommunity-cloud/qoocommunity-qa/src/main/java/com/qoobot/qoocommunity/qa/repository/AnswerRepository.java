package com.qoobot.qoocommunity.qa.repository;

import com.qoobot.qoocommunity.qa.domain.Answer;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AnswerRepository extends JpaRepository<Answer, Long> {

    List<Answer> findByQuestionIdOrderByVoteScoreDesc(Long questionId);

    long countByQuestionId(Long questionId);

    long countByUserId(String userId);
}
