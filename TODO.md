# TODO

- [X] either make a script to add an entry in the dataset or just doucemnt the command to do it.
- [X] diff computation
- [X] Make the dataset with a python script
- [X] refactor dataset creation
- [X] change diff computation
- [X] refactor run-evaluation
  - [X] Use vllm and openai inference via a wrapper for evaluation(get inspired by https://github.com/HumanEval-V/HumanEval-V-Benchmark/blob/main/models/vllm_model.py)
- [X] Finish implementing openai batch api
- [X] Add an api option for run evaluation
- [X] Make a score object and change the evaluator to return it (change the tests as well)
- [X] Remake latex-Compiler
- [X] Make some first simple data
- [X] text squid, find other possible solutions for dataset
- [X] implement pass@k
- [X] test pass@k
- [X] complex oracle
  - [X] vlm or computer-vision("Are the eyes red")
  - [X] Image comparison(image diff)
  - [X] line diff(need to think, either same as before with only one column diff, or a new one with only the lines)
- [X] Test compilers when image not compilable
- [X] Fix evaluator tests
- [X] fix line diff
- [X] Add vision input possibility in model class (both vllm and openai->https://platform.openai.com/docs/guides/vision)
- [X] fix workflow
- [X] Add a config file containing vllm config 
- [ ] Add backup at each step for synthetic data generation
- [ ] Create synthetic data and then verify
- [ ] Make another submodel called multimodal that can take images, and allow for parametrization in the command line
- [ ] Make another submodel called multimodal-loop that can take images and loops until a satifying image is created, and allow for parametrization in the command line.
- [ ] Assessment of vlm on checking 
- [ ] Test LLM-only models then compare with Multimodal with image in input
- [ ] Implement LLM+something solution and test it
- [ ] Explore which other things can be tested(tikz, svg, ascii, what else?)
Eventually
- [ ] ascii art "compiler"
- [ ] github action
  - [ ] creates and publishes the dataset

