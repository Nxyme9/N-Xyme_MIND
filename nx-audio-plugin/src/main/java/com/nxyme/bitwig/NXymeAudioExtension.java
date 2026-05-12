package com.nxyme.bitwig;

import com.bitwig.extension.controller.api.*;
import com.bitwig.extensions.framework.Layer;
import com.bitwig.extensions.framework.Layers;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.util.ArrayList;
import java.util.List;

public class NXymeAudioExtension extends ControllerExtension {
    
    private final String HOST = "127.0.0.1";
    private final int OSC_SEND_PORT = 8000;
    private final int OSC_RECEIVE_PORT = 9000;
    
    private ControllerHost host;
    private Transport transport;
    private TrackBank trackBank;
    private HardwareSurface hardwareSurface;
    private Layers layers;
    private Layer mainLayer;
    private DatagramSocket oscSocket;
    
    private boolean neuralMode = false;
    private float modelMix = 0.5f;
    private String currentModel = "default";
    private int selectedTrack = 0;
    
    private final String[] MODELS = {"default", "vocals", "drums", "bass", "synth"};
    private final String[] FX_NAMES = {"reverb", "delay", "compress", "eq", "distort"};
    
    public NXymeAudioExtension(NXymeAudioExtensionDefinition definition, ControllerHost host) {
        super(definition, host);
        this.host = host;
    }
    
    @Override
    public void init() {
        host = getHost();
        
        transport = host.createTransport();
        transport.isPlaying().markInterested();
        transport.isRecording().markInterested();
        
        trackBank = host.createTrackBank(8, 0, 8, true);
        
        hardwareSurface = host.createHardwareSurface();
        hardwareSurface.setPhysicalSize(800, 400);
        
        layers = new Layers(this);
        mainLayer = new Layer(layers, "Main");
        
        setupMidiPorts();
        setupControls();
        setupBindings();
        
        mainLayer.activate();
        
        initOSC();
        
        host.showPopupNotification("N-Xyme Audio v1.0 Ready!");
    }
    
    private void setupMidiPorts() {
        // Virtual MIDI ports - not actually used for hardware
        // OSC is used for communication instead
    }
    
    private void setupControls() {
        // Transport controls
        HardwareButton playBtn = hardwareSurface.createHardwareButton("play");
        playBtn.setLabel("PLAY");
        
        HardwareButton stopBtn = hardwareSurface.createHardwareButton("stop");
        stopBtn.setLabel("STOP");
        
        HardwareButton recBtn = hardwareSurface.createHardwareButton("record");
        recBtn.setLabel("REC");
        
        // BPM control via relative knob
        RelativeHardwareKnob bpmKnob = hardwareSurface.createRelativeHardwareKnob("bpm");
        bpmKnob.setLabel("BPM");
        
        // Model selection
        List<HardwareButton> modelButtons = new ArrayList<>();
        for (int i = 0; i < MODELS.length; i++) {
            HardwareButton btn = hardwareSurface.createHardwareButton("model_" + MODELS[i]);
            btn.setLabel(MODELS[i].toUpperCase());
            modelButtons.add(btn);
        }
        
        // Model mix slider
        HardwareSlider mixSlider = hardwareSurface.createHardwareSlider("modelMix");
        mixSlider.setLabel("MIX");
        
        // Neural mode toggle
        HardwareButton neuralBtn = hardwareSurface.createHardwareButton("neural");
        neuralBtn.setLabel("NEURAL");
        
        // Track selection buttons
        List<HardwareButton> trackButtons = new ArrayList<>();
        for (int i = 0; i < 8; i++) {
            HardwareButton btn = hardwareSurface.createHardwareButton("track_" + i);
            btn.setLabel("T" + (i + 1));
            trackButtons.add(btn);
        }
        
        // FX buttons
        List<HardwareButton> fxButtons = new ArrayList<>();
        for (int i = 0; i < FX_NAMES.length; i++) {
            HardwareButton btn = hardwareSurface.createHardwareButton("fx_" + FX_NAMES[i]);
            btn.setLabel(FX_NAMES[i].toUpperCase());
            fxButtons.add(btn);
        }
    }
    
    private void setupBindings() {
        // Transport bindings would use actual MIDI actions
        // For now, the controls are visual representation
        // OSC is used for actual communication
    }
    
    private void initOSC() {
        try {
            oscSocket = new DatagramSocket(OSC_RECEIVE_PORT);
            host.println("OSC initialized on port " + OSC_RECEIVE_PORT);
        } catch (Exception e) {
            host.println("OSC Error: " + e.getMessage());
        }
    }
    
    @Override
    public void flush() {
        if (hardwareSurface != null) {
            hardwareSurface.updateHardware();
        }
    }
    
    @Override
    public void exit() {
        if (oscSocket != null) {
            oscSocket.close();
        }
        host.showPopupNotification("N-Xyme Audio disconnected");
    }
    
    private void sendOSC(String address, Object... args) {
        try {
            StringBuilder msg = new StringBuilder(address);
            for (Object arg : args) {
                msg.append(" ").append(arg);
            }
            msg.append("\n");
            
            byte[] data = msg.toString().getBytes();
            DatagramPacket packet = new DatagramPacket(
                data, data.length, InetAddress.getByName(HOST), OSC_SEND_PORT);
            oscSocket.send(packet);
        } catch (Exception e) {
            host.println("OSC Send Error: " + e.getMessage());
        }
    }
    
    private String[] receiveOSC() {
        try {
            byte[] buffer = new byte[1024];
            DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
            oscSocket.receive(packet);
            return new String(packet.getData(), 0, packet.getLength()).split(" ");
        } catch (Exception e) {
            return null;
        }
    }
}