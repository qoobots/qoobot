package com.qoobot.qoocloud.teleop.repository;

import com.qoobot.qoocloud.teleop.entity.TeleopSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface TeleopSessionRepository extends JpaRepository<TeleopSession, String> {

    /** 查找机器人当前活跃会话 */
    @Query("SELECT s FROM TeleopSession s WHERE s.robotId = :robotId " +
           "AND s.sessionStatus NOT IN ('CLOSED', 'REJECTED', 'TIMEOUT')")
    Optional<TeleopSession> findActiveByRobotId(@Param("robotId") String robotId);

    /** 查找操作员当前活跃会话 */
    @Query("SELECT s FROM TeleopSession s WHERE s.operatorId = :operatorId " +
           "AND s.sessionStatus NOT IN ('CLOSED', 'REJECTED', 'TIMEOUT')")
    Optional<TeleopSession> findActiveByOperatorId(@Param("operatorId") String operatorId);

    /** 按机器人查询历史会话 */
    List<TeleopSession> findByRobotIdOrderByCreatedAtDesc(String robotId);

    /** 按操作员查询历史会话 */
    List<TeleopSession> findByOperatorIdOrderByCreatedAtDesc(String operatorId);

    /** 按状态查询 */
    List<TeleopSession> findBySessionStatus(TeleopSession.SessionStatus status);

    /** 查找超时会话（心跳超时但未关闭） */
    @Query("SELECT s FROM TeleopSession s WHERE s.sessionStatus = 'ACTIVE' " +
           "AND s.lastHeartbeat < :timeout")
    List<TeleopSession> findTimedOutSessions(@Param("timeout") Instant timeout);

    /** 按时间范围查询 */
    @Query("SELECT s FROM TeleopSession s WHERE s.createdAt >= :since " +
           "ORDER BY s.createdAt DESC")
    List<TeleopSession> findSince(@Param("since") Instant since);

    /** 统计操作员会话数 */
    long countByOperatorId(String operatorId);

    /** 统计机器人会话数 */
    long countByRobotId(String robotId);
}
