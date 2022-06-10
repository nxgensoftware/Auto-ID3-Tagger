# Auto ID3 Tagger
This script will read all files in the provided folder (MUSIC_FOLDER) and identify the songs using Shazam.
It will then collect some information about the songs, including album art, and write this information to the ID3 tags
of the MP3 file.

### Packages used
[ShazamIO](https://github.com/dotX12/ShazamIO) - Used to identify the songs

[EyeD3](https://eyed3.readthedocs.io/en/latest/index.html) - Used to write the ID3 tags