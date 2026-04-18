--liquibase formatted sql

--changeset scrapper:5 labels:identity
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

--changeset scrapper:6 labels:identity
CREATE TABLE IF NOT EXISTS user_identities (
    id UUID DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR NOT NULL,
    provider_id VARCHAR NOT NULL,
    CONSTRAINT user_identities_provider_unique UNIQUE (provider, provider_id),
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_ui_user_id ON user_identities(user_id);
CREATE INDEX IF NOT EXISTS idx_ui_provider ON user_identities(provider, provider_id);

--changeset scrapper:7 labels:identity
CREATE TABLE IF NOT EXISTS user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    notify_email BOOLEAN NOT NULL DEFAULT false,
    notify_telegram BOOLEAN NOT NULL DEFAULT true
);

--changeset scrapper:8 labels:identity
ALTER TABLE tg_chat ADD COLUMN IF NOT EXISTS user_uuid UUID;
UPDATE tg_chat SET user_uuid = gen_random_uuid() WHERE user_uuid IS NULL;

INSERT INTO users (id, created_at)
SELECT user_uuid, NOW() FROM tg_chat
ON CONFLICT (id) DO NOTHING;

INSERT INTO user_identities (id, user_id, provider, provider_id)
SELECT gen_random_uuid(), user_uuid, 'telegram', id::text FROM tg_chat
ON CONFLICT (provider, provider_id) DO NOTHING;

INSERT INTO user_settings (user_id, notify_email, notify_telegram)
SELECT user_uuid, false, true FROM tg_chat
ON CONFLICT (user_id) DO NOTHING;

--changeset scrapper:9 labels:identity
ALTER TABLE link_user_mapping ADD COLUMN IF NOT EXISTS user_id UUID;

UPDATE link_user_mapping lum
SET user_id = tc.user_uuid
FROM tg_chat tc
WHERE lum.chat_id = tc.id AND lum.user_id IS NULL;

ALTER TABLE link_user_mapping ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE link_user_mapping ADD CONSTRAINT lum_user_fk
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE link_user_mapping DROP CONSTRAINT link_user_mapping_pkey;
ALTER TABLE link_user_mapping ADD PRIMARY KEY (link_id, user_id);
ALTER TABLE link_user_mapping DROP COLUMN chat_id;

DROP INDEX IF EXISTS idx_lum_chat_id;
CREATE INDEX IF NOT EXISTS idx_lum_user_id ON link_user_mapping(user_id);

--changeset scrapper:10 labels:identity
ALTER TABLE tg_chat DROP COLUMN IF EXISTS user_uuid;
DROP TABLE IF EXISTS tg_chat;
