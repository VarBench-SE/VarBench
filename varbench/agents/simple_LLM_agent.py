import base64
from io import BytesIO
from typing import Iterable
from PIL import Image
from loguru import logger
from openai.types.chat import ChatCompletionMessageParam

from varbench.agents import Agent
from varbench.api.chat_api import ChatApi
from varbench.prompt_templates import IT_PROMPT, SYSTEM_PROMPT_GENERATION
from varbench.renderers.renderer import Renderer, RendererException
from varbench.utils.parsing import get_first_code_block


class SimpleLLMAgent(Agent):
    """Simple LLM agent that uses only the "reading" capabilities of the models tested"""

    def compute(
        self, instruction: str, code: str, image: Image.Image = None, **kwargs
    ) -> Iterable[str]:
        messages = self._create_message(instruction, code)

        return self.api.chat_request(messages)

    def batchCompute(
        self,
        instructions: Iterable[str],
        codes: Iterable[str],
        ids: Iterable[str],
        image_input: Iterable[Image.Image] = None,
        **kwargs,
    ) -> Iterable[Iterable[str]]:
        messages = [
            self._create_message(instruction, code)
            for instruction, code in zip(instructions, codes)
        ]

        return self.api.batch_chat_request(messages, ids)

    def _create_message(
        self, instruction: str, code: str
    ) -> Iterable[ChatCompletionMessageParam]:
        """Add a row that contains the prompt"""
        user_instruction = IT_PROMPT.format(instruction=instruction, content=code)

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT_GENERATION,
            },
            {"role": "user", "content": user_instruction},
        ]

        return messages