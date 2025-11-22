
class LocalizationManager:
    _instance = None
    
    TRANSLATIONS = {
        "en": {
            "window_title": "Livestream Translator Control",
            "grp_control": "Control",
            "grp_stt_settings": "STT Model Settings",
            "lbl_model": "Model:",
            "lbl_device": "Device:",
            "lbl_compute_type": "Compute Type:",
            "lbl_audio_input": "Audio Input:",
            "btn_refresh_tooltip": "Refresh Audio Devices",
            "lbl_stt_lang": "STT Language:",
            "lbl_target_lang": "Target Language:",
            "btn_start": "Start",
            "btn_stop": "Stop",
            "btn_settings_tooltip": "Settings",
            "btn_reset_context": "Reset Context",
            "btn_reset_context_tooltip": "Reset the translation context memory. \nWarning: This will make the translator forget previous conversation history.",
            "btn_hide_context": "Hide/Show Context",
            "grp_overlay": "Overlay",
            "btn_toggle_overlay": "Show/Hide Overlay",
            "lbl_font_size": "Font Size:",
            "lbl_history_lines": "History Lines:",
            "grp_logs": "System Log",
            "settings_title": "Settings",
            "grp_config": "Configuration",
            "lbl_openai_key": "OpenAI API Key:",
            "lbl_google_key": "Google API Key:",
            "lbl_trans_model": "Translation Model:",
            "lbl_summary_model": "Summary Model:",
            "chk_use_original": "Use Original Text for Context",
            "lbl_overlay_opacity": "Overlay Opacity:",
            "btn_save": "Save",
            "btn_cancel": "Cancel",
            "overlay_ongoing": "Standby for startup...",
            "overlay_translation": "Translation Standby...",
            "overlay_context": "Context Standby...",
            "lbl_gui_language": "GUI Language:"
        },
        "ja": {
            "window_title": "ライブ配信翻訳コントロール",
            "grp_control": "コントロール",
            "grp_stt_settings": "STTモデル設定",
            "lbl_model": "モデル:",
            "lbl_device": "デバイス:",
            "lbl_compute_type": "計算タイプ:",
            "lbl_audio_input": "音声入力:",
            "btn_refresh_tooltip": "音声デバイスを更新",
            "lbl_stt_lang": "音声認識言語:",
            "lbl_target_lang": "翻訳先言語:",
            "btn_start": "開始",
            "btn_stop": "停止",
            "btn_settings_tooltip": "設定",
            "btn_reset_context": "コンテキストをリセット",
            "btn_reset_context_tooltip": "翻訳コンテキストメモリをリセットします。\n警告: これにより、翻訳者は以前の会話履歴を忘れます。",
            "btn_hide_context": "コンテキストの表示/非表示",
            "grp_overlay": "オーバーレイ",
            "btn_toggle_overlay": "オーバーレイの表示/非表示",
            "lbl_font_size": "フォントサイズ:",
            "lbl_history_lines": "履歴行数:",
            "grp_logs": "システムログ",
            "settings_title": "設定",
            "grp_config": "構成",
            "lbl_openai_key": "OpenAI APIキー:",
            "lbl_google_key": "Google APIキー:",
            "lbl_trans_model": "翻訳モデル:",
            "lbl_summary_model": "要約モデル:",
            "chk_use_original": "コンテキストに原文を使用する",
            "lbl_overlay_opacity": "オーバーレイ不透明度:",
            "btn_save": "保存",
            "btn_cancel": "キャンセル",
            "overlay_ongoing": "起動待機中...",
            "overlay_translation": "翻訳待機中...",
            "overlay_context": "コンテキスト待機中...",
            "lbl_gui_language": "GUI言語:"
        },
        "zh-TW": {
            "window_title": "直播翻譯控制台",
            "grp_control": "控制",
            "grp_stt_settings": "STT 模型設定",
            "lbl_model": "模型:",
            "lbl_device": "裝置:",
            "lbl_compute_type": "計算類型:",
            "lbl_audio_input": "音訊輸入:",
            "btn_refresh_tooltip": "重新整理音訊裝置",
            "lbl_stt_lang": "語音辨識語言:",
            "lbl_target_lang": "目標翻譯語言:",
            "btn_start": "開始",
            "btn_stop": "停止",
            "btn_settings_tooltip": "設定",
            "btn_reset_context": "重置情境",
            "btn_reset_context_tooltip": "重置翻譯情境記憶。\n警告:這將使翻譯器忘記之前的對話歷史。",
            "btn_hide_context": "隱藏/顯示情境",
            "grp_overlay": "字幕覆蓋層",
            "btn_toggle_overlay": "顯示/隱藏 覆蓋層",
            "lbl_font_size": "字體大小:",
            "lbl_history_lines": "歷史行數:",
            "grp_logs": "系統日誌",
            "settings_title": "設定",
            "grp_config": "組態設定",
            "lbl_openai_key": "OpenAI API Key:",
            "lbl_google_key": "Google API Key:",
            "lbl_trans_model": "翻譯模型:",
            "lbl_summary_model": "摘要模型:",
            "chk_use_original": "使用原文進行情境更新",
            "lbl_overlay_opacity": "覆蓋層不透明度:",
            "btn_save": "儲存",
            "btn_cancel": "取消",
            "overlay_ongoing": "等待啟動...",
            "overlay_translation": "翻譯待命...",
            "overlay_context": "情境待命...",
            "lbl_gui_language": "介面語言:"
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalizationManager, cls).__new__(cls)
            cls._instance.current_lang = "en"
        return cls._instance

    def set_language(self, lang_code):
        if lang_code in self.TRANSLATIONS:
            self.current_lang = lang_code

    def get(self, key):
        return self.TRANSLATIONS.get(self.current_lang, {}).get(key, key)

# Global instance
i18n = LocalizationManager()

