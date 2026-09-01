"""
Configuration and LLM Client Provider for Online Course Examination System Agent.
Prioritizes ultra-fast Groq Cloud (GPT-OSS-120B / Qwen) with seamless Google Gemini and Mock fallbacks.
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class LLMProvider:
    """Fast, reliable LLM Provider with Groq, Gemini, and Mock support."""

    def __init__(self):
        load_dotenv(dotenv_path=env_path, override=True)
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()

        self.groq_client = None
        self.gemini_client = None
        self.openai_client = None

        # Prioritize Groq if key is available (0.3s response time, high free limits)
        if self.groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_key, timeout=6.0)
                self.active_provider = "groq"
                self.active_model = "openai/gpt-oss-120b"
            except Exception as e:
                print(f"[Config] Error initializing Groq: {e}")

        if not self.groq_client and self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self.gemini_client = genai.GenerativeModel("gemini-flash-latest")
                self.active_provider = "gemini"
                self.active_model = "gemini-flash-latest"
            except Exception as e:
                print(f"[Config] Error initializing Gemini: {e}")

        if not self.groq_client and not self.gemini_client and self.openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_key, timeout=6.0)
                self.active_provider = "openai"
                self.active_model = "gpt-4o-mini"
            except Exception as e:
                print(f"[Config] Error initializing OpenAI: {e}")

        if not self.groq_client and not self.gemini_client and not self.openai_client:
            self.active_provider = "mock"
            self.active_model = "offline_engine"

    def get_provider_name(self) -> str:
        return self.active_provider

    def get_model_name(self) -> str:
        return self.active_model

    def generate_with_groq(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        if not self.groq_client:
            return None
        models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b", "groq/compound"]
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for m in models:
            try:
                resp = self.groq_client.chat.completions.create(
                    model=m,
                    messages=messages,
                    temperature=0.2,
                )
                self.active_provider = "groq"
                self.active_model = m
                return resp.choices[0].message.content
            except Exception:
                continue
        return None

    def generate_with_gemini(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        if not self.gemini_client:
            return None
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            resp = self.gemini_client.generate_content(
                full_prompt,
                request_options={"timeout": 4.0}
            )
            return resp.text
        except Exception:
            return None

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Generates text with fast Groq priority and immediate fallbacks.
        """
        # 1. Try Groq first (Fastest and most reliable)
        if self.groq_key:
            res = self.generate_with_groq(prompt, system_prompt)
            if res:
                return res

        # 2. Try Gemini
        if self.gemini_key:
            res = self.generate_with_gemini(prompt, system_prompt)
            if res:
                return res

        # 3. Try OpenAI
        if self.openai_key and self.openai_client:
            try:
                resp = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                return resp.choices[0].message.content
            except Exception:
                pass

        # 4. Fallback to Mock
        return ""


# Global instance
llm_client = LLMProvider()
