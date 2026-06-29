#include <gtest/gtest.h>
#include "qoosvc/voice/voice_service.h"

using namespace qoosvc::voice;

/**
 * Integration test: VoiceService full pipeline (wake word → ASR → NLU → TTS).
 */
TEST(VoicePipelineTest, ServiceInitialization) {
    VoiceService voice;
    auto result = voice.initialize();
    EXPECT_TRUE(result.is_ok());
}

TEST(VoicePipelineTest, WakeWordConfiguration) {
    VoiceService voice;
    voice.initialize();

    EXPECT_TRUE(voice.set_wake_word("Hey QooBot", "zh"));
    EXPECT_TRUE(voice.enable_wake_word(true));
    EXPECT_TRUE(voice.enable_wake_word(false));
}

TEST(VoicePipelineTest, ASRConfiguration) {
    VoiceService voice;
    voice.initialize();

    ASRConfig config;
    config.model_path = "models/test_asr.onnx";
    config.language = "zh";
    EXPECT_TRUE(voice.configure_asr(config));
}

TEST(VoicePipelineTest, TTSConfiguration) {
    VoiceService voice;
    voice.initialize();

    TTSConfig config;
    config.voice_id = "warm_female";
    config.speed = 1.0f;
    EXPECT_TRUE(voice.configure_tts(config));
}

TEST(VoicePipelineTest, LifecycleSequence) {
    VoiceService voice;
    voice.initialize();

    auto pause_result = voice.pause();
    EXPECT_TRUE(pause_result.is_ok());

    auto resume_result = voice.resume();
    EXPECT_TRUE(resume_result.is_ok());

    auto stop_result = voice.stop();
    EXPECT_TRUE(stop_result.is_ok());
}
