package com.qoobot.qoogear.common.storage;

import io.minio.*;
import io.minio.http.Method;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/**
 * Unified file storage service backed by MinIO.
 * Supports upload, download, presigned URLs, and deletion.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class FileStorageService {

    private final MinioClient minioClient;

    /**
     * Upload a file to the specified bucket.
     * Returns the object key (UUID-based to avoid collisions).
     */
    public String upload(String bucket, MultipartFile file) {
        try {
            ensureBucketExists(bucket);
            String objectKey = UUID.randomUUID() + "_" + sanitize(file.getOriginalFilename());
            minioClient.putObject(
                    PutObjectArgs.builder()
                            .bucket(bucket)
                            .object(objectKey)
                            .stream(file.getInputStream(), file.getSize(), -1)
                            .contentType(file.getContentType())
                            .build());
            log.info("Uploaded file: bucket={}, key={}, size={}", bucket, objectKey, file.getSize());
            return objectKey;
        } catch (Exception e) {
            log.error("Failed to upload file to bucket={}: {}", bucket, e.getMessage(), e);
            throw new RuntimeException("File upload failed", e);
        }
    }

    /**
     * Download a file as InputStream.
     */
    public InputStream download(String bucket, String objectKey) {
        try {
            return minioClient.getObject(
                    GetObjectArgs.builder()
                            .bucket(bucket)
                            .object(objectKey)
                            .build());
        } catch (Exception e) {
            log.error("Failed to download file: bucket={}, key={}", bucket, objectKey, e);
            throw new RuntimeException("File download failed", e);
        }
    }

    /**
     * Generate a presigned URL for temporary access (valid for 1 hour).
     */
    public String getPresignedUrl(String bucket, String objectKey) {
        try {
            return minioClient.getPresignedObjectUrl(
                    GetPresignedObjectUrlArgs.builder()
                            .method(Method.GET)
                            .bucket(bucket)
                            .object(objectKey)
                            .expiry(1, TimeUnit.HOURS)
                            .build());
        } catch (Exception e) {
            log.error("Failed to generate presigned URL: bucket={}, key={}", bucket, objectKey, e);
            throw new RuntimeException("Presigned URL generation failed", e);
        }
    }

    /**
     * Delete a file.
     */
    public void delete(String bucket, String objectKey) {
        try {
            minioClient.removeObject(
                    RemoveObjectArgs.builder()
                            .bucket(bucket)
                            .object(objectKey)
                            .build());
            log.info("Deleted file: bucket={}, key={}", bucket, objectKey);
        } catch (Exception e) {
            log.error("Failed to delete file: bucket={}, key={}", bucket, objectKey, e);
            throw new RuntimeException("File deletion failed", e);
        }
    }

    private void ensureBucketExists(String bucket) throws Exception {
        boolean found = minioClient.bucketExists(BucketExistsArgs.builder().bucket(bucket).build());
        if (!found) {
            minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
            log.info("Created bucket: {}", bucket);
        }
    }

    private String sanitize(String filename) {
        if (filename == null) return "unnamed";
        return filename.replaceAll("[^a-zA-Z0-9._-]", "_");
    }
}
