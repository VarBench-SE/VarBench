import base64
from io import BytesIO
from typing import Iterable
from PIL import Image
from loguru import logger
from openai.types.chat import ChatCompletionMessageParam

from varbench.agents import Agent
from varbench.api.chat_api import ChatApi
from varbench.prompt_templates import MULTIMODAL_INSTRUCTION
from varbench.renderers.renderer import Renderer, RendererException
from varbench.utils.parsing import get_first_code_block

class LMMAgent(Agent):
    """LMM(Large Multimodal Model) agent that uses both the "reading" and "vision" capabilities of the models tested"""

    def compute(
        self, instruction: str, code: str, image: Image.Image = None, **kwargs
    ) -> Iterable[str]:
        messages = self._create_message(instruction, code, image)

        return self.api.chat_request(messages)

    def batchCompute(
        self,
        instructions: Iterable[str],
        codes: Iterable[str],
        ids: Iterable[str],
        images_input: Iterable[Image.Image] = None,
        **kwargs,
    ) -> Iterable[Iterable[str]]:
        messages = [
            self._create_message(instruction, code, image)
            for instruction, code, image in zip(instructions, codes, images_input)
        ]

        return self.api.batch_chat_request(messages, ids)

    def _create_message(
        self, instruction: str, code: str, image: Image.Image
    ) -> Iterable[ChatCompletionMessageParam]:
        """Add a row that contains the prompt"""

        # Some multimodal models do not support system prompts, so we only use the user prompt as input

        user_instruction = MULTIMODAL_INSTRUCTION.format(
            instruction=instruction, content=code
        )

        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_instruction,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_str}",
                            "detail": "low",
                        },
                    },
                ],
            },
        ]

        return messages