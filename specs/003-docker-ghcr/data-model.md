# Data Model: Docker Container with GitHub Container Registry

**Feature**: 003-docker-ghcr
**Date**: 2026-01-12

## Overview

This feature does not introduce new data entities to the application. The container packages the existing application without data model changes.

## Configuration Entities (Existing)

The following entities are referenced but not modified by this feature:

### Configuration File (config.yaml)

**Purpose**: Runtime configuration for the polybotz application
**Location in container**: `/app/config.yaml` (mounted volume)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| slugs | list[string] | Yes | Polymarket event slugs to monitor |
| poll_interval | integer | No | Seconds between polls (default: 60) |
| spike_threshold | float | No | Percentage for spike alerts (default: 5.0) |
| lvr_threshold | float | No | LVR threshold for liquidity warnings (default: 8.0) |
| telegram.bot_token | string | Yes | Telegram bot API token |
| telegram.chat_id | string | Yes | Telegram chat/channel ID |

### Environment Variables

**Purpose**: Sensitive credentials passed at container runtime

| Variable | Required | Description |
|----------|----------|-------------|
| TELEGRAM_BOT_TOKEN | Yes | Telegram bot API token (can override config) |
| TELEGRAM_CHAT_ID | Yes | Telegram chat/channel ID (can override config) |

## Container Artifacts

### Container Image Metadata

| Attribute | Value |
|-----------|-------|
| Registry | ghcr.io |
| Repository | {owner}/polybotz |
| Tags | main, latest, {version}, sha-{commit} |
| Platforms | linux/amd64, linux/arm64 |

## State Transitions

N/A - The container is stateless. All state is external (Polymarket API, Telegram API).
