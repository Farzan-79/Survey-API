from .gemini import generate_summary
from django.conf import settings

def build_answers_text(answers):
    return "\n".join(
        f"{i}. {item}" for i,item in enumerate(answers, start=1))

def build_prompt(question, answers):
    prompt = f"""
        You are an expert survey analyst.

        Analyze the responses to the survey question below and produce a very brief summary for the survey owner to get a general idea of the answers.

        Rules:
        - Base your summary only on the provided responses.
        - Focus only on the most common themes.
        - Do not mention every individual opinion.
        - Do not invent information.
        - If opinions are mixed, briefly mention that.
        - If there are recurring suggestions or complaints, include only the most important ones.
        - Keep the entire response under 80 words.
        - Write in one short paragraph. Short enough to be readable under 15 seconds
        - Do not use headings, bullet points, numbering, or markdown.

        Survey Question:
        {question}

        Survey Responses:
        {answers}
        """
    return prompt

def summarize_answers(question: str, answer_list: list[str], model: str = settings.GEMINI_MODEL) -> str:
    answers = build_answers_text(answer_list)

    prompt = build_prompt(question, answers)

    return generate_summary(prompt, model)