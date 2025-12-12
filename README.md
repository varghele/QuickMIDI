# QuickMIDI
Quick MIDI analyzer and fixer, I don't want to open the DAW everytime.\
If you wanto build it yourself, you will need the following:
``````bash
conda create --name quickmidi python=3.12
conda activate quickmidi
conda install anaconda::pyqt
pip install python-rtmidi
pip install pyaudio soundfile audioread numpy librosa
pip install scikit-learn scipy numba llvmlite
pip install requests urllib3 certifi charset-normalizer idna
pip install mido msgpack
pip install joblib threadpoolctl
pip install lazy_loader pooch packaging platformdirs
pip install cffi pycparser
pip install PyQt6_sip sip
pip install decorator typing_extensions
pip install soxr
``````
You can also run:
``````bash
pip install -r requirements.txt
``````
