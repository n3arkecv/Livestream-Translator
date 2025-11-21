import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                               QCheckBox, QPushButton, QHBoxLayout, QMessageBox, 
                               QFormLayout, QGroupBox)
from PySide6.QtCore import Qt

class SettingsWindow(QDialog):
    def __init__(self, config_path="User_config.txt", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(500, 400)
        self.config_path = config_path
        self.config_data = {}
        
        # Layout
        layout = QVBoxLayout(self)
        
        # Form
        form_group = QGroupBox("Configuration")
        self.form_layout = QFormLayout()
        
        # Fields
        self.txt_openai_key = QLineEdit()
        self.txt_openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.form_layout.addRow("OpenAI API Key:", self.txt_openai_key)
        
        self.txt_google_key = QLineEdit()
        self.txt_google_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.form_layout.addRow("Google API Key:", self.txt_google_key)
        
        self.txt_llm_trans_model = QLineEdit()
        self.txt_llm_trans_model.setPlaceholderText("gpt-4o-mini")
        self.form_layout.addRow("Translation Model:", self.txt_llm_trans_model)
        
        self.txt_llm_summary_model = QLineEdit()
        self.txt_llm_summary_model.setPlaceholderText("gpt-4o-mini")
        self.form_layout.addRow("Summary Model:", self.txt_llm_summary_model)
        
        self.chk_use_original = QCheckBox("Use Original Text for Context")
        self.form_layout.addRow("", self.chk_use_original)
        
        form_group.setLayout(self.form_layout)
        layout.addWidget(form_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.save_config)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        # Load initial data
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    self.config_data[key.strip()] = value.strip()
            
            # Populate fields
            self.txt_openai_key.setText(self.config_data.get("OPENAI_API_KEY", ""))
            self.txt_google_key.setText(self.config_data.get("GOOGLE_API_KEY", ""))
            self.txt_llm_trans_model.setText(self.config_data.get("LLM_TRANSLATION_MODEL", ""))
            self.txt_llm_summary_model.setText(self.config_data.get("LLM_SUMMARY_MODEL", ""))
            
            use_orig = self.config_data.get("USE_ORIGINAL_TEXT_FOR_CONTEXT", "True")
            self.chk_use_original.setChecked(use_orig.lower() == "true")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load config: {e}")

    def save_config(self):
        # Update data from fields
        self.config_data["OPENAI_API_KEY"] = self.txt_openai_key.text()
        self.config_data["GOOGLE_API_KEY"] = self.txt_google_key.text()
        
        trans_model = self.txt_llm_trans_model.text()
        if trans_model:
            self.config_data["LLM_TRANSLATION_MODEL"] = trans_model
        elif "LLM_TRANSLATION_MODEL" in self.config_data:
            del self.config_data["LLM_TRANSLATION_MODEL"]
            
        sum_model = self.txt_llm_summary_model.text()
        if sum_model:
            self.config_data["LLM_SUMMARY_MODEL"] = sum_model
        elif "LLM_SUMMARY_MODEL" in self.config_data:
            del self.config_data["LLM_SUMMARY_MODEL"]
            
        self.config_data["USE_ORIGINAL_TEXT_FOR_CONTEXT"] = str(self.chk_use_original.isChecked())

        try:
            # Read original file to preserve comments if possible, or just overwrite?
            # Simple overwrite with keys is safer for now, but we lose comments.
            # Better: Read all lines, update known keys, append new keys.
            
            new_lines = []
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            else:
                lines = []
                
            processed_keys = set()
            
            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    new_lines.append(line)
                    continue
                
                if '=' in stripped:
                    key, _ = stripped.split('=', 1)
                    key = key.strip()
                    if key in self.config_data:
                        new_lines.append(f"{key}={self.config_data[key]}\n")
                        processed_keys.add(key)
                    else:
                        new_lines.append(line) # Keep unknown keys
                else:
                    new_lines.append(line)
            
            # Append missing keys
            for key, value in self.config_data.items():
                if key not in processed_keys:
                    new_lines.append(f"{key}={value}\n")
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
                
            QMessageBox.information(self, "Success", "Settings saved. \nSome changes may require a restart.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config: {e}")
