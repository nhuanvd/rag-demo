# Models Directory

This directory should contain your quantized GGML model files compatible with llama-cpp-python.

## Required Model

Place a quantized model file named `small-model.ggml` in this directory.

## Getting a Model

You can find small quantized models at:
- Hugging Face Model Hub (search for "ggml" models)
- TheBloke's quantized models on Hugging Face
- Official LLaMA model repositories (requires license acceptance)

## Example Models

- LLaMA 2 7B quantized (q4_0, q4_1, q5_0, q5_1, q8_0)
- LLaMA 2 13B quantized (if you have more resources)
- Other compatible GGML models

## Model Requirements

- Must be in GGML format
- Compatible with llama-cpp-python
- Quantized for efficient inference
- Small enough to run on your hardware

## License Compliance

Make sure to comply with the model's license requirements before downloading and using any model files.
