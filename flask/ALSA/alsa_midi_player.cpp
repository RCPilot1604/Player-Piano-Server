#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <algorithm>
#include <sstream>
#include <alsa/asoundlib.h>
#include <jsoncpp/json/json.h>

struct MidiEvent {
    int tick;
    double time_ms;
    int channel;
    std::string type;
    int note_number;
    int velocity;
    std::vector<unsigned char> data;
    
    MidiEvent() : tick(0), time_ms(0.0), channel(0), note_number(-1), velocity(0) {}
};

struct TempoChange {
    int tick;
    int tempo; // microseconds per quarter note
    double time_ms;
};

class AlsaSequencerController {
private:
    snd_seq_t* seq_handle;
    int client_id;
    int port_id;
    int queue_id;  // Changed from snd_seq_queue_t to int
    
    std::vector<MidiEvent> events;
    std::vector<TempoChange> tempo_changes;
    std::atomic<bool> is_playing{false};
    std::atomic<bool> should_stop{false};
    std::atomic<bool> is_loaded{false};
    
    std::thread control_thread;
    std::thread playback_thread;
    std::mutex sequencer_mutex;
    
    // Playback state
    std::atomic<double> current_position_ms{0.0};
    std::atomic<int> current_tick{0};
    std::chrono::high_resolution_clock::time_point start_time;
    double pause_offset_ms = 0.0;
    
public:
    AlsaSequencerController() : seq_handle(nullptr), client_id(-1), port_id(-1), queue_id(-1) {}
    
    ~AlsaSequencerController() {
        cleanup();
    }
    
    bool initialize() {
        // Open ALSA sequencer
        int result = snd_seq_open(&seq_handle, "default", SND_SEQ_OPEN_OUTPUT, 0);
        if (result < 0) {
            std::cerr << "Error: Cannot open ALSA sequencer: " << snd_strerror(result) << std::endl;
            return false;
        }
        
        // Set client name
        snd_seq_set_client_name(seq_handle, "PlayerPianoSequencer");
        
        // Get client ID
        client_id = snd_seq_client_id(seq_handle);
        
        // Create output port
        port_id = snd_seq_create_simple_port(seq_handle, "MIDI Output",
            SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ,
            SND_SEQ_PORT_TYPE_APPLICATION | SND_SEQ_PORT_TYPE_MIDI_GENERIC);
            
        if (port_id < 0) {
            std::cerr << "Error: Cannot create ALSA port: " << snd_strerror(port_id) << std::endl;
            return false;
        }
        
        // Create queue for timing
        queue_id = snd_seq_alloc_named_queue(seq_handle, "PlayerPianoQueue");
        if (queue_id < 0) {
            std::cerr << "Error: Cannot create ALSA queue: " << snd_strerror(queue_id) << std::endl;
            return false;
        }
        
        // Start the queue
        snd_seq_start_queue(seq_handle, queue_id, NULL);
        snd_seq_drain_output(seq_handle);
        
        std::cout << "ALSA Sequencer initialized successfully" << std::endl;
        std::cout << "Client: " << client_id << ", Port: " << port_id << ", Queue: " << queue_id << std::endl;
        std::cout << "Connect with: aconnect " << client_id << ":" << port_id << " <destination>" << std::endl;
        
        return true;
    }
    
    bool load_events(const std::string& json_file) {
        std::ifstream file(json_file);
        if (!file.is_open()) {
            std::cerr << "Error: Cannot open events file: " << json_file << std::endl;
            return false;
        }
        
        Json::Value root;
        Json::CharReaderBuilder builder;
        std::string errors;
        
        if (!Json::parseFromStream(builder, file, &root, &errors)) {
            std::cerr << "Error parsing JSON: " << errors << std::endl;
            return false;
        }
        
        std::lock_guard<std::mutex> lock(sequencer_mutex);
        
        events.clear();
        tempo_changes.clear();
        
        // Load tempo changes if available
        if (root.isMember("tempo_changes")) {
            const Json::Value& tempo_array = root["tempo_changes"];
            for (const auto& tempo_json : tempo_array) {
                TempoChange tempo;
                tempo.tick = tempo_json["tick"].asInt();
                tempo.tempo = tempo_json["tempo"].asInt();
                tempo.time_ms = tempo_json.get("time_ms", 0.0).asDouble();
                tempo_changes.push_back(tempo);
            }
        }
        
        // Load MIDI events
        const Json::Value& events_array = root["events"];
        for (const auto& event_json : events_array) {
            MidiEvent event;
            event.tick = event_json["tick"].asInt();
            event.time_ms = event_json["time_ms"].asDouble();
            event.channel = event_json["channel"].asInt();
            event.type = event_json["type"].asString();
            
            if (event_json.isMember("note_number") && !event_json["note_number"].isNull()) {
                event.note_number = event_json["note_number"].asInt();
            }
            if (event_json.isMember("velocity") && !event_json["velocity"].isNull()) {
                event.velocity = event_json["velocity"].asInt();
            }
            
            // Parse MIDI data bytes
            if (event_json.isMember("data") && event_json["data"].isArray()) {
                const Json::Value& data_array = event_json["data"];
                for (const auto& byte : data_array) {
                    event.data.push_back(static_cast<unsigned char>(byte.asInt()));
                }
            }
            
            events.push_back(event);
        }
        
        // Sort events by time
        std::sort(events.begin(), events.end(), 
                 [](const MidiEvent& a, const MidiEvent& b) {
                     return a.time_ms < b.time_ms;
                 });
        
        is_loaded = true;
        std::cout << "Loaded " << events.size() << " MIDI events and " 
                  << tempo_changes.size() << " tempo changes" << std::endl;
        
        if (!events.empty()) {
            std::cout << "Duration: " << events.back().time_ms / 1000.0 << " seconds" << std::endl;
        }
        
        return true;
    }
    
    void play() {
        std::lock_guard<std::mutex> lock(sequencer_mutex);
        
        if (!is_loaded) {
            std::cerr << "Error: No MIDI file loaded" << std::endl;
            return;
        }
        
        if (is_playing) {
            return; // Already playing
        }
        
        is_playing = true;
        should_stop = false;
        
        // Calculate start time considering pause offset
        start_time = std::chrono::high_resolution_clock::now() - 
                    std::chrono::milliseconds(static_cast<long>(pause_offset_ms));
        
        // Start playback thread
        if (playback_thread.joinable()) {
            playback_thread.join();
        }
        playback_thread = std::thread(&AlsaSequencerController::playback_loop, this);
        
        // Start control thread for position tracking
        if (control_thread.joinable()) {
            control_thread.join();
        }
        control_thread = std::thread(&AlsaSequencerController::control_loop, this);
        
        std::cout << "Playback started" << std::endl;
    }
    
    void pause() {
        std::lock_guard<std::mutex> lock(sequencer_mutex);
        
        if (!is_playing) {
            return; // Already paused
        }
        
        is_playing = false;
        
        // Calculate pause offset
        auto now = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time);
        pause_offset_ms = elapsed.count();
        
        // Stop all notes
        stop_all_notes();
        
        std::cout << "Playback paused at " << pause_offset_ms << "ms" << std::endl;
    }
    
    void stop() {
        std::lock_guard<std::mutex> lock(sequencer_mutex);
        
        is_playing = false;
        pause_offset_ms = 0.0;
        current_position_ms = 0.0;
        current_tick = 0;
        
        // Stop all notes
        stop_all_notes();
        
        std::cout << "Playback stopped and reset" << std::endl;
    }
    
    void seek(int tick) {
        std::lock_guard<std::mutex> lock(sequencer_mutex);
        
        // Find corresponding time
        double target_time = 0;
        for (const auto& event : events) {
            if (event.tick >= tick) {
                target_time = event.time_ms;
                break;
            }
        }
        
        pause_offset_ms = target_time;
        current_position_ms = target_time;
        current_tick = tick;
        
        if (is_playing) {
            start_time = std::chrono::high_resolution_clock::now() - 
                        std::chrono::milliseconds(static_cast<long>(pause_offset_ms));
        }
        
        stop_all_notes();
        
        std::cout << "Seeked to tick " << tick << " (time: " << target_time << "ms)" << std::endl;
    }
    
    void quit() {
        should_stop = true;
        is_playing = false;
        
        if (playback_thread.joinable()) {
            playback_thread.join();
        }
        if (control_thread.joinable()) {
            control_thread.join();
        }
        
        stop_all_notes();
        std::cout << "Sequencer shutting down" << std::endl;
    }
    
    // Status information
    double get_position_ms() const { return current_position_ms.load(); }
    int get_current_tick() const { return current_tick.load(); }
    bool get_is_playing() const { return is_playing.load(); }
    bool get_is_loaded() const { return is_loaded.load(); }
    
private:
    void playback_loop() {
        while (is_playing && !should_stop) {
            auto now = std::chrono::high_resolution_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time);
            double current_time = elapsed.count();
            
            // Find and play events at current time
            for (const auto& event : events) {
                if (event.time_ms <= current_time && 
                    event.time_ms > current_time - 10) { // 10ms tolerance
                    send_midi_event(event);
                }
                
                // Skip events that are too far in the future
                if (event.time_ms > current_time + 100) {
                    break;
                }
            }
            
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
    
    void send_midi_event(const MidiEvent& event) {
        if (!seq_handle) return;
        
        #ifdef SERIAL_DEBUG
            std::cout << "Sending MIDI event: type=" << event.type
            << " channel=" << event.channel
            << " note=" << event.note_number
            << " velocity=" << event.velocity << std::endl;
        #endif
        snd_seq_event_t seq_event;
        snd_seq_ev_clear(&seq_event);
        
        // Set source port
        snd_seq_ev_set_source(&seq_event, port_id);
        snd_seq_ev_set_subs(&seq_event);
        snd_seq_ev_set_direct(&seq_event);
        
        bool event_sent = false;
        
        if (event.type == "note_on" && event.velocity > 0) {
            snd_seq_ev_set_noteon(&seq_event, event.channel, event.note_number, event.velocity);
            event_sent = true;
        } 
        else if (event.type == "note_off" || (event.type == "note_on" && event.velocity == 0)) {
            snd_seq_ev_set_noteoff(&seq_event, event.channel, event.note_number, 
                                  event.velocity > 0 ? event.velocity : 64);
            event_sent = true;
        } 
        else if (event.type == "control_change" && event.data.size() >= 3) {
            snd_seq_ev_set_controller(&seq_event, event.channel, event.data[1], event.data[2]);
            event_sent = true;
        } 
        else if (event.type == "program_change" && event.data.size() >= 2) {
            snd_seq_ev_set_pgmchange(&seq_event, event.channel, event.data[1]);
            event_sent = true;
        } 
        else if (event.type == "pitchwheel" && event.data.size() >= 3) {
            int pitch_value = (event.data[2] << 7) | event.data[1];
            snd_seq_ev_set_pitchbend(&seq_event, event.channel, pitch_value - 8192);
            event_sent = true;
        }
        
        if (event_sent) {
            int result = snd_seq_event_output(seq_handle, &seq_event);
            if (result < 0) {
                std::cerr << "Error sending MIDI event: " << snd_strerror(result) << std::endl;
            }
        }
        
        // Flush output
        snd_seq_drain_output(seq_handle);
    }
    
    void control_loop() {
        while (is_playing && !should_stop) {
            auto now = std::chrono::high_resolution_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time);
            
            current_position_ms = elapsed.count();
            
            // Update current tick based on position
            for (const auto& event : events) {
                if (event.time_ms <= current_position_ms) {
                    current_tick = event.tick;
                } else {
                    break;
                }
            }
            
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }
    
    void stop_all_notes() {
        if (!seq_handle) return;
        
        for (int channel = 0; channel < 16; ++channel) {
            // All Notes Off (CC 123)
            snd_seq_event_t seq_event;
            snd_seq_ev_clear(&seq_event);
            snd_seq_ev_set_source(&seq_event, port_id);
            snd_seq_ev_set_subs(&seq_event);
            snd_seq_ev_set_direct(&seq_event);
            snd_seq_ev_set_controller(&seq_event, channel, 123, 0);
            snd_seq_event_output(seq_handle, &seq_event);
            
            // All Sound Off (CC 120)
            snd_seq_ev_clear(&seq_event);
            snd_seq_ev_set_source(&seq_event, port_id);
            snd_seq_ev_set_subs(&seq_event);
            snd_seq_ev_set_direct(&seq_event);
            snd_seq_ev_set_controller(&seq_event, channel, 120, 0);
            snd_seq_event_output(seq_handle, &seq_event);
        }
        
        snd_seq_drain_output(seq_handle);
    }
    
    void cleanup() {
        should_stop = true;
        
        if (playback_thread.joinable()) {
            playback_thread.join();
        }
        if (control_thread.joinable()) {
            control_thread.join();
        }
        
        if (seq_handle) {
            stop_all_notes();
            
            if (queue_id >= 0) {
                snd_seq_stop_queue(seq_handle, queue_id, NULL);
                snd_seq_free_queue(seq_handle, queue_id);
            }
            
            snd_seq_close(seq_handle);
            seq_handle = nullptr;
        }
    }
};

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <events_json_file>" << std::endl;
        std::cerr << "Commands: PLAY, PAUSE, STOP, SEEK <tick>, STATUS, QUIT" << std::endl;
        return 1;
    }
    
    AlsaSequencerController controller;
    
    if (!controller.initialize()) {
        std::cerr << "Failed to initialize ALSA sequencer" << std::endl;
        return 1;
    }
    
    if (!controller.load_events(argv[1])) {
        std::cerr << "Failed to load events from: " << argv[1] << std::endl;
        return 1;
    }
    
    std::cout << "ALSA Sequencer ready. Waiting for commands..." << std::endl;
    std::cout << "Commands: PLAY, PAUSE, STOP, SEEK <tick>, STATUS, QUIT" << std::endl;
    
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream iss(line);
        std::string command;
        iss >> command;
        
        if (command == "PLAY") {
            controller.play();
        } 
        else if (command == "PAUSE") {
            controller.pause();
        } 
        else if (command == "STOP") {
            controller.stop();
        } 
        else if (command == "SEEK") {
            int tick;
            if (iss >> tick) {
                controller.seek(tick);
            } else {
                std::cerr << "Error: SEEK requires tick parameter" << std::endl;
            }
        }
        else if (command == "STATUS") {
            std::cout << "Status - Playing: " << (controller.get_is_playing() ? "Yes" : "No")
                      << ", Position: " << controller.get_position_ms() << "ms"
                      << ", Tick: " << controller.get_current_tick()
                      << ", Loaded: " << (controller.get_is_loaded() ? "Yes" : "No") << std::endl;
        }
        else if (command == "QUIT") {
            controller.quit();
            break;
        } 
        else if (!command.empty()) {
            std::cerr << "Unknown command: " << command << std::endl;
        }
    }
    
    return 0;
}