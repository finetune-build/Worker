from finetune_worker import register_agent 

from transformers import GPT2Tokenizer, GPT2LMHeadModel
import torch

@register_agent
def generate_text(prompt, max_length=50):
    # Load model and tokenizer
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    model = GPT2LMHeadModel.from_pretrained("gpt2")
    model.eval()

    # Encode input prompt
    input_ids = tokenizer.encode(prompt, return_tensors="pt")

    # Generate output
    with torch.no_grad():
        output_ids = model.generate(
            input_ids,
            max_length=max_length,
            num_return_sequences=1,
            do_sample=True,
            top_k=50,
            top_p=0.95,
            temperature=0.9,
        )

    # Decode output
    generated_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    return generated_text
