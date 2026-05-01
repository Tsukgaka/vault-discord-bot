-- Discord Auth Bot - Database Schema
-- NeonのSQL Editorにそのまま貼り付けて実行してください

CREATE TABLE IF NOT EXISTS guild_settings (
  guild_id                VARCHAR(20) PRIMARY KEY,
  log_channel_id          VARCHAR(20),
  language                VARCHAR(2)  NOT NULL DEFAULT 'ja',
  vpn_protection          BOOLEAN     NOT NULL DEFAULT true,
  sub_account_protection  BOOLEAN     NOT NULL DEFAULT true,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verified_users (
  id                SERIAL PRIMARY KEY,
  guild_id          VARCHAR(20)  NOT NULL,
  discord_id        VARCHAR(20)  NOT NULL,
  discord_username  VARCHAR(100) NOT NULL,
  email             TEXT         NOT NULL,
  ip_address        INET         NOT NULL,
  ip_hash           VARCHAR(64)  NOT NULL,
  email_hash        VARCHAR(64)  NOT NULL,
  is_vpn            BOOLEAN      NOT NULL DEFAULT false,
  verified_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  UNIQUE (guild_id, discord_id),
  UNIQUE (guild_id, email_hash),
  UNIQUE (guild_id, ip_hash)
);

CREATE INDEX IF NOT EXISTS idx_vu_guild    ON verified_users(guild_id);
CREATE INDEX IF NOT EXISTS idx_vu_discord  ON verified_users(discord_id);
CREATE INDEX IF NOT EXISTS idx_vu_ip_hash  ON verified_users(guild_id, ip_hash);
CREATE INDEX IF NOT EXISTS idx_vu_em_hash  ON verified_users(guild_id, email_hash);

CREATE TABLE IF NOT EXISTS auth_sessions (
  token VARCHAR(64) PRIMARY KEY,
  guild_id VARCHAR(20) NOT NULL,
  user_id VARCHAR(20) NOT NULL,
  role_id VARCHAR(20),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);
