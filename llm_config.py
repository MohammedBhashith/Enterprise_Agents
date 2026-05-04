import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

load_dotenv()


def get_llm(temperature: float = 0.2):
    """
    Returns LLM based on MODEL_PROVIDER in .env.
    Supported providers: gemini, groq
    """

    provider = os.getenv("MODEL_PROVIDER", "groq").lower()

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing in .env")

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
        )

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

        if not api_key:
            raise ValueError("GROQ_API_KEY is missing in .env")

        return ChatGroq(
            model=model,
            api_key=api_key,
            temperature=temperature,
        )

    raise ValueError("MODEL_PROVIDER must be either 'gemini' or 'groq'")