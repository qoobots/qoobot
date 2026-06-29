package com.qoobot.qoocommunity.qa.service;

import com.qoobot.qoocommunity.common.dto.PageResponse;
import com.qoobot.qoocommunity.common.exception.QooCommunityException;
import com.qoobot.qoocommunity.qa.domain.Answer;
import com.qoobot.qoocommunity.qa.domain.Question;
import com.qoobot.qoocommunity.qa.domain.Vote;
import com.qoobot.qoocommunity.qa.repository.AnswerRepository;
import com.qoobot.qoocommunity.qa.repository.QuestionRepository;
import com.qoobot.qoocommunity.qa.repository.VoteRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class QuestionService {

    private final QuestionRepository questionRepository;
    private final AnswerRepository answerRepository;
    private final VoteRepository voteRepository;

    public PageResponse<Question> listQuestions(int page, int size) {
        Page<Question> result = questionRepository.findAllByOrderByCreatedAtDesc(PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public PageResponse<Question> listUnanswered(int page, int size) {
        Page<Question> result = questionRepository.findUnanswered(PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public PageResponse<Question> search(String keyword, int page, int size) {
        Page<Question> result = questionRepository.searchByKeyword(keyword, PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public Question getQuestion(Long id) {
        Question q = questionRepository.findById(id)
                .orElseThrow(() -> QooCommunityException.notFound("Question not found: " + id));
        q.setViewCount(q.getViewCount() + 1);
        questionRepository.save(q);
        return q;
    }

    @Transactional
    public Question createQuestion(String userId, String title, String content, String contentHtml) {
        Question q = new Question();
        q.setUserId(userId);
        q.setTitle(title);
        q.setContent(content);
        q.setContentHtml(contentHtml);
        q.setCreatedAt(LocalDateTime.now());
        q.setUpdatedAt(LocalDateTime.now());
        return questionRepository.save(q);
    }

    public List<Answer> getAnswers(Long questionId) {
        return answerRepository.findByQuestionIdOrderByVoteScoreDesc(questionId);
    }

    @Transactional
    public Answer createAnswer(Long questionId, String userId, String content, String contentHtml) {
        Question q = questionRepository.findById(questionId)
                .orElseThrow(() -> QooCommunityException.notFound("Question not found"));
        Answer a = new Answer();
        a.setQuestionId(questionId);
        a.setUserId(userId);
        a.setContent(content);
        a.setContentHtml(contentHtml);
        a.setCreatedAt(LocalDateTime.now());
        a.setUpdatedAt(LocalDateTime.now());
        Answer saved = answerRepository.save(a);

        q.setAnswerCount((int) answerRepository.countByQuestionId(questionId));
        questionRepository.save(q);

        return saved;
    }

    @Transactional
    public void acceptAnswer(Long questionId, Long answerId, String userId) {
        Question q = questionRepository.findById(questionId)
                .orElseThrow(() -> QooCommunityException.notFound("Question not found"));
        if (!q.getUserId().equals(userId)) {
            throw QooCommunityException.forbidden("Only the question author can accept an answer");
        }
        Answer a = answerRepository.findById(answerId)
                .orElseThrow(() -> QooCommunityException.notFound("Answer not found"));
        a.setIsAccepted(true);
        answerRepository.save(a);
        q.setAcceptedAnswerId(answerId);
        q.setIsSolved(true);
        questionRepository.save(q);
    }

    @Transactional
    public void vote(String userId, String targetType, Long targetId, String voteType) {
        voteRepository.findByUserIdAndTargetTypeAndTargetId(userId, targetType, targetId)
                .ifPresent(v -> {
                    if (v.getVoteType().equals(voteType)) {
                        voteRepository.delete(v);
                    } else {
                        v.setVoteType(voteType);
                        voteRepository.save(v);
                    }
                    return;
                });

        Vote v = new Vote();
        v.setUserId(userId);
        v.setTargetType(targetType);
        v.setTargetId(targetId);
        v.setVoteType(voteType);
        voteRepository.save(v);

        long upCount = voteRepository.countByTargetTypeAndTargetIdAndVoteType(targetType, targetId, "UP");
        long downCount = voteRepository.countByTargetTypeAndTargetIdAndVoteType(targetType, targetId, "DOWN");
        int score = (int) (upCount - downCount);

        if ("QUESTION".equals(targetType)) {
            questionRepository.findById(targetId).ifPresent(q -> {
                q.setVoteScore(score);
                questionRepository.save(q);
            });
        } else if ("ANSWER".equals(targetType)) {
            answerRepository.findById(targetId).ifPresent(a -> {
                a.setVoteScore(score);
                answerRepository.save(a);
            });
        }
    }
}
