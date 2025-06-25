-- Database schema for movie scraper
-- Run this in your Supabase SQL Editor

-- Create movies table
CREATE TABLE IF NOT EXISTS knowledge_base.movies (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    description TEXT,
    content_hash TEXT, -- Hash of movie content for change detection
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create cinemas table
CREATE TABLE IF NOT EXISTS knowledge_base.cinemas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_movies_name ON knowledge_base.movies(name);
CREATE INDEX IF NOT EXISTS idx_movies_is_active ON knowledge_base.movies(is_active);
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