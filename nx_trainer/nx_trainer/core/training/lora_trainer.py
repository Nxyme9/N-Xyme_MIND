import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, TaskType
import logging


class LoRATrainer:
    def __init__(
        self,
        model_name: str,
        output_dir: str = "./output",
        rank: int = 16,
        alpha: int = 32,
        lr: float = 3e-4,
        epochs: int = 3,
        batch_size: int = 8,
        gradient_checkpointing: bool = True,
        use_4bit: bool = False,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        self.model_name = model_name
        self.output_dir = output_dir
        self.rank = rank
        self.alpha = alpha
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.gradient_checkpointing = gradient_checkpointing
        self.use_4bit = use_4bit
        self.device = device
        self.logger = logging.getLogger("nx_trainer.lora")

    def load_model_and_tokenizer(self):
        self.logger.info(f"Loading model: {self.model_name}")
        
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            use_fast=False,
        )
        tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.bfloat16,
            device_map=self.device,
            trust_remote_code=True,
        )

        return model, tokenizer

    def prepare_lora_model(self, model):
        lora_config = LoraConfig(
            r=self.rank,
            lora_alpha=self.alpha,
            target_modules=[
                "q_proj", "v_proj", "k_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj"
            ],
            lora_dropout=0.05,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )

        model = get_peft_model(model, lora_config)
        
        if self.gradient_checkpointing:
            model.enable_gradient_checkpointing()

        model.print_trainable_parameters()
        
        return model

    def train(self, dataset: Dataset):
        model, tokenizer = self.load_model_and_tokenizer()
        model = self.prepare_lora_model(model)

        training_args = TrainingArguments(
            output_dir=self.output_dir,
            num_train_epochs=self.epochs,
            per_device_train_batch_size=self.batch_size,
            learning_rate=self.lr,
            logging_steps=10,
            save_steps=500,
            eval_steps=500,
            save_total_limit=3,
            bf16=True,
            logging_dir=f"{self.output_dir}/logs",
            report_to="none",
            remove_unused_columns=False,
        )

        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,
        )

        from transformers import Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            data_collator=data_collator,
        )

        self.logger.info("Starting training...")
        trainer.train()
        
        self.logger.info(f"Saving adapter to {self.output_dir}/adapter")
        model.save_pretrained(f"{self.output_dir}/adapter")
        
        return model

    def save_adapter(self, model, path: str):
        model.save_pretrained(path)
        self.logger.info(f"Adapter saved to {path}")

    def merge_and_save(self, model, base_model_path: str, output_path: str):
        _ = AutoModelForCausalLM.from_pretrained(
            base_model_path,
            torch_dtype=torch.bfloat16,
            device_map="cpu",
            trust_remote_code=True,
        )
        
        merged_model = model.merge_and_unload()
        merged_model.save_pretrained(output_path)
        self.logger.info(f"Merged model saved to {output_path}")