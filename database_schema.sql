-- Database schema for movie scraper
-- Run this in your Supabase SQL Editor

-- Create the knowledge_base schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS knowledge_base;

-- Grant usage on the knowledge_base schema to anon and authenticated users
GRANT USAGE ON SCHEMA knowledge_base TO anon;
GRANT USAGE ON SCHEMA knowledge_base TO authenticated;

-- Create movies table
CREATE TABLE IF NOT EXISTS knowledge_base.movies (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT,
    category TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create cinemas table
CREATE TABLE IF NOT EXISTS knowledge_base.cinemas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    url TEXT,
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create showtimes table
CREATE TABLE IF NOT EXISTS knowledge_base.showtimes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    movie_id UUID REFERENCES knowledge_base.movies(id) ON DELETE CASCADE,
    cinema_id UUID REFERENCES knowledge_base.cinemas(id) ON DELETE CASCADE,
    showtime TIMESTAMP WITH TIME ZONE NOT NULL,
    language TEXT, -- e.g., "英語版", "粵語版"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Grant permissions on tables to anon and authenticated users
-- Movies table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_base.movies TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_base.movies TO authenticated;

-- Cinemas table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_base.cinemas TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_base.cinemas TO authenticated;

-- Showtimes table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_base.showtimes TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_base.showtimes TO authenticated;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_movies_name ON knowledge_base.movies(name);

CREATE INDEX IF NOT EXISTS idx_movies_last_updated ON knowledge_base.movies(last_updated);
CREATE INDEX IF NOT EXISTS idx_cinemas_name ON knowledge_base.cinemas(name);
CREATE INDEX IF NOT EXISTS idx_showtimes_movie_id ON knowledge_base.showtimes(movie_id);
CREATE INDEX IF NOT EXISTS idx_showtimes_cinema_id ON knowledge_base.showtimes(cinema_id);
CREATE INDEX IF NOT EXISTS idx_showtimes_showtime ON knowledge_base.showtimes(showtime);

-- Create a composite index for efficient showtime queries
CREATE INDEX IF NOT EXISTS idx_showtimes_movie_cinema_time ON knowledge_base.showtimes(movie_id, cinema_id, showtime);

-- Add RLS (Row Level Security) policies if needed
-- ALTER TABLE movies ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cinemas ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE showtimes ENABLE ROW LEVEL SECURITY; 