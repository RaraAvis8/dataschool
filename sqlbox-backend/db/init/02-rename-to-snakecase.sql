-- Rename Chinook's singular table names to the plural snake_case names the
-- dataschool tutorials and sqlbox.js autocomplete expect:
--   albums, artists, tracks, employees, invoices, customers, genres,
--   playlists, media_types, playlist_track, invoice_lines
--
-- Also adds the `id` alias columns: the tutorials consistently use
-- `albums.id`, `artists.id`, `tracks.id` etc. (see sqlbox.js schema and
-- e.g. _chapters/learn-sql/basic/from.md: "SELECT id, title, artist_id FROM albums").
-- Chinook names its PKs `album_id`, `artist_id`, ... so we rename those to `id`.

ALTER TABLE album         RENAME TO albums;
ALTER TABLE artist        RENAME TO artists;
ALTER TABLE track         RENAME TO tracks;
ALTER TABLE employee      RENAME TO employees;
ALTER TABLE customer      RENAME TO customers;
ALTER TABLE genre         RENAME TO genres;
ALTER TABLE invoice       RENAME TO invoices;
ALTER TABLE invoice_line  RENAME TO invoice_lines;
ALTER TABLE media_type    RENAME TO media_types;
ALTER TABLE playlist      RENAME TO playlists;
-- playlist_track already matches its expected name

-- PK renames: <table>_id -> id
ALTER TABLE albums        RENAME COLUMN album_id    TO id;
ALTER TABLE artists       RENAME COLUMN artist_id   TO id;
ALTER TABLE tracks        RENAME COLUMN track_id    TO id;
ALTER TABLE employees     RENAME COLUMN employee_id TO id;
ALTER TABLE customers     RENAME COLUMN customer_id TO id;
ALTER TABLE genres        RENAME COLUMN genre_id    TO id;
ALTER TABLE invoices      RENAME COLUMN invoice_id  TO id;
ALTER TABLE invoice_lines RENAME COLUMN invoice_line_id TO id;
ALTER TABLE media_types   RENAME COLUMN media_type_id TO id;
ALTER TABLE playlists     RENAME COLUMN playlist_id TO id;
-- playlist_track has no surrogate PK (composite playlist_id + track_id), keep as-is

-- FK columns keep their descriptive names (album_id, artist_id, ...) which is
-- exactly what the tutorials use: tracks.album_id, albums.artist_id, etc.

-- SERIAL sequences follow the renamed columns automatically in PG; but their
-- names still reference old column names. Rename for tidiness.
ALTER SEQUENCE album_album_id_seq    RENAME TO albums_id_seq;
ALTER SEQUENCE artist_artist_id_seq  RENAME TO artists_id_seq;
ALTER SEQUENCE track_track_id_seq    RENAME TO tracks_id_seq;
ALTER SEQUENCE employee_employee_id_seq RENAME TO employees_id_seq;
ALTER SEQUENCE customer_customer_id_seq RENAME TO customers_id_seq;
ALTER SEQUENCE genre_genre_id_seq    RENAME TO genres_id_seq;
ALTER SEQUENCE invoice_invoice_id_seq RENAME TO invoices_id_seq;
ALTER SEQUENCE invoice_line_invoice_line_id_seq RENAME TO invoice_lines_id_seq;
ALTER SEQUENCE media_type_media_type_id_seq RENAME TO media_types_id_seq;
ALTER SEQUENCE playlist_playlist_id_seq RENAME TO playlists_id_seq;

ANALYZE;
