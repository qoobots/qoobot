// ============================================================================
// voice_translation.cpp — Multi-language translation & offline voice commands
// Part of qoosvc::voice::VoiceService (PIMPL extension)
// ============================================================================

#include "qoosvc/voice/voice_service.h"
#include <algorithm>
#include <map>
#include <regex>
#include <set>
#include <sstream>

namespace qoosvc::voice {

// ============================================================================
// Translation dictionary (simplified phrase-based for framework skeleton)
// In production: ONNX NMT model via qoocore inference engine
// ============================================================================

namespace {

struct PhraseEntry {
    std::string zh;
    std::string en;
    std::string ja;
};

// Common robot interaction phrases
const std::vector<PhraseEntry> kPhraseDict = {
    {"你好", "Hello", "こんにちは"},
    {"再见", "Goodbye", "さようなら"},
    {"谢谢", "Thank you", "ありがとう"},
    {"对不起", "Sorry", "ごめんなさい"},
    {"请过来", "Come here", "こっちに来て"},
    {"停止", "Stop", "止まれ"},
    {"跟我来", "Follow me", "ついて来て"},
    {"去充电", "Go charge", "充電に行く"},
    {"我在这里", "I am here", "ここにいる"},
    {"警告", "Warning", "警告"},
    {"好的", "OK", "はい"},
    {"不行", "Cannot do that", "できません"},
    {"让开", "Move aside", "どいて"},
    {"安静", "Be quiet", "静かに"},
    {"快一点", "Faster", "もっと速く"},
    {"慢一点", "Slower", "もっとゆっくり"},
    {"左转", "Turn left", "左に曲がる"},
    {"右转", "Turn right", "右に曲がる"},
    {"前进", "Go forward", "前進"},
    {"后退", "Go backward", "後退"},
};

std::string lookup_phrase(const std::string& text, const std::string& src, const std::string& tgt) {
    for (const auto& entry : kPhraseDict) {
        std::string source_text;
        if (src == "zh-CN") source_text = entry.zh;
        else if (src == "en-US") source_text = entry.en;
        else if (src == "ja-JP") source_text = entry.ja;
        else continue;

        if (source_text == text) {
            if (tgt == "zh-CN") return entry.zh;
            if (tgt == "en-US") return entry.en;
            if (tgt == "ja-JP") return entry.ja;
        }
    }

    // Fallback: word-by-word lookup
    std::istringstream iss(text);
    std::string word;
    std::vector<std::string> translated_words;
    while (iss >> word) {
        std::string translated = word;
        for (const auto& entry : kPhraseDict) {
            std::string candidate;
            if (src == "zh-CN") candidate = entry.zh;
            else if (src == "en-US") candidate = entry.en;
            else if (src == "ja-JP") candidate = entry.ja;
            else continue;

            if (candidate == word) {
                if (tgt == "zh-CN") translated = entry.zh;
                else if (tgt == "en-US") translated = entry.en;
                else if (tgt == "ja-JP") translated = entry.ja;
                break;
            }
        }
        translated_words.push_back(translated);
    }

    std::string result;
    for (size_t i = 0; i < translated_words.size(); ++i) {
        if (i > 0) result += (tgt == "ja-JP" ? "" : " ");
        result += translated_words[i];
    }
    return result;
}

} // anonymous namespace

// ============================================================================
// Real-time Translation
// ============================================================================

Result<TranslationResult> VoiceService::translate_text(
    const std::string& text,
    const std::string& source_language,
    const std::string& target_language) {

    if (text.empty()) {
        return Result<TranslationResult>::err(ErrorCode::INVALID_ARGUMENT, "Empty text");
    }

    // Validate languages
    const auto& supported = config_.supported_languages;
    if (std::find(supported.begin(), supported.end(), source_language) == supported.end()) {
        return Result<TranslationResult>::err(ErrorCode::INVALID_ARGUMENT,
            "Unsupported source language: " + source_language);
    }
    if (std::find(supported.begin(), supported.end(), target_language) == supported.end()) {
        return Result<TranslationResult>::err(ErrorCode::INVALID_ARGUMENT,
            "Unsupported target language: " + target_language);
    }

    if (source_language == target_language) {
        // No translation needed
        TranslationResult result;
        result.source_text = text;
        result.translated_text = text;
        result.source_language = source_language;
        result.target_language = target_language;
        result.confidence = 1.0f;
        result.is_streaming = false;
        result.timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        return result;
    }

    // In production: use ONNX neural machine translation model via qoocore
    // For now: phrase-based dictionary lookup + basic word mapping
    TranslationResult result;
    result.source_text = text;
    result.translated_text = lookup_phrase(text, source_language, target_language);
    result.source_language = source_language;
    result.target_language = target_language;
    result.confidence = 0.75f;  // Phrase-based confidence
    result.is_streaming = false;
    result.timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    return result;
}

Result<void> VoiceService::translate_stream(
    const AudioBuffer& audio,
    const std::string& source_language,
    const std::string& target_language,
    std::function<void(const TranslationResult&)> callback) {

    if (!callback) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "Callback required for streaming");
    }

    // Pipeline: ASR → Translation → callback with partial results
    // First, run ASR on the audio buffer
    auto asr_future = recognize(audio);
    auto asr_result = asr_future.get();

    if (!asr_result.is_final) {
        // Send partial result as streaming translation
        auto trans = translate_text(asr_result.text, source_language, target_language);
        if (trans.is_ok()) {
            auto& result = *trans;
            result.is_streaming = true;
            callback(result);
        }
    } else {
        // Send final result
        auto trans = translate_text(asr_result.text, source_language, target_language);
        if (trans.is_ok()) {
            auto& result = *trans;
            result.is_streaming = false;
            callback(result);
        }
    }

    return Result<void>::ok();
}

Result<void> VoiceService::translate_speech(
    const AudioBuffer& audio,
    const std::string& source_language,
    const std::string& target_language) {

    // Full pipeline: ASR → Translation → TTS
    auto asr_future = recognize(audio);
    auto asr_result = asr_future.get();

    if (!asr_result.is_final) {
        return Result<void>::err(ErrorCode::VOICE_ASR_FAILED, "ASR did not produce final result");
    }

    auto trans_result = translate_text(asr_result.text, source_language, target_language);
    if (trans_result.is_err()) {
        return Result<void>::err(trans_result.error_code(), trans_result.error_message());
    }

    // Speak the translated text
    return speak(trans_result->translated_text);
}

Result<void> VoiceService::set_translation_languages(const std::vector<std::string>& languages) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    config_.supported_languages = languages;
    return Result<void>::ok();
}

// ============================================================================
// Offline Voice Commands
// ============================================================================

Result<void> VoiceService::set_offline_mode(bool enabled) {
    offline_mode_ = enabled;
    config_.offline_mode = enabled;
    return Result<void>::ok();
}

Result<void> VoiceService::register_offline_command(const OfflineCommand& command) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (command.command_id.empty()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "Command ID cannot be empty");
    }
    if (command.phrases.empty()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "At least one trigger phrase required");
    }

    // Check for duplicate command ID
    auto it = std::find_if(impl_->offline_commands.begin(), impl_->offline_commands.end(),
        [&](const auto& cmd) { return cmd.command_id == command.command_id; });

    if (it != impl_->offline_commands.end()) {
        *it = command;  // Update existing
    } else {
        impl_->offline_commands.push_back(command);
    }

    return Result<void>::ok();
}

Result<void> VoiceService::unregister_offline_command(const std::string& command_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->offline_commands.begin(), impl_->offline_commands.end(),
        [&](const auto& cmd) { return cmd.command_id == command_id; });

    if (it == impl_->offline_commands.end()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
            "Offline command not found: " + command_id);
    }

    impl_->offline_commands.erase(it);
    return Result<void>::ok();
}

std::vector<OfflineCommand> VoiceService::get_offline_commands() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->offline_commands;
}

Result<NLUResult> VoiceService::process_offline(const AudioBuffer& audio) {
    if (!offline_mode_) {
        return Result<NLUResult>::err(ErrorCode::INVALID_ARGUMENT, "Not in offline mode");
    }

    // Offline ASR pipeline: use local ASR model without network
    // In production: ONNX streaming ASR model via qoocore
    auto asr_future = recognize(audio);
    auto asr_result = asr_future.get();

    if (!asr_result.is_final || asr_result.text.empty()) {
        return Result<NLUResult>::err(ErrorCode::VOICE_ASR_FAILED,
            "Offline ASR failed to produce text");
    }

    std::string recognized = asr_result.text;
    std::transform(recognized.begin(), recognized.end(), recognized.begin(), ::tolower);

    // Match against registered offline commands
    std::lock_guard<std::mutex> lock(impl_->mutex);

    float best_confidence = 0.0f;
    OfflineCommand best_match;

    for (const auto& cmd : impl_->offline_commands) {
        for (const auto& phrase : cmd.phrases) {
            std::string lower_phrase = phrase;
            std::transform(lower_phrase.begin(), lower_phrase.end(),
                           lower_phrase.begin(), ::tolower);

            // Substring matching (simplified; production uses embedding similarity)
            if (recognized.find(lower_phrase) != std::string::npos) {
                float score = static_cast<float>(lower_phrase.length()) / recognized.length();
                if (score > best_confidence) {
                    best_confidence = score;
                    best_match = cmd;
                }
            }
        }
    }

    if (best_confidence >= 0.3f) {  // Minimum match threshold
        NLUResult result;
        result.intent = best_match.intent;
        result.slots = best_match.slots;
        result.raw_text = asr_result.text;
        result.confidence = best_confidence;
        return result;
    }

    // Fall back to regular NLU
    return understand(asr_result.text);
}

} // namespace qoosvc::voice
