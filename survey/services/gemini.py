from google import genai
from django.conf import settings

client = genai.Client(
    api_key = settings.GOOGLE_API_KEY
)

def summerize_answers(question=str ,answer_list=list[str], model="gemini-3.1-flash-lite"):
    answers = ", ".join(
        f"{i}. {item}" for i,item in enumerate(answer_list, start=1))

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
        - Keep the entire response under 100 words.
        - Write in one short paragraph. Short enough to be readable under 15 seconds
        - Do not use headings, bullet points, numbering, or markdown.

        Survey Question:
        {question}

        Survey Responses:
        {answers}
        """
    
    response = client.models.generate_content(
        model = model,
        contents = prompt)

    return response.text