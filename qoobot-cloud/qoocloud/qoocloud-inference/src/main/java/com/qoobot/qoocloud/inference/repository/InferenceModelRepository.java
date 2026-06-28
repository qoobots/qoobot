package com.qoobot.qoocloud.inference.repository;

import com.qoobot.qoocloud.inference.entity.InferenceModel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface InferenceModelRepository extends JpaRepository<InferenceModel, String> {

    List<InferenceModel> findByState(String state);

    Optional<InferenceModel> findByNameAndVersion(String name, String version);

    int countByState(String state);
}
