import asyncio
import os
import urllib.request

import eyed3
import eyed3.plugins.art

from shazamio import Shazam, Serialize

MUSIC_FOLDER = ""


async def main():
    shazam = Shazam()
    files = os.listdir(MUSIC_FOLDER)
    for file in files:
        print(file)
        # Loop over files and filter on MP3 files
        path = os.path.join(MUSIC_FOLDER, file)
        if not os.path.isfile(path):
            continue
        if path[-3:] != "mp3":
            continue

        # Identify song using Shazam
        out = await shazam.recognize_song(path)
        if len(out['matches']) < 1:
            print("Shazam could not find a match")
            continue
        data = Serialize.track(out['track'])

        # Extract data from Shazam response
        tags = {}
        tags['title'] = out['track']['title']
        tags['artist'] = out['track']['subtitle']
        tags['genre'] = out['track']['genres']['primary']

        cover_art = out['track']['images']['coverarthq'].replace("400x400", "1000x1000")

        for section in data.sections:
            if section.type == "SONG":
                for md in section.metadata:
                    if md.title == "Album":
                        tags['album'] = md.text
                    if md.title == "Released":
                        tags['year'] = md.text

        print("Shazam: " + tags['artist'] + " - " + tags['title'] + " (" + tags['album'] + ")")

        # Reset current tags
        id3 = eyed3.load(path)
        if id3.tag:
            id3.tag.clear()
            id3.tag.save()
        else:
            id3.initTag()
            id3.tag.save()

        # Save new tags
        id3 = eyed3.load(path)
        id3.tag.album = tags['album']
        id3.tag.artist = tags['artist']
        id3.tag.album_artist = tags['artist']
        id3.tag.genre = tags['genre']
        id3.tag.title = tags['title']
        id3.tag.year = tags['year']

        # Download art and (temporary) save locally
        local_art = os.path.join(MUSIC_FOLDER, "tmp_file" + cover_art[-4:])
        urllib.request.urlretrieve(cover_art, local_art)

        # Save art to MP3 file
        id3_front_cover_id = eyed3.utils.art.TO_ID3_ART_TYPES['FRONT_COVER'][0]
        id3_cover = eyed3.plugins.art.ArtFile(local_art)
        id3_cover.id3_art_type = id3_front_cover_id
        id3.tag.images.set(id3_cover.id3_art_type, id3_cover.image_data, id3_cover.mime_type)

        # Save the new tags
        id3.tag.save(version=(2, 3, 0))

        print("Saved new tags")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
