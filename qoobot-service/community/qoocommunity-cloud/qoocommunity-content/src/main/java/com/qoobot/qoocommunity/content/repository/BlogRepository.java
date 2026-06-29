package com.qoobot.qoocommunity.content.repository;

import com.qoobot.qoocommunity.content.domain.Blog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BlogRepository extends JpaRepository<Blog, Long> {
    Page<Blog> findByIsPublishedTrueOrderByPublishedAtDesc(Pageable pageable);
}
