# Movie Rating System (8086 Assembly)

A console-based movie rating app written entirely in **8086 assembly** for the EMU8086 emulator. Admins manage a small movie database; users log in to rate movies, write reviews and search the catalogue.

Built as the course project for **CSE341: Microprocessors** at BRAC University.

## Features

**Accounts**
- Separate admin and user logins, each with its own menu
- Register up to 5 new users, with checks for duplicate usernames, a minimum length of 3 characters and password confirmation

**Admin menu**
- Add movies with a name and genre (Action, Comedy, Drama, Horror, SciFi)
- Edit a movie's name or genre, delete a movie, or delete individual reviews
- View all movies, search, and see the highest-rated movie

**User menu**
- View all movies with their average rating and reviews
- Rate a movie from 1 to 5
- Write a review of up to 40 characters (3 review slots per movie)
- Search by name or genre (case-insensitive, matches any part of the text)
- See the highest-rated movie

Five movies are preloaded at startup so there is something to rate straight away.

## How it works

All data lives in the data segment; there is no file storage or heap. The movie database is a flat 1,680-byte array holding up to 10 movies, and each movie is a fixed 168-byte record:

| Offset | Size | Field |
|---|---|---|
| 0 | 30 bytes | Movie name (null-terminated) |
| 30 | 15 bytes | Genre (null-terminated) |
| 45 | 1 byte | Number of ratings |
| 46 | 2 bytes | Sum of ratings (a word, since it can exceed 255) |
| 48 | 40 bytes | Review 1 |
| 88 | 40 bytes | Review 2 |
| 128 | 40 bytes | Review 3 |

Movie *i* starts at `movie_db + i × 168`. The average rating is the rating sum divided by the number of ratings. Deleting a movie shifts every later record up by one slot.

Input and output use DOS interrupt `INT 21h` (functions `01h` read a character, `02h` print a character, `09h` print a `$`-terminated string). String comparison, case-insensitive substring search, copying and clearing memory are all written as small reusable procedures.

## Running it

1. Install the EMU8086 emulator (Windows).
2. Open `MovieRatingSystem.asm`.
3. Click **Emulate**, then **Run**.

Demo accounts:

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| User | `alice` | `pass1` |
| User | `bob` | `pass2` |

(`charlie`, `diana` and `eve` use `pass3`, `pass4` and `pass5`.)

## Limitations

- Everything is kept in memory, so movies, ratings and new users are lost when the program exits.
- Averages are whole numbers, because the 8086 `DIV` used here returns an integer result.
- Passwords are stored as plain text, which is fine for an emulator demo but not for real use.

## Team

| Name | GitHub |
|---|---|
| Mohammed Mashrekin Yakub | [@mash-yk](https://github.com/mash-yk) |
| [Teammate name] | [GitHub link] |
| [Teammate name] | [GitHub link] |
