--liquibase formatted sql

--changeset scrapper:1 labels:initial
CREATE TABLE IF NOT EXISTS tg_chat (
    id BIGINT PRIMARY KEY
);

--changeset scrapper:2 labels:initial
CREATE TABLE IF NOT EXISTS link (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT link_url_unique UNIQUE (url)
);

CREATE INDEX IF NOT EXISTS idx_link_url ON link(url);

--changeset scrapper:3 labels:initial
CREATE TABLE IF NOT EXISTS link_user_mapping (
    link_id BIGINT NOT NULL REFERENCES link(id) ON DELETE CASCADE,
    chat_id BIGINT NOT NULL REFERENCES tg_chat(id) ON DELETE CASCADE,
    tags TEXT[] NOT NULL DEFAULT '{}',
    filters TEXT[] NOT NULL DEFAULT '{}',
    added_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (link_id, chat_id)
);

CREATE INDEX IF NOT EXISTS idx_lum_chat_id ON link_user_mapping(chat_id);
CREATE INDEX IF NOT EXISTS idx_lum_link_id ON link_user_mapping(link_id);

--changeset scrapper:4 labels:initial
CREATE TABLE IF NOT EXISTS event_data (
    id BIGSERIAL PRIMARY KEY,
    link_id BIGINT NOT NULL REFERENCES link(id) ON DELETE CASCADE,
    title TEXT,
    event_date TEXT,
    location TEXT,
    price TEXT,
    registration_url TEXT,
    format TEXT,
    event_type TEXT,
    summary TEXT,
    tags TEXT[] NOT NULL DEFAULT '{}',
    organizer TEXT,
    scraped_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_data_link_id ON event_data(link_id);
