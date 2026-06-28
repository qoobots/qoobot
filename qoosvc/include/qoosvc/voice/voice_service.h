#pragma once

#include "voice_types.h"
#include "../common/result.h"
#include "../common/service_base.h"
#include <functional>
#include <future>
#include <memory>
#include <string>
#include <vector>

namespace qoosvc::voice {

/**
 * VoiceService — Robot voice interaction service.
 *
 * Provides wake word detection, ASR, NLU, TTS, speaker identification,
 * and sound source localization.
 *
 * This is the primary interface for QooBot's voice capabilities,
 * analogous to Siri/Alexa for robots.
 */
class VoiceService : public ServiceBase {
public:
    VoiceService();
    ~VoiceService() override;

    // --- Configuration ---

    Result<void> configure(const VoiceConfig& config);
    const VoiceConfig& config() const { return config_; }

    // --- Wake Word ---

    /**
     * Set the wake word. Supports custom wake words.
     * Example: "Hey QooBot", "你好小Q"
     */
    Result<void> set_wake_word(const std::string& word, const std::string& language);

    /**
     * Enable or disable wake word detection.
     */
    Result<void> enable_wake_word(bool enable);

    /**
     * Register a callback for wake word detection events.
     */
    void on_wake_word_detected(std::function<void(const WakeWordResult&)> callback);

    // --- ASR (Automatic Speech Recognition) ---

    /**
     * Perform streaming ASR on an audio buffer.
     * Returns partial results as they become available via callback.
     */
    Result<void> recognize_stream(const AudioBuffer& audio,
                                   std::function<void(const ASRResult&)> callback);

    /**
     * Perform non-streaming ASR on a complete audio buffer.
     */
    std::future<ASRResult> recognize(const AudioBuffer& audio);

    // --- NLU (Natural Language Understanding) ---

    /**
     * Understand the intent and slots from recognized text.
     */
    Result<NLUResult> understand(const std::string& text);

    /**
     * Understand with context from previous conversation turns.
     */
    Result<NLUResult> understand_with_context(
        const std::string& text,
        const std::vector<std::pair<std::string, NLUResult>>& conversation_history);

    // --- TTS (Text-to-Speech) ---

    /**
     * Synthesize speech from text.
     * Returns audio buffer containing the synthesized speech.
     */
    Result<AudioBuffer> synthesize(const std::string& text, const TTSConfig& config = {});

    /**
     * Synthesize and immediately play through the robot's speaker.
     */
    Result<void> speak(const std::string& text, const TTSConfig& config = {});

    // --- Speaker Identification ---

    /**
     * Identify the speaker from an audio sample.
     */
    Result<SpeakerInfo> identify_speaker(const AudioBuffer& audio);

    /**
     * Enroll a new speaker with voice samples.
     */
    Result<std::string> enroll_speaker(const std::string& name,
                                        const std::vector<AudioBuffer>& samples);

    /**
     * Remove an enrolled speaker.
     */
    Result<void> remove_speaker(const std::string& speaker_id);

    // --- Sound Source Localization ---

    /**
     * Estimate the direction of arrival for a sound source.
     * Uses microphone array beamforming.
     */
    struct DirectionOfArrival {
        double azimuth_deg;         // Horizontal angle (0 = front)
        double elevation_deg;       // Vertical angle (0 = horizontal)
        float confidence;
    };

    Result<DirectionOfArrival> estimate_direction(const AudioBuffer& audio);

    // --- Real-time Translation ---

    /**
     * Translate text in real-time. Supports streaming for live caption display.
     */
    Result<TranslationResult> translate_text(const std::string& text,
                                               const std::string& source_language,
                                               const std::string& target_language);

    /**
     * Streaming translation with partial result callbacks (for live captions).
     */
    Result<void> translate_stream(const AudioBuffer& audio,
                                    const std::string& source_language,
                                    const std::string& target_language,
                                    std::function<void(const TranslationResult&)> callback);

    /**
     * Translate speech directly: ASR + translation + TTS pipeline.
     */
    Result<void> translate_speech(const AudioBuffer& audio,
                                    const std::string& source_language,
                                    const std::string& target_language);

    /**
     * Set supported languages for translation.
     */
    Result<void> set_translation_languages(const std::vector<std::string>& languages);

    // --- Offline Voice ---

    /**
     * Enable/disable offline voice mode.
     * When enabled, uses local models without network dependency.
     */
    Result<void> set_offline_mode(bool enabled);

    /**
     * Register an offline voice command with trigger phrases.
     */
    Result<void> register_offline_command(const OfflineCommand& command);

    /**
     * Unregister an offline voice command.
     */
    Result<void> unregister_offline_command(const std::string& command_id);

    /**
     * Get all registered offline commands.
     */
    std::vector<OfflineCommand> get_offline_commands() const;

    /**
     * Process audio with offline-only pipeline (no network).
     * Returns the matched offline command intent, if any.
     */
    Result<NLUResult> process_offline(const AudioBuffer& audio);

    // --- Service Lifecycle ---

    bool is_wake_word_active() const { return wake_word_enabled_; }
    bool is_listening() const { return listening_; }
    bool is_offline_mode() const { return offline_mode_; }

protected:
    Result<void> on_initialize() override;
    Result<void> on_stop() override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;

    VoiceConfig config_;
    bool wake_word_enabled_ = true;
    bool listening_ = false;
    bool offline_mode_ = false;
};

} // namespace qoosvc::voice
