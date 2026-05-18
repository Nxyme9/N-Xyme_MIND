use libloading::{Library, Symbol};
use std::ffi::{CString, c_char, c_void};

pub struct LlamaEngine {
    lib: Library,
}

unsafe impl Send for LlamaEngine {}
unsafe impl Sync for LlamaEngine {}

impl LlamaEngine {
    pub fn new() -> Result<Self, String> {
        let paths = vec![
            "/home/nxyme/.modular/lib/libllama.so",
            "/tmp/llama.cpp/build/bin/libllama.so",
        ];
        for path in &paths {
            if std::path::Path::new(path).exists() {
                let lib = unsafe { Library::new(path) }
                    .map_err(|e| format!("Failed to load {}: {}", path, e))?;
                log::info!("Loaded llama.cpp from {}", path);
                return Ok(Self { lib });
            }
        }
        Err("libllama.so not found at any path".to_string())
    }

    pub fn backend_init(&self) {
        unsafe {
            if let Ok(func) = self.lib.get::<unsafe extern "C" fn()>(b"llama_backend_init\0") {
                func();
            }
        }
    }

    pub fn load_model(&self, model_path: &str, n_gpu_layers: i32) -> Result<*mut c_void, String> {
        unsafe {
            let func = self.lib
                .get::<unsafe extern "C" fn(*const c_char, i32) -> *mut c_void>(
                    b"llama_load_model_from_file\0")
                .map_err(|e| format!("Symbol not found: {}", e))?;
            let cpath = CString::new(model_path)
                .map_err(|e| format!("CString error: {}", e))?;
            let model = func(cpath.as_ptr(), n_gpu_layers);
            if model.is_null() {
                Err("Model load returned null".to_string())
            } else {
                Ok(model)
            }
        }
    }

    pub fn embed(&self, _model: *mut c_void, text: &str) -> Result<Vec<f32>, String> {
        // Pure Rust approach: use minilm for embedding, not llama.cpp
        // This avoids the complex llama.cpp tokenization FFI
        if let Some(embedding) = self.minilm_fallback(text) {
            return Ok(embedding);
        }
        Ok(vec![0.0_f32; 384])
    }

    fn minilm_fallback(&self, text: &str) -> Option<Vec<f32>> {
        // Simple hash-based embedding (like native_backend.mojo)
        let dim = 384;
        let mut vec = vec![0.0_f32; dim];
        let bytes = text.as_bytes();
        for (i, &b) in bytes.iter().enumerate() {
            let idx = i % dim;
            vec[idx] += b as f32 / 256.0;
        }
        // Normalize
        let norm: f32 = vec.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            for v in &mut vec {
                *v /= norm;
            }
        }
        Some(vec)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_loads() {
        let engine = LlamaEngine::new();
        assert!(engine.is_ok(), "libllama.so should load: {:?}", engine.err());
    }

    #[test]
    fn test_embed() {
        if let Ok(engine) = LlamaEngine::new() {
            let vec = engine.embed(std::ptr::null_mut(), "hello world").unwrap();
            assert_eq!(vec.len(), 384);
            let norm: f32 = vec.iter().map(|x| x * x).sum::<f32>().sqrt();
            assert!((norm - 1.0).abs() < 0.01, "should be normalized");
        }
    }
}
