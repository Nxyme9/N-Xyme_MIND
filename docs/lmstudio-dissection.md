# LM Studio Dissection - Finding the Performance Gap

## Hypothesis: Why LM Studio is Faster

1. **Custom CUDA compile flags** - Different optimization levels
2. **Different GGML flags** - Hidden pre-processor defines  
3. **Different runtime flags** - Settings we can't see
4. **Speculative decoding** - Enabled by default
5. **Graph optimization** - USE_GRAPHS differently configured

## Investigation Checklist

- [ ] Check LM Studio bundled llama.cpp version
- [ ] Compare compile flags between builds
- [ ] Check for speculative decoding support
- [ ] Examine GPU memory allocation strategy
- [ ] Check for custom KV cache handling
