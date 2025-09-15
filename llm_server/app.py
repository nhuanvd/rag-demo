from fastapi import FastAPI
from pydantic import BaseModel
import os
from llama_cpp import Llama


MODEL_PATH = os.getenv("MODEL_PATH", "/models/small-model.ggml")


print("Loading model from", MODEL_PATH)
llm = Llama(model_path=MODEL_PATH)


app = FastAPI()


class GenReq(BaseModel):
    prompt: str
    max_tokens: int = 256


@app.post("/generate")
async def generate(req: GenReq):
    # llama-cpp-python has sync API; wrap simply
    out = llm.create(prompt=req.prompt, max_tokens=req.max_tokens)
    return {"text": out["choices"][0]["text"]}


@app.get("/health")
async def health():
    return {"status": "ok"}
