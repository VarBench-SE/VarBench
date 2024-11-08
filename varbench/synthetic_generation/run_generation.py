import argparse
from enum import Enum
import pandas as pd
from tqdm import tqdm
from varbench.compilers import Compiler, TexCompiler, SvgCompiler, CompilerException
from varbench.model import API_model, LLM_Model, ModelType, VLLM_model
from varbench.utils.diffs import diffs
from varbench.utils.parsing import get_first_code_block
from .api_generation import (
    groq_generation_format,
    openai_generation_format,
)
import os
from datasets import Dataset, Features, Sequence, Value, Image
from loguru import logger
from ..prompt_templates import (
    SYSTEM_PROMPT_GENERATION,
    SYSTEM_PROMPT_INSTRUCTIONS,
    IT_PROMPT,
)


class ApiType(Enum):
    OPENAI = 0
    GROQ = 1


def api_type_mapper(value):
    api_map = {"OPENAI": ApiType.OPENAI, "GROQ": ApiType.GROQ}
    if value.upper() not in api_map:
        raise argparse.ArgumentTypeError(f"Invalid API type: {value}")
    return api_map[value.upper()]


def model_type_mapper(value):
    api_map = {"API": ModelType.API, "VLLM": ModelType.VLLM}
    if value.upper() not in api_map:
        raise argparse.ArgumentTypeError(f"Invalid API type: {value}")
    return api_map[value.upper()]


parser = argparse.ArgumentParser()

parser.add_argument(
    "--api_type_ins",
    "-a",
    type=api_type_mapper,
    help="type of the api to use for the instruction generator",
    default=ApiType.GROQ,
)
parser.add_argument(
    "--model_ins",
    "-mi",
    type=str,
    required=True,
    help="Name of the model to use the instruction generator",
)

parser.add_argument(
    "--model_type_gen",
    "-t",
    type=model_type_mapper,
    help="type of the model to use for the code generation",
    default=ModelType.VLLM,
)
parser.add_argument(
    "--model_gen",
    "-mg",
    type=str,
    required=True,
    help="Name of the model to use for the code generation",
)

parser.add_argument(
    "--temperature",
    type=float,
    default=0.7,
    help="Temperature setting for model sampling",
)

parser.add_argument(
    "--folder",
    "-f",
    type=str,
    required=True,
    help="path to the folder that contains the code files to use as input",
)

parser.add_argument(
    "--number_gen",
    "-ng",
    type=int,
    required=False,
    default=5,
    help="The number of example of modifications generated by the llm(not certified to be exactly the one provided)",
)

parser.add_argument(
    "--api_url",
    type=str,
    default="https://api.openai.com/v1",
    help="URL of the openai completion compatible API",
)
parser.add_argument(
    "--passk", "-k", type=int, default=3, help="Number of generations per prompt"
)
parser.add_argument(
    "--api_key",
    type=str,
    default=None,
    help="API key for authentication, will default to the ENV variable OPENAI_API_KEY",
)

parser.add_argument(
    "--gpu_number", type=int, default=1, help="GPU number to use for evaluation"
)

args = parser.parse_args()

api_type_ins = args.api_type_ins
model_ins = args.model_ins
temperature = args.temperature

model_type_gen = args.model_type_gen

folder_path = os.path.abspath(args.folder)
number_gen = args.number_gen
match api_type_ins:
    case ApiType.GROQ:
        instructor = groq_generation_format
    case ApiType.OPENAI:
        instructor = openai_generation_format


key_args: dict = {}
key_args["model_name"] = args.model_gen
key_args["gpu_number"] = args.gpu_number
key_args["api_url"] = args.api_url
key_args["api_key"] = args.api_key
key_args["temperature"] = args.temperature
key_args["no_batch"] = True
key_args["n"] = args.passk

llm_model: LLM_Model = None
# loading model
match model_type_gen:
    case ModelType.API:
        llm_model = API_model(**key_args)
    case ModelType.VLLM:
        llm_model = VLLM_model(**key_args)


unfiltered_dataset = {}
for subset in tqdm(os.listdir(folder_path), position=0, desc="Treating the subsets"):
    # creating compiler
    compiler: Compiler = None
    match subset:
        case "tikz":
            compiler = TexCompiler()
        case "svg":
            compiler = SvgCompiler()
        case _:
            logger.warning(f"unsupported subset {subset}")
            continue
    current_subset = []
    for code_file in tqdm(
        os.listdir(os.path.join(folder_path, subset)),
        position=1,
        desc="Treating the files",
    ):
        file_path = os.path.join(folder_path, subset, code_file)
        with open(file_path, "r") as file:

            ##################"Generating instructions"###############
            content = file.read()

            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_INSTRUCTIONS.format(
                        number_generation=number_gen
                    ),
                },
                {"role": "user", "content": content},
            ]
            # generating responses
            modifications = instructor(
                messages=messages, model=model_ins, temperature=temperature
            )

            ##################"Generating modifications"################
            all_images = []
            all_possible_codes = []
            for modification in tqdm(modifications,position=3,desc="Treating the  modifications"):

                # prompt
                user_instruction = IT_PROMPT.format(
                    instruction=modification.instruction, content=content
                )

                messages = [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT_GENERATION,
                    },
                    {"role": "user", "content": user_instruction},
                ]

                # generating
                possible_codes = llm_model.request(messages=messages)
                possible_codes = [
                    get_first_code_block(possible_code)
                    for possible_code in possible_codes
                ]
                # Making a list of images
                compiling_images = []
                treated_codes = (
                    set()
                )  # to ensure we don't compile the codes multiple times
                for code in possible_codes:
                    if code in treated_codes:
                        continue
                    treated_codes.add(code)
                    try:
                        current_image = compiler.compile_from_string(code)
                        compiling_images.append(current_image)
                    except CompilerException:
                        logger.info("Image compiling failed")
                all_possible_codes.append(treated_codes)
                if len(compiling_images) == 0:
                    all_images.append(None)
                else:
                    all_images.append(compiling_images)

            ################ creating a dataset ##############
            for modification in zip(modifications, all_images, content, possible_codes):
                if not modification[1]:
                    continue
                current_diffs = diffs(content, modification[3])
                current_subset.append(
                    {
                        "id": modification[0].id,
                        "code": content,
                        "result_description": modification[0].result_description,
                        "instruction": modification[0].instruction,
                        "image_solution": modification[1],
                        "diffs": current_diffs,
                    }
                )
    if len(current_subset) > 0:
        unfiltered_dataset[subset] = current_subset

features = Features(
    {
        "id": Value("string"),
        "code": Value("string"),
        "instruction": Value("string"),
        "result_description": Value("string"),
        "diffs": Sequence(Value("string")),
        "image_solution": Sequence(Image()),
    }
)

for subset in unfiltered_dataset:
    current_subset = pd.DataFrame(unfiltered_dataset[subset])
    dataset = Dataset.from_dict(pd.DataFrame(current_subset), features=features)
    dataset.push_to_hub(
        "CharlyR/varbench-synthetic", config_name=subset, split="unfiltered"
    )
