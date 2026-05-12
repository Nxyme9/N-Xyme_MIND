package com.nxyme.bitwig;

import java.util.UUID;
import com.bitwig.extension.api.PlatformType;
import com.bitwig.extension.controller.AutoDetectionMidiPortNamesList;
import com.bitwig.extension.controller.ControllerExtensionDefinition;
import com.bitwig.extension.controller.api.ControllerHost;

/**
 * Controller Extension Definition for N-Xyme Audio Plugin
 * Provides metadata and factory for the extension
 */
public class NXymeAudioExtensionDefinition extends ControllerExtensionDefinition {
    
    private static final UUID DRIVER_ID = UUID.fromString("A1B2C3D4-E5F6-7890-ABCD-EF1234567890");
    
    public static final NXymeAudioExtensionDefinition INSTANCE = new NXymeAudioExtensionDefinition();
    
    private NXymeAudioExtensionDefinition() {
        // Singleton
    }
    
    @Override
    public String getName() {
        return "N-Xyme Audio";
    }
    
    @Override
    public String getAuthor() {
        return "N-Xyme";
    }
    
    @Override
    public String getVersion() {
        return "1.0.0";
    }
    
    @Override
    public UUID getId() {
        return DRIVER_ID;
    }
    
    @Override
    public String getHardwareVendor() {
        return "N-Xyme";
    }
    
    @Override
    public String getHardwareModel() {
        return "N-Xyme Audio Plugin";
    }
    
    @Override
    public int getRequiredAPIVersion() {
        return 25;
    }
    
    @Override
    public int getNumMidiInPorts() {
        return 1;  // Virtual MIDI port for OSC communication
    }
    
    @Override
    public int getNumMidiOutPorts() {
        return 1;
    }
    
    @Override
    public void listAutoDetectionMidiPortNames(final AutoDetectionMidiPortNamesList list,
                                                final PlatformType platformType) {
        // No auto-detection - manual activation only
        list.add(new String[]{"N-Xyme Audio"}, new String[]{"N-Xyme Audio"});
    }
    
    @Override
    public NXymeAudioExtension createInstance(final ControllerHost host) {
        return new NXymeAudioExtension(this, host);
    }
}