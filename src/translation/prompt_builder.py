class PromptBuilder:
    """
    Constructs prompts for LLM translation and context summarization.
    """

    def build_translation_prompt(self, sentence: str, context: str, target_lang: str = "Traditional Chinese") -> str:
        """
        Builds the prompt for translating a sentence given the scenario context.
        """
        return f"""You are a real-time translation assistant.
Translate the following sentence into {target_lang} accurately.

Key Instruction:
- Identify pronouns (I, you, he, she, they) and resolve their references based on the context.
- Explicitly state the subject if the pronoun reference is clear from the context, instead of using generic pronouns like "他" or "它".
- Preserve the original tone and meaning.

Scenario Context:
{context}

Sentence to Translate:
"{sentence}"

Output only the translation, without explanation."""

    def build_summary_prompt(self, original_context: str, new_sentence: str, use_original_text: bool = False) -> str:
        """
        Builds the prompt for updating the scenario context.
        """
        label = "New Sentence" if use_original_text else "New Translated Sentence"
        
        return f"""You are a summarization assistant.
Update the scenario context to reflect the latest sentence.

Previous Context:
{original_context}

{label}:
{new_sentence}

Return a concise updated context summary (max 500 tokens)."""
