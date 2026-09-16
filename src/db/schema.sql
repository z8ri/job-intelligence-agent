CREATE DATABASE IF NOT EXISTS job_intelligence
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE job_intelligence;

CREATE TABLE IF NOT EXISTS jobs (
    job_id      VARCHAR(64) PRIMARY KEY,
    source      VARCHAR(32) NOT NULL,
    company     VARCHAR(255),
    title       VARCHAR(255),
    location    VARCHAR(255),
    remote      ENUM('remote','onsite','hybrid','unknown') DEFAULT 'unknown',
    salary_min  INT,
    salary_max  INT,
    degree_req  ENUM('none','bachelor','master','phd','unknown') DEFAULT 'unknown',
    category    ENUM('backend','frontend','data','devops','fullstack','mobile','management','other') DEFAULT 'other',
    description TEXT,
    publish_time DATETIME,
    crawled_at  DATETIME
);

CREATE TABLE IF NOT EXISTS job_tags (
    job_id  VARCHAR(64),
    tag     VARCHAR(64),
    PRIMARY KEY (job_id, tag),
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

-- 跨轮偏好记忆：session_id -> 上次已知的完整偏好画像
CREATE TABLE IF NOT EXISTS user_memory (
    session_id  VARCHAR(64) PRIMARY KEY,
    preferences JSON NOT NULL,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
