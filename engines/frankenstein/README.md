# Frankenstein Engine 🔩

**My first engine.** Written in C++ before I knew C++. Zero coding background.

Ran in production until May 2026, when it was replaced by the Mojo stack.

A llama.cpp-based batch inference server with hot-swappable models, dynamic batching, and GPU monitoring.

## What it does

```
multiple GGUF models → loaded into registry → hot-swap mid-session
                        ↓
              dynamic batch (parallel sequences)
                        ↓
              GPU offloaded (n_gpu_layers = 99)
              Flash attention
              KV cache quantized (Q4_0)
              16 threads (7800X3D)
```

## Build

```bash
mkdir build && cd build
cmake .. && make
./frankenstein-engine -m model.gguf -p "Hello" -n 64 -np 4
```

## Hot-swap

```bash
./frankenstein-engine --model model1.gguf --model-add model2.gguf --model-add model3.gguf
```

## Timeline

- **November 2025**: Started as "AE Whisper Project" — voice-to-AfterEffects scripting
- **January 2026**: First C++ inference engine (this file)
- **January → May 2026**: Ran production inference for every model call
- **May 2026**: Replaced by Mojo stack — 6,181 lines, Tensor Core kernels, consciousness engine

---

*"I couldn't code. Then I built this. Then I built an agent OS in Mojo."*
