#pragma once

#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace qoosvc::voice {

/**
 * Audio buffer for streaming audio data.
 */
struct AudioBuffer {
    std::vector<int16_t> samples;   // 16-bit PCM samples
    uint32_t sample_rate = 16000;   // Hz
    uint8_t channels = 1;           // Mono
    uint64_t timestamp_us = 0;      // Microsecond timestamp
};

/**
 * ASR (Automatic Speech Recognition) result.
 */
struct ASRResult {
    std::string text;               // Recognized text
    std::string language;           // BCP 47 language tag (e.g., "zh-CN", "en-US")
    float confidence = 0.0f;        // 0.0 - 1.0
    bool is_final = false;          // True if this is the final result
    bool is_partial = false;        // True if streaming intermediate result
};

/**
 * NLU (Natural Language Understanding) result.
 */
struct NLUResult {
    std::string intent;             // Intent name (e.g., "navigation.go_to")
    std::map<std::string, std::string> slots;  // Slot values
    std::string raw_text;           // Original input text
    float confidence = 0.0f;        // Intent classification confidence
};

/**
 * TTS (Text-to-Speech) configuration.
 */
struct TTSConfig {
    std::string voice_id = "default";  // Voice profile ID
    float speed = 1.0f;                // Playback speed (0.5 - 2.0)
    float pitch = 1.0f;                // Pitch shift (0.5 - 2.0)
    float volume = 1.0f;               // Volume (0.0 - 1.0)
    std::string emotion;               // Emotion tag (e.g., "happy", "neutral", "serious")
};

/**
 * Wake word detection result.
 */
struct WakeWordResult {
    std::string word;               // Detected wake word
    float confidence = 0.0f;        // Detection confidence
    double azimuth_deg = 0.0;       // Sound source direction (degrees)
    double elevation_deg = 0.0;     // Sound source elevation (degrees)
    uint64_t timestamp_us = 0;
};

/**
 * Speaker identification result.
 */
struct SpeakerInfo {
    std::string speaker_id;         // Unique speaker identifier
    std::string display_name;       // Human-readable name
    float confidence = 0.0f;        // Identification confidence
    bool is_enrolled = false;       // Whether speaker is in the database
};

/**
 * Language translation result.
 */
struct TranslationResult {
    std::string source_text;            // Original text
    std::string translated_text;        // Translated text
    std::string source_language;        // Source BCP 47 language tag
    std::string target_language;        // Target BCP 47 language tag
    float confidence = 0.0f;
    bool is_streaming = false;          // True if partial streaming result
    uint64_t timestamp_us = 0;
};

/**
 * Offline voice command definition.
 */
struct OfflineCommand {
    std::string command_id;             // Unique command identifier
    std::vector<std::string> phrases;   // Trigger phrases (e.g., ["stop", "停止", "止まれ"])
    std::string intent;                 // Mapped intent
    std::map<std::string, std::string> slots;  // Default slot values
    float threshold = 0.75f;            // Detection confidence threshold
};

/**
 * Voice service configuration.
 */
struct VoiceConfig {
    // Wake word
    std::string wake_word = "Hey QooBot";
    std::string wake_word_language = "en-US";
    float wake_word_threshold = 0.7f;

    // ASR
    std::string asr_model_path;
    std::string asr_language = "zh-CN";
    bool streaming_asr = true;

    // NLU
    std::string nlu_model_path;
    float nlu_threshold = 0.6f;

    // TTS
    std::string tts_model_path;
    TTSConfig default_tts_config;

    // Translation
    std::string translation_model_path;
    std::vector<std::string> supported_languages = {"zh-CN", "en-US", "ja-JP"};

    // Offline voice
    bool offline_mode = false;
    std::string offline_asr_model_path;
    std::string offline_commands_path;  // Path to offline command set JSON
};

} // namespace qoosvc::voice
