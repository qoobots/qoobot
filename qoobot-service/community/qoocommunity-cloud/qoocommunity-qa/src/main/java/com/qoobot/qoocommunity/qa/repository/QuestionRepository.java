package com.qoobot.qoocommunity.qa.repository;

import com.qoobot.qoocommunity.qa.domain.Question;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface QuestionRepository extends JpaRepository<Question, Long> {

    Page<Question> findAllByOrderByCreatedAtDesc(Pageable pageable);

    @Query("SELECT q FROM Question q WHERE q.isSolved = false ORDER BY q.voteScore DESC")
    Page<Question> findUnanswered(Pageable pageable);

    @Query("SELECT q FROM Question q WHERE LOWER(q.title) LIKE LOWER(CONCAT('%', :keyword, '%')) OR LOWER(q.content) LIKE LOWER(CONCAT('%', :keyword, '%'))")
    Page<Question> searchByKeyword(@Param("keyword") String keyword, Pageable pageable);

    long countByUserId(String userId);
}
