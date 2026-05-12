package com.nxyme.bitwig;

import org.deeplearning4j.nn.modelimport.keras.KerasModelImport;
import org.deeplearning4j.nn.modelimport.keras.exceptions.InvalidKerasConfigurationException;
import org.deeplearning4j.nn.modelimport.keras.exceptions.UnsupportedKerasConfigurationException;
import org.deeplearning4j.nn.multilayer.MultiLayerNetwork;
import org.nd4j.linalg.api.ndarray.INDArray;
import org.nd4j.linalg.factory.Nd4j;
import org.nd4j.common.io.ClassPathResource;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

public class ONNXModelLoader {
    
    private Map<String, MultiLayerNetwork> loadedModels = new HashMap<>();
    private String activeModel = null;
    private final String modelsPath;
    
    public ONNXModelLoader(String modelsPath) {
        this.modelsPath = modelsPath;
    }
    
    public boolean loadModel(String modelName) {
        String modelFile = modelsPath + "/" + modelName + ".onnx";
        File f = new File(modelFile);
        
        if (!f.exists()) {
            modelFile = modelsPath + "/" + modelName + ".h5";
            f = new File(modelFile);
        }
        
        if (!f.exists()) {
            return false;
        }
        
        try {
            MultiLayerNetwork model;
            if (modelFile.endsWith(".h5")) {
                model = KerasModelImport.importKerasSequentialModel(modelFile);
            } else {
                return false;
            }
            
            loadedModels.put(modelName, model);
            activeModel = modelName;
            return true;
        } catch (IOException | InvalidKerasConfigurationException | UnsupportedKerasConfigurationException e) {
            System.err.println("Model load error: " + e.getMessage());
            return false;
        }
    }
    
    public INDArray processAudio(float[] audioData) {
        if (activeModel == null || !loadedModels.containsKey(activeModel)) {
            return null;
        }
        
        MultiLayerNetwork model = loadedModels.get(activeModel);
        
        INDArray input = Nd4j.create(audioData);
        if (input.shape().length == 1) {
            input = input.reshape(1, audioData.length);
        }
        
        INDArray output = model.output(input);
        return output;
    }
    
    public float[] processAudioSimple(float[] audioData) {
        INDArray result = processAudio(audioData);
        if (result == null) return audioData;
        
        return result.flatten().toFloatVector();
    }
    
    public void setActiveModel(String modelName) {
        if (loadedModels.containsKey(modelName)) {
            activeModel = modelName;
        }
    }
    
    public String[] getLoadedModels() {
        return loadedModels.keySet().toArray(new String[0]);
    }
    
    public String getActiveModel() {
        return activeModel;
    }
    
    public void unloadModel(String modelName) {
        loadedModels.remove(modelName);
        if (activeModel.equals(modelName)) {
            activeModel = loadedModels.isEmpty() ? null : loadedModels.keySet().iterator().next();
        }
    }
    
    public void unloadAll() {
        loadedModels.clear();
        activeModel = null;
    }
}