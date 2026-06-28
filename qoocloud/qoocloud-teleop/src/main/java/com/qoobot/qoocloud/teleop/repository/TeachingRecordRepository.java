package com.qoobot.qoocloud.teleop.repository;

import com.qoobot.qoocloud.teleop.entity.TeachingRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TeachingRecordRepository extends JpaRepository<TeachingRecord, String> {

    /** 按机器人查询示教记录 */
    List<TeachingRecord> findByRobotIdOrderByCreatedAtDesc(String robotId);

    /** 按操作员查询示教记录 */
    List<TeachingRecord> findByOperatorIdOrderByCreatedAtDesc(String operatorId);

    /** 按会话查询示教记录 */
    List<TeachingRecord> findBySessionId(String sessionId);

    /** 按名称模糊搜索 */
    @Query("SELECT r FROM TeachingRecord r WHERE r.name LIKE %:keyword% " +
           "ORDER BY r.createdAt DESC")
    List<TeachingRecord> searchByName(@Param("keyword") String keyword);

    /** 按标签查询 */
    @Query(value = "SELECT * FROM teaching_records WHERE tags @> :tag::jsonb " +
           "ORDER BY created_at DESC", nativeQuery = true)
    List<TeachingRecord> findByTag(@Param("tag") String tag);

    /** 统计操作员示教数 */
    long countByOperatorId(String operatorId);

    /** 统计机器人示教数 */
    long countByRobotId(String robotId);
}
