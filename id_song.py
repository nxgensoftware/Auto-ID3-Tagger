#!/usr/bin/env python3

import asyncio
import os
import urllib.request
import eyed3
import eyed3.plugins.art
import platform
import sys
import getpass
import datetime

from pathlib import Path
from shazamio import Shazam, Serialize
from dateutil.parser import parse as dateparse

directory = None
recursive = False
emptyonly = True
overwriteconsent = False
files: list[Path] = []

if platform.system() == "Windows":
    user = getpass.getuser()
    directory = "C:/Users/" + user + "/Music"
elif platform.system() == "Linux" or platform.system() == "Darwin":
    user = getpass.getuser()
    directory = "/home/" + user + "/Music"
else:
    print("Unsupported OS")
    exit(1)

def print_help():
    print("Usage: python id_song.py [options]")
    print("Options:")
    print("\t-h, --help: Show this help message")
    print("\t-d, --directory: Specify a directory to scan for MP3 files")
    print("\t\t if no directory is specified, the default Music folder is used")
    print("\t-r, --recursive: Scan the directory recursively")
    print("\t-a, --all: Scan all mp3 files")
    print("\t\t if argument is not specified, only mp3 files with no tags are scanned")
    print("\t-au, --autoaccept: auto accept overwriting tags")
    print("\t\t if argument is not specified, every mp3 file set to be written will result in a consent prompt")
    print("\t\t\t(not using it can get annoying for long lists)")
    print("\n")
    print("Example Usage:")
    print("\tpython id_song.py -r")
    print("\tpython id_song.py -d /home/<username>/Downloads/totallylegalmusicfolder -r")
    print("\tpython id_song.py -r -d /home/<username>/Downloads/totallylegalmusicfolder")

def tags_empty(file):
    # This doesn't exactly filter 100% of the time, as a file might just tags that aren't scanned, but 
    # 1, I don't know how to check for absolutely all tags
    # 2, This set of tags is basic enough that it should be present in most files
    # If you know of a better way, that's what pull requests are for! (thanks in advance if you do contribute! :3)
    #print("checking: " + file)
    eyed3.log.setLevel("ERROR")
    file = eyed3.load(file)
    if(file.tag.artist == None and file.tag.album == None and file.tag.title == None):
        return True
    else:
        return False

def check_args():
    global directory
    global recursive
    global emptyonly
    global overwriteconsent
    for arg in sys.argv:
        if arg == "-h" or arg == "--help":
            return False
        if arg == "-d" or arg == "--directory":
            if(sys.argv.index(arg) + 1 < len(sys.argv)):
                if(os.path.isdir(sys.argv[sys.argv.index(arg) + 1])):
                    directory = sys.argv[sys.argv.index(arg) + 1]
                else:
                    print("Invalid directory")
                    return False
        if arg == "-r" or arg == "--recursive":
            recursive = True
        if arg == "-a" or arg == "--all":
            emptyonly = False
        if arg == "-au" or arg == "--autoaccept":
            overwriteconsent = True
    
def get_files(directory):
    global files
    files_scan = os.listdir(directory)
    for file in files_scan:
        if(os.path.isdir(os.path.join(directory, file))):
            if(recursive):
                get_files(os.path.join(directory, file))
            else:   
                continue
        try:
            if(Path(file).suffixes.index(".mp3") != -1):
                if(emptyonly):
                    if(tags_empty(os.path.join(directory, file))):
                        files.append(Path(os.path.join(directory, file)))
                    else:
                        continue
                else:
                    files.append(Path(os.path.join(directory, file)))
        except ValueError:
            continue
    # Restore logging level if it was changed
    eyed3.log.setLevel("ERROR")

async def main():
    shazam = Shazam()
    for file in files:
        # Loop over files and filter on MP3 files
        file = file.resolve()
        # Identify song using Shazam
        out = await shazam.recognize(bytes(file.read_bytes()))
        if len(out['matches']) < 1:
            print("Shazam could not find a match for file: " + str(file) + " skipping...")
            continue
        track_id = out['matches'][0]['id']
        about_track = await shazam.track_about(track_id=track_id)

        # Extract data from Shazam response
        tags = {
            "title": about_track['title'],
            "artist": about_track['subtitle'],
            "genre": about_track['genres']['primary'],
            "release_date": dateparse(about_track['releasedate']).strftime("%Y-%m-%d")
        }

        url = out['track']['share']['href']
        cover_art = out['track']['images']['coverarthq'].replace("400x400", "1000x1000")
        data = Serialize.track(out['track'])

        for section in data.sections:
            if section.type == "SONG":
                for md in section.metadata:
                    if md.title == "Album":
                        tags['album'] = md.text
                    if md.title == "Released":
                        tags['year'] = md.text

        id3 = eyed3.load(file)

        # Save new tags
        id3 = eyed3.load(file)
        id3.tag.album = tags['album']
        id3.tag.artist = tags['artist']
        id3.tag.album_artist = tags['artist']
        id3.tag.genre = tags['genre']
        id3.tag.title = tags['title']
        id3.tag.release_date = tags['release_date']

        # Download art and (temporary) save locally
        local_art = os.path.join(file.parent, "tmp_file" + cover_art[-4:])
        urllib.request.urlretrieve(cover_art, local_art)

        # Save art to MP3 file
        id3_front_cover_id = eyed3.utils.art.TO_ID3_ART_TYPES['FRONT_COVER'][0]
        id3_cover = eyed3.plugins.art.ArtFile(local_art)
        id3_cover.id3_art_type = id3_front_cover_id
        id3.tag.images.set(id3_cover.id3_art_type, id3_cover.image_data, id3_cover.mime_type)

        print("For file: \"" + str(file) + "\"")
        print("Shazam found match:")
        print("Title: " + tags['title'])
        print("Artist: " + tags['artist'])
        print("Album: " + tags['album'])
        print("Genre: " + tags['genre'])
        print("Release Date: " + tags['release_date'])
        print("URL: " + url)

        # Save the new tags
        if(overwriteconsent):
            id3.tag.save(version=(2, 3, 0))
            print("Saved new tags to file " + str(file))
        else:
            print("Do you want to overwrite the tags for this file? (y/n)")
            overwrite = input()
            if(overwrite == "y"):
                id3.tag.save(version=(2, 3, 0))
                print("Saved new tags to file " + str(file))
            else:
                print("Skipping file")
                continue

get_files(directory)        

if(check_args() == False):
    print_help()
    exit(0)
else:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
