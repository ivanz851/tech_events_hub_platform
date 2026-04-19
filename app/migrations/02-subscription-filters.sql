--liquibase formatted sql

--changeset scrapper:10 labels:subscription-filters
ALTER TABLE link_user_mapping DROP COLUMN IF EXISTS tags;
ALTER TABLE link_user_mapping DROP COLUMN IF EXISTS filters;
ALTER TABLE link_user_mapping ADD COLUMN filters JSONB NOT NULL DEFAULT '{}';
