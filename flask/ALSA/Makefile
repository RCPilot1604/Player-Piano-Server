# Makefile
CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O2 -pthread
LIBS = -lasound -ljsoncpp

TARGET = alsa_midi_player
SOURCE = alsa_midi_player.cpp

all: $(TARGET)

$(TARGET): $(SOURCE)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SOURCE) $(LIBS)

clean:
	rm -f $(TARGET)

install-deps:
	sudo apt-get update
	sudo apt-get install libasound2-dev libjsoncpp-dev build-essential

.PHONY: clean install-deps all