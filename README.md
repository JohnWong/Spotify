# Spotify — Billboard Hot 100 → Spotify Playlist

把 [Billboard Hot 100](https://www.billboard.com/charts/hot-100/) 榜单自动同步到一个 Spotify 歌单。不依赖 Spotipy，用 OOP + Spotify Web API 原生实现授权、搜索、清空与写入。

## 部署（Google Cloud）

本项目部署在 **Google Cloud Platform**，用 `gcloud` CLI 部署。

| 项目 | 值 |
| --- | --- |
| GCP Project | `breakbupt` |
| Cloud Run 服务 | `billboard-spotify`（region `us-central1`） |
| 服务 URL | `https://billboard-spotify-668711577072.us-central1.run.app` |
| Cloud Scheduler 任务 | `billboard-sync`（`us-central1`，`0 */12 * * *` UTC，每 12 小时触发一次 `POST /`） |
| 状态存储 | Google Cloud Storage（`GCS_BUCKET`），存 `refresh_token.txt`、`api.json` |

架构：Cloud Scheduler 定时 `POST` Cloud Run 服务 → `main.py`（Flask + gunicorn）调用
`billboard_to_spotify.updateBillboardForSAE()` 跑一次同步。OAuth 凭据与 refresh token
通过 `sae_patch.py` 读写 GCS（`STORAGE_MODE=gcs`，默认）。

### 重新部署

```bash
gcloud run deploy billboard-spotify \
  --source . \
  --region us-central1 \
  --project breakbupt
```

### 手动触发一次

```bash
gcloud scheduler jobs run billboard-sync --location us-central1 --project breakbupt
```

## 本地运行

```bash
STORAGE_MODE=local python main.py
```

凭据放在本地 `api.json`（`USER_ID` / `CLIENT_ID` / `CLIENT_SECRET`）。

- User ID: https://www.spotify.com/us/account/profile/
- Client ID & Secret: https://developer.spotify.com/dashboard
