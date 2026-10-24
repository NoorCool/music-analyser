#!/usr/bin/env python3

from pathlib import Path
import csv
import sys
import math
import random

import matplotlib.pyplot as plt
import matplotlib.image as mpimg

#Current music library solely consists of MP3 files
AUDIO_EXT = ".mp3"

#Album covers are added to each album folder as an image
COVER_EXT = [
    ".jpg",
    ".jpeg",
    ".png",
]

#Name of the album covers
COVER_NAME = "cover"

#Number of album covers to visualise
COVER_LIM = 100

#Generated files and directories
STATS_DIR = ".music_stats"
README_NAME = "README.md"
CSV_NAME = "albums.csv"

def format_bytes(num_bytes: float) -> str:
    """Format bytes."""

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
        "PB",
    ]

    size = float(num_bytes)

    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size:.2f} EB"


def format_int(value: int) -> str:
    """Format integers with thousands separators."""

    return f"{value:,}"

def is_audio_file(path) -> bool:
    """Returns True if the file has one of given audio extension."""

    return path.is_file() and path.suffix.lower() == AUDIO_EXT

def is_image_file(path) -> bool:
    """Return True if the file has a supported image extension."""

    return path.is_file() and path.suffix.lower() in COVER_EXT

def find_album_cover(album_dir):
    """
    Find the album cover.

    First looks for:
        cover.jpg
        cover.jpeg
        cover.png

    If none of those exist, the first image in the directory is used.

    If there are no images, returns None.
    """

    for extension in COVER_EXT:
        cover = album_dir / (COVER_NAME + extension)

        if cover.is_file():
            return cover

    images = sorted(path for path in album_dir.iterdir() if is_image_file(path))

    if images:
        return images[0]

    return None

def scan_music_library(music_dir) -> dict:
    """
    Scan the music directory.

    Expected structure:
        music_dir/
            A/
                Artist/
                    Album/
                        tracks...
                        cover.jpg

    Returns:
        Dictionary containing all discovered information.
    """

    artists = []
    albums = []
    tracks = []

    #Informative checks for when the library grows.
    albums_without_cover = []
    unexpected_files = []
    unexpected_dirs = []
    
    #Get all letter directories and the 0-9 directory.
    alphabetical_dirs = sorted(path for path in music_dir.iterdir() if path.is_dir() and not path.name.startswith(".") and path.name != STATS_DIR)

    for letter_dir in alphabetical_dirs:

        #Get all artist directories.
        artist_dirs = sorted(path for path in letter_dir.iterdir() if path.is_dir() and not path.name.startswith("."))

        for artist_dir in artist_dirs:
            artist_name = artist_dir.name

            artists.append({
                "name": artist_name,
                "dir": artist_dir,
                "letter": letter_dir.name,
            })

            #Get all album directories.
            album_directories = sorted(path for path in artist_dir.iterdir() if path.is_dir() and not path.name.startswith("."))

            for album_dir in album_directories:
                album_name = album_dir.name
                cover = find_album_cover(album_dir) #Get album cover.

                #Get all tracks in the albums.
                album_tracks = sorted(path for path in album_dir.iterdir() if is_audio_file(path))

                audio_size = sum(path.stat().st_size for path in album_tracks)

                album_info = {
                    "artist": artist_name,
                    "album": album_name,
                    "path": album_dir,
                    "cover": cover,
                    "tracks": album_tracks,
                    "track_count": len(album_tracks),
                    "size": audio_size,
                }

                albums.append(album_info)
                tracks.extend(album_tracks)

                #If no album cover is found keep track of it in the list.
                if cover is None:
                    albums_without_cover.append(album_info)
                
            #Check whether there are unwanted files and folders.
                for item in album_dir.iterdir():
                    if item.is_file():
                        if (not is_audio_file(item) and not is_image_file(item)):
                            unexpected_files.append(item)

                    elif item.is_dir():
                        unexpected_dirs.append(item)

            for item in artist_dir.iterdir():
                if item.is_file():
                    unexpected_files.append(item)

    #Get a total overview of the size of the music library.
    total_size = 0

    for path in music_dir.rglob("*"):
        if not path.is_file():
            continue

        try:
            path.relative_to(music_dir / STATS_DIR)
            continue

        except ValueError:
            pass

        total_size += path.stat().st_size

    audio_size = sum(path.stat().st_size for path in tracks)

    return {
        "artists": artists,
        "albums": albums,
        "tracks": tracks,
        "total_size": total_size,
        "audio_size": audio_size,
        "albums_without_covers": albums_without_cover,
        "unexpected_files": unexpected_files,
        "unexpected_directories": unexpected_dirs
    }

def generate_cover_mosaic(albums, output_path, limit = COVER_LIM) -> bool:
    """
    Create an album cover mosaic at exactly 2256x1504 pixels.
    """

    albums_with_covers = [album for album in albums if album["cover"] is not None]

    random.shuffle(albums_with_covers)

    #Limit the number of covers.
    albums_with_covers = albums_with_covers[:limit]

    if not albums_with_covers:
        return False

    width = 2256
    height = 1504
    dpi = 100

    #Determine the grid dimensions.
    columns = 12
    rows = math.ceil(height / (width / columns))

    total_cells = rows * columns

    #Load valid cover images.
    covers = []

    for album in albums_with_covers:
        try:
            covers.append(mpimg.imread(album["cover"]))

        except Exception as error:
            print(
                f"Warning: could not load "
                f"{album['cover']}: {error}"
            )

    if not covers:
        return False

    #Repeat covers if necessary to fill the entire grid.
    while len(covers) < total_cells:
        covers.extend(
            random.choices(covers, k = total_cells - len(covers))
        )

    random.shuffle(covers)
    covers = covers[:total_cells]

    figure, axes = plt.subplots(
        rows,
        columns,
        figsize = (width / dpi, height / dpi),
        dpi = dpi
    )

    figure.subplots_adjust(
        left = 0,
        right = 1,
        top = 1,
        bottom = 0,
        wspace = 0,
        hspace = 0
    )

    for index, axis in enumerate(axes.flat):
        axis.imshow(
            covers[index],
            aspect = "auto",
            interpolation = "antialiased",
        )

        axis.axis("off")

    output_path.parent.mkdir(
        parents = True,
        exist_ok = True,
    )

    figure.savefig(
        output_path,
        dpi = dpi,
        bbox_inches = None,
        pad_inches = 0,
        transparent = False
    )

    plt.close(figure)

    return True

def generate_music_csv(albums: list, music_dir: Path, output_path: Path) -> None:
    """
    Generate a CSV containing album information.
    """

    with output_path.open("w", newline = "", encoding = "utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            "Artist",
            "Album",
            "Tracks",
            "Size",
            "Cover",
            "Path"
        ])

        for album in sorted(albums, key = lambda item: (item["artist"].lower(), item["album"].lower())):
            cover = ""

            if album["cover"]:
                cover = album["cover"].name

            relative_path = (album["path"].relative_to(music_dir))

            writer.writerow([
                album["artist"],
                album["album"],
                album["track_count"],
                album["size"],
                cover,
                relative_path.as_posix()
            ])


def create_readme(stats, mosaic_exists) -> str:
    """
    Generate README.md.
    """

    artists = stats["artists"]
    albums = stats["albums"]
    tracks = stats["tracks"]

    total_size = stats["total_size"]
    audio_size = stats["audio_size"]

    albums_without_covers = stats["albums_without_covers"]

    artist_count = len(artists)
    album_count = len(albums)
    track_count = len(tracks)

    # Average albums per artist.
    average_albums = (album_count / artist_count if artist_count else 0)

    # Average tracks per album.
    average_tracks = (track_count / album_count if album_count else 0)

    # Cover statistics.
    albums_with_covers = (album_count - len(albums_without_covers))
    cover_percentage = (albums_with_covers / album_count * 100 if album_count else 0)

    # Writing README lines.
    lines = []

    lines.extend([
        "# My Personal Music Library",
        "",
        "A Python project for cataloguing, documenting, and keeping track of my personal physical CD collection.",
        "",
        "This project automatically generates an overview of my music library every time I run the script. It collects information about my artists, albums, tracks, album artwork, and storage usage.",
        "",
        "The goal is to combine a digital music catalogue with a practical inventory of my physical collection. In the future, this project will be expanded to help organise my CD racks, automatically determine where newly purchased albums should be placed.",
        "",
        "The catalogue and statistics are already being generated automatically, while physical CD organisation features haven't been implemented.",
        ""
    ])

    lines.extend([
        "## Project Goals",
        "",
        "- **Cataloguing:** Generate an overview of my music collection using Python.",
        "- **Collection Inventory:** Maintain a digital inventory of the physical CDs I own.",
        "- **Album artwork:** Track missing covers and create a visual mosaic of the collection.",
        "- **CD rack organisation:** Develop a system that determines where albums should be stored.",
        "- **Automatic placement suggestions:** Find a suitable location for newly acquired CDs based on the existing organisation of the racks.",
        ""
    ])

    lines.extend([
        "## Library Statistics",
        "",
        "| Statistic | Value |",
        "|---|---:|",
        f"| 🎤 Artists | **{artist_count:,}** |",
        f"| 💿 Albums | **{album_count:,}** |",
        f"| 🎵 Tracks | **{track_count:,}** |",
        f"| 💾 Total size | **{format_bytes(total_size)}** |",
        f"| 🎧 Audio size | **{format_bytes(audio_size)}** |",
        f"| Average albums per artist | **{average_albums:.1f}** |",
        f"| Average tracks per album | **{average_tracks:.1f}** |",
        f"| Albums with covers | **{cover_percentage:.1f}%** |",
        ""
    ])

    if mosaic_exists:
        lines.extend([
            "## Album Covers",
            "",
            "A selection of album artwork from the collection is made into a collage. For copyright reasons it is not given in this repository :)",
            "",
            "[Browse the complete album list](albums.csv)",
            ""
        ])

    lines.extend([
        "## Artwork",
        "",
        f"- Albums with covers: **{albums_with_covers:,}**",
        f"- Albums without covers: **{len(albums_without_covers):,}**",
        ""
    ])

    if albums_without_covers:
        lines.extend([
            "### Albums without covers",
            "",
            "| Artist | Album |",
            "|---|---|",
        ])

        for album in albums_without_covers[:50]:
            lines.append(f"| {album['artist']} | {album['album']} |")

        if len(albums_without_covers) > 50:
            lines.extend([
                "",
                f"_Showing the first 50 of {len(albums_without_covers):,}._",
            ])

        lines.append("")

    lines.extend([
        "## To Do's",
        "",
        "- [x] Automatically generate the README and library statistics.",
        "- [x] Export the album catalogue to CSV.",
        "- [x] Generate an album cover mosaic.",
        "- [ ] Track the physical organisation of each CD.",
        "- [ ] Automatically reveal storage locations for newly purchased CDs.",
        ""
    ])

    return "\n".join(lines)

def main():
    if len(sys.argv) != 2:
        print("Usage:\tpython3 music_analyser.py /path/to/Music")
        sys.exit(1)

    #Get the parent directory of this scipt.
    script_dir = (Path(__file__).resolve().parent)

    #Set the given path to the library as the root.
    root = (Path(sys.argv[1]).expanduser().resolve())

    if not root.exists():
        print(f"Error: directory does not exist: {root}")
        sys.exit(1)

    if not root.is_dir():
        print(f"Error: not a directory: {root}")
        sys.exit(1)

    #Terminal introduction to script.
    print()
    print("=" * 60)
    print("MUSIC LIBRARY ANALYSER")
    print("=" * 60)
    print()

    #Print the root.
    print(f"Library:\t{root}")

    #Print output path.
    print(f"Output:\t{script_dir}")

    print()

    #"Loading screen".
    print("Scanning library...")

    #Get the stats.
    stats = scan_music_library(root)

    #"Loading complete".
    print()
    print("Scan complete.")
    print()

    #Get the stats so they are shown in the terminal.
    artist_count = len(stats["artists"])
    album_count = len(stats["albums"])
    track_count = len(stats["tracks"])

    print(f"Artists:\t{format_int(artist_count)}")
    print(f"Albums:\t{format_int(album_count)}")
    print(f"Tracks:\t{format_int(track_count)}")
    print(f"Total size:\t{format_bytes(stats['total_size'])}")
    print(f"Audio size:\t{format_bytes(stats['audio_size'])}")
    print(f"Missing covers:\t{format_int(len(stats['albums_without_covers']))}")
    print()

    #Get the stats_directory.
    stats_directory = (script_dir / STATS_DIR)
    stats_directory.mkdir(exist_ok = True)

    #Create mosaic.
    print("Creating album cover mosaic...")
    mosaic_path = (stats_directory / "cover_mosaic.png")
    mosaic_exists = generate_cover_mosaic(stats["albums"], mosaic_path)

    if mosaic_exists:
        print(f"Cover mosaic:\t{mosaic_path}")
    else:
        print("No album covers found.")

    print()

    #Create the album csv.
    print("Creating album list...")
    csv_path = (script_dir / CSV_NAME)
    generate_music_csv(stats["albums"], root, csv_path)
    print(f"Album list:\t{csv_path}")

    print()

    #Create the README.
    print("Creating README...")
    readme = create_readme(stats, mosaic_exists)
    readme_path = (script_dir / README_NAME)
    readme_path.write_text(readme,encoding = "utf-8")
    print(f"README:\t{readme_path}")

    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print()

if __name__ == "__main__":
    main()

